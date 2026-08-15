#coding: utf-8
#@author sundream
#@date 2026-08-07
"""Excel <-> schema/json/binary import and export (MapEditor round-trip).

- import_xlsx_to_dirs: xlsx workbook -> schema/ + json/ (+ kind=1 class deps)
- export_one / export_dir: schema + json or binary -> xlsx
- field.layout restores merge-split columns (P1 keys / P2 element-per-column)
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

try:
    import openpyxl
    from openpyxl import load_workbook
    from openpyxl.comments import Comment
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
except ImportError:
    openpyxl = None
    load_workbook = None

from XlsParser.Config import Config
from XlsParser.Sheet import Sheet, is_importable_sheet_title, split_at_display
from XlsParser.Xls2JsonParser import Xls2JsonParser
from XlsParser.Xls2SchemaParser import (
    Xls2SchemaParser,
    KIND_CLASS,
    KIND_1D,
    KIND_2D,
)
from XlsParser.ByteStream import ByteStream
from XlsParser.Type import Type, parse_tags_cell, format_tags_cell
from XlsParser.XlsClass import readClass
from XlsParser.XlsEnum import readEnum

CLASS_WORKBOOK = "__class__.xlsx"
ENUM_WORKBOOK = "__enum__.xlsx"

EXCEL_DEFAULT_COL_WIDTH = 8.43
EXPORT_COL_WIDTH = EXCEL_DEFAULT_COL_WIDTH * 1.5

STRING_ALIASES = frozenset(
    {"string", "i18nstring", "lang", "json", "bit32", "bit64", "bit"}
)


def field_remarks(field: dict) -> str:
    if not field:
        return ""
    return field.get("remarks") or ""


def is_excel_text_type(typ: str) -> bool:
    t = (typ or "").strip().lower()
    if not t:
        return False
    if t in STRING_ALIASES or t == "string":
        return True
    if t.startswith("list<") or t.startswith("map<"):
        return True
    return False


def format_bit_mask_cell(val):
    """Convert stored bit mask int back to Excel [bitIndex,...] text."""
    if val is None or val == "":
        return "[]"
    if isinstance(val, str):
        return val
    if isinstance(val, list):
        return "[" + ",".join(str(x) for x in val) + "]"
    try:
        n = int(val)
    except Exception:
        return str(val)
    if n == -1:
        return "[-1]"
    bits = []
    i = 0
    while n:
        if n & 1:
            bits.append(str(i))
        n >>= 1
        i += 1
    return "[" + ",".join(bits) + "]"


def _class_field_names(class_name: str):
    typ = Type.get(class_name)
    if typ is not None and typ.isClass() and typ.fields:
        return [f.name for f in typ.fields]
    return None


def encode_value_for_excel(typ: str, val):
    """Encode json/runtime value into Excel cell text/number for re-import."""
    if val is None:
        return None
    if isinstance(val, bool):
        return 1 if val else 0
    t = (typ or "").strip()
    tl = t.lower()
    if tl in ("bit32", "bit64", "bit"):
        return format_bit_mask_cell(val)
    if tl in ("string", "i18nstring", "lang"):
        return str(val)
    if t.startswith("list<") and t.endswith(">"):
        inner = t[5:-1].strip()
        if not isinstance(val, list):
            return str(val)
        class_fields = _class_field_names(inner)
        if class_fields:
            encoded = []
            for elem in val:
                if isinstance(elem, dict):
                    encoded.append([elem.get(k) for k in class_fields])
                else:
                    encoded.append(elem)
            return json.dumps(encoded, ensure_ascii=False)
        # nested list / primitives
        return json.dumps(val, ensure_ascii=False)
    if t.startswith("map<") and t.endswith(">"):
        if isinstance(val, dict):
            return json.dumps(val, ensure_ascii=False)
        return val
    class_fields = _class_field_names(t)
    if class_fields and isinstance(val, dict):
        return format_bracket_list([val.get(k) for k in class_fields])
    if isinstance(val, (list, dict)):
        return json.dumps(val, ensure_ascii=False)
    return val


def format_int_with_base(val, int_base):
    if val is None or isinstance(val, bool):
        return val
    try:
        n = int(val)
    except Exception:
        return val
    if int_base == 16:
        return hex(n)
    if int_base == 2:
        return bin(n)
    return n


def format_cell_value(typ: str, val, int_base=None):
    if val is None or val == "":
        return "" if is_excel_text_type(typ) else None
    if int_base in (16, 2) and not isinstance(val, (list, dict, bool)):
        return format_int_with_base(val, int_base)
    return encode_value_for_excel(typ, val)


def format_leaf_value(val, int_base=None):
    if val is None:
        return None
    if isinstance(val, bool):
        return 1 if val else 0
    if isinstance(val, (list, dict)):
        return json.dumps(val, ensure_ascii=False)
    if int_base in (16, 2):
        return format_int_with_base(val, int_base)
    return val


def format_bracket_list(values) -> str:
    parts = []
    for v in values:
        if v is None:
            parts.append("nil")
        elif isinstance(v, bool):
            parts.append("1" if v else "0")
        elif isinstance(v, (list, dict)):
            parts.append(json.dumps(v, ensure_ascii=False))
        else:
            parts.append(str(v))
    return "[" + ",".join(parts) + "]"


def format_split_element_cell(field_type: str, layout: dict, elem):
    """Format one list element for P2 (one element per column)."""
    if elem is None:
        return None
    if isinstance(elem, dict):
        element_keys = layout.get("elementKeys")
        if not element_keys:
            typ = Type.get((field_type or "").strip())
            # list<Class> → Class
            inner = field_type or ""
            if inner.startswith("list<") and inner.endswith(">"):
                inner = inner[5:-1].strip()
                typ = Type.get(inner)
            if typ is not None and typ.isClass() and typ.fields:
                element_keys = [f.name for f in typ.fields]
            else:
                element_keys = list(elem.keys())
        return format_bracket_list([elem.get(k) for k in element_keys])
    if isinstance(elem, (list, tuple)):
        return format_bracket_list(list(elem))
    return format_leaf_value(elem)


def field_layout_raw(field: dict) -> dict:
    layout = field.get("layout") if field else None
    return layout if isinstance(layout, dict) else {}


def field_layout(field: dict) -> dict:
    layout = field_layout_raw(field)
    if layout.get("mode") == "split":
        return layout
    return {}


def field_int_base(field: dict):
    return field_layout_raw(field).get("intBase")


def field_split_width(field: dict, sample_value=None) -> int:
    layout = field_layout(field)
    if not layout:
        return 1
    col_span = int(layout.get("colSpan") or 1)
    keys = layout.get("keys") or []
    needed = col_span
    if keys:
        element_span = int(layout.get("elementSpan") or len(keys) or 1)
        if isinstance(sample_value, list):
            needed = max(col_span, len(sample_value) * element_span)
        elif isinstance(sample_value, dict):
            needed = max(col_span, element_span)
    else:
        if isinstance(sample_value, list):
            needed = max(col_span, len(sample_value))
    return max(1, needed)


def expand_split_constraint_cells(field: dict, width: int) -> list:
    layout = field_layout(field)
    keys = layout.get("keys") or []
    if not keys:
        return [""] * width
    element_span = int(layout.get("elementSpan") or len(keys) or 1)
    cells = []
    for i in range(width):
        key = keys[i % element_span]
        cells.append(".%s" % key)
    return cells


def expand_split_data_cells(field: dict, value, width: int) -> list:
    layout = field_layout(field)
    field_type = field.get("type") or "int32"
    int_base = field_int_base(field)
    if not layout:
        return [format_cell_value(field_type, value, int_base)]
    keys = layout.get("keys") or []
    cells = [None] * width
    if keys:
        element_span = int(layout.get("elementSpan") or len(keys) or 1)
        if isinstance(value, dict):
            for i, key in enumerate(keys):
                if i < width:
                    cells[i] = format_leaf_value(value.get(key), int_base)
        elif isinstance(value, list):
            for elem_idx, elem in enumerate(value):
                base = elem_idx * element_span
                if isinstance(elem, dict):
                    for i, key in enumerate(keys):
                        pos = base + i
                        if pos < width:
                            cells[pos] = format_leaf_value(elem.get(key), int_base)
                elif base < width:
                    cells[base] = format_leaf_value(elem, int_base)
        elif value is not None and width > 0:
            cells[0] = format_leaf_value(value, int_base)
    else:
        if isinstance(value, list):
            for i, elem in enumerate(value):
                if i < width:
                    cells[i] = format_split_element_cell(field_type, layout, elem)
        elif value is not None and width > 0:
            cells[0] = format_cell_value(field_type, value, int_base)
    return cells


def apply_text_number_format(cell) -> None:
    if cell.value is None:
        cell.value = ""
    elif not isinstance(cell.value, str):
        cell.value = str(cell.value)
    cell.number_format = "@"


def apply_export_column_widths(ws, max_col: int) -> None:
    from openpyxl.utils import get_column_letter

    for c in range(1, max(1, max_col) + 1):
        ws.column_dimensions[get_column_letter(c)].width = EXPORT_COL_WIDTH


def paint_header_black(ws, max_row: int, max_col: int) -> None:
    fill = PatternFill(start_color="FF000000", end_color="FF000000", fill_type="solid")
    font = Font(color="FFFFFFFF", bold=True)
    thin = Side(style="thin", color="FF9E9E9E")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for r in range(1, max_row + 1):
        for c in range(1, max_col + 1):
            cell = ws.cell(row=r, column=c)
            # Keep None as None (empty "" breaks constraint-row parsing).
            cell.fill = fill
            cell.font = font
            cell.border = border
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=False)


def save_workbook(wb, xlsx_out: Path) -> None:
    tmp = xlsx_out.with_name(xlsx_out.stem + ".__export_tmp__.xlsx")
    try:
        wb.save(tmp)
        try:
            if xlsx_out.exists():
                xlsx_out.unlink()
            tmp.replace(xlsx_out)
        except OSError as e:
            raise SystemExit(
                "无法写入导出文件（可能正被 Excel/WPS 打开）: %s\n请关闭后重试。\n%s"
                % (xlsx_out, e)
            ) from e
    except PermissionError as e:
        raise SystemExit(
            "无法写入导出文件（可能正被 Excel/WPS 打开）: %s\n请关闭后重试。\n%s"
            % (xlsx_out, e)
        ) from e
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def keyed_schema_fields(fields: list) -> list:
    """Ensure id is first for 2D tables."""
    user = []
    id_field = None
    for f in fields or []:
        n = (f.get("name") or "").strip()
        if not n:
            continue
        if n.lower() == "id":
            id_field = dict(f)
            id_field["name"] = "id"
        else:
            user.append(f)
    if id_field is None:
        id_field = {"name": "id", "type": "int32", "displayName": "id"}
    return [id_field] + user


def default_xlsx_path(schema: dict, out_dir: Path) -> Path:
    workbook = schema.get("workbook")
    if workbook:
        return Path(out_dir) / os.path.basename(workbook)
    name = schema.get("name") or "table"
    sheet_name = schema.get("sheetName") or "data"
    # Fallback when workbook meta missing: stem from logical name.
    if sheet_name != "data" and name.endswith("_" + sheet_name):
        stem = name[: -(len(sheet_name) + 1)]
    else:
        stem = name
    return Path(out_dir) / ("%s.xlsx" % stem)


def sheet_title_from_schema(schema: dict) -> str:
    """Excel sheet tab title.

    ``data`` sheets stay as ``data`` (display comes from workbook ``name@中文``).
    Other sheets may be ``SheetName@displayName``.
    """
    sheet_name = schema.get("sheetName") or "data"
    disp = schema.get("displayName") or schema.get("comment") or ""
    if sheet_name != "data" and disp:
        title = "%s@%s" % (sheet_name, disp)
    else:
        title = sheet_name
    # Excel sheet title limits
    title = re.sub(r'[:\\/?*\[\]]', "_", title)
    return title[:31] or "data"


def is_enum_schema(schema: dict) -> bool:
    """Enum schemas are kind=0 with enumType."""
    return bool(schema and schema.get("enumType"))


def is_class_schema(schema: dict) -> bool:
    if not schema:
        return False
    if is_enum_schema(schema):
        return False
    kind = schema.get("kind")
    if kind == KIND_CLASS:
        return True
    if kind != KIND_1D:
        return False
    workbook = os.path.basename(schema.get("workbook") or "")
    if workbook == CLASS_WORKBOOK:
        return True
    # Class schemas: name == typename (tables usually differ, e.g. entity_Hero vs Entity_Hero)
    name = schema.get("name") or ""
    type_name = schema.get("typename") or ""
    return bool(name) and name == type_name


def fill_worksheet_from_schema(ws, schema: dict, data) -> None:
    """Write one sheet's header + rows into an existing worksheet."""
    fields = schema.get("fields") or []
    kind = schema.get("kind", KIND_1D)

    if kind == KIND_1D:
        header = ["##key", "type", "value", "desc", "tags", "##end"]
        ws.append(header)
        obj = data if isinstance(data, dict) else (
            data[0] if isinstance(data, list) and data else {}
        )
        data_row = 1
        for f in fields:
            n = f.get("name") or ""
            if not n:
                continue
            typ = f.get("type") or "int32"
            data_row += 1
            cell_val = format_cell_value(
                typ,
                obj.get(n) if isinstance(obj, dict) else None,
                field_int_base(f),
            )
            ws.append(
                [
                    n,
                    typ,
                    cell_val,
                    f.get("displayName") or f.get("comment") or n,
                    format_tags_cell(f.get("tags"), f.get("group")),
                    "",
                ]
            )
            apply_text_number_format(ws.cell(data_row, 1))
            apply_text_number_format(ws.cell(data_row, 2))
            apply_text_number_format(ws.cell(data_row, 4))
            if is_excel_text_type(typ) or field_int_base(f) in (16, 2):
                apply_text_number_format(ws.cell(data_row, 3))
            rem = field_remarks(f)
            if rem:
                ws.cell(data_row, 4).comment = Comment(rem, "xls2cfg")
        paint_header_black(ws, 1, len(header))
        apply_export_column_widths(ws, len(header))
    else:
        fields = keyed_schema_fields(fields)
        named = [f for f in fields if f.get("name")]
        rows = [r for r in (data if isinstance(data, list) else []) if isinstance(r, dict)]

        # Expand each logical field into 1..N Excel columns (layout.colSpan,
        # grown if any data row needs more slots).
        col_specs = []  # (field, width, start_col_1based)
        col = 1
        for f in named:
            fname = f.get("name")
            width = field_split_width(f, None)
            for r in rows:
                width = max(width, field_split_width(f, r.get(fname)))
            col_specs.append((f, width, col))
            col += width
        end_col = col  # includes trailing ##end column index

        remarks_row = []
        names_row = []
        types_row = []
        constraints_row = []
        tags_row = []
        for f, width, _start in col_specs:
            remarks_row.append(f.get("displayName") or f.get("comment") or f.get("name") or "")
            remarks_row.extend([""] * (width - 1))
            names_row.append(f.get("name"))
            names_row.extend([None] * (width - 1))
            types_row.append(f.get("type") or "int32")
            types_row.extend([None] * (width - 1))
            constraints_row.extend(expand_split_constraint_cells(f, width))
            # Non-split fields keep their constraint text on the first column.
            if width == 1 and not field_layout(f):
                constraints_row[-1] = f.get("constraint") or ""
            tags_row.append(format_tags_cell(f.get("tags"), f.get("group")))
            tags_row.extend([""] * (width - 1))

        remarks_row.append("##end")
        names_row.append("")
        types_row.append("")
        constraints_row.append("")
        tags_row.append("")

        ws.append(remarks_row)
        ws.append(names_row)
        ws.append(types_row)
        ws.append(constraints_row)
        ws.append(tags_row)

        paint_header_black(ws, 5, end_col)
        apply_export_column_widths(ws, end_col)
        for f, width, start_col in col_specs:
            rem = field_remarks(f)
            if rem:
                ws.cell(1, start_col).comment = Comment(rem, "xls2cfg")

        # Merge header cells (rows 1-3) after styling (MergedCell is read-only).
        for f, width, start_col in col_specs:
            if width <= 1:
                continue
            end = start_col + width - 1
            for row_idx in (1, 2, 3):
                ws.merge_cells(
                    start_row=row_idx,
                    start_column=start_col,
                    end_row=row_idx,
                    end_column=end,
                )

        text_cols = set()
        for f, width, start_col in col_specs:
            if field_layout(f) or is_excel_text_type(f.get("type") or ""):
                for c in range(start_col, start_col + width):
                    text_cols.add(c)

        for r in rows:
            line = []
            for f, width, _start in col_specs:
                cells = expand_split_data_cells(f, r.get(f.get("name")), width)
                line.extend(cells)
            line.append("")
            ws.append(line)
            row_idx = ws.max_row
            for c in text_cols:
                cell = ws.cell(row_idx, c)
                if isinstance(cell.value, str) or cell.value is None:
                    apply_text_number_format(cell)


def write_excel_from_schema_json(schema: dict, data, xlsx_out: Path) -> Path:
    if openpyxl is None:
        raise SystemExit("openpyxl required: pip install openpyxl")
    if is_enum_schema(schema):
        return write_enum_workbook([schema], Path(xlsx_out))
    if is_class_schema(schema):
        return write_class_workbook([schema], Path(xlsx_out))

    xlsx_out = Path(xlsx_out)
    xlsx_out.parent.mkdir(parents=True, exist_ok=True)
    if xlsx_out.suffix.lower() != ".xlsx":
        xlsx_out = xlsx_out.with_suffix(".xlsx")
    # Rewrite default stem (schema name) to workbook filename when meta present.
    name = schema.get("name") or "table"
    if xlsx_out.stem == name and schema.get("workbook"):
        xlsx_out = default_xlsx_path(schema, xlsx_out.parent)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_title_from_schema(schema)
    fill_worksheet_from_schema(ws, schema, data)
    save_workbook(wb, xlsx_out)
    return xlsx_out


def write_multi_sheet_workbook(sheet_items, xlsx_out: Path) -> Path:
    """sheet_items: [(sheetIndex, schema, data), ...] sorted by sheetIndex."""
    if openpyxl is None:
        raise SystemExit("openpyxl required: pip install openpyxl")
    xlsx_out = Path(xlsx_out)
    xlsx_out.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    first = True
    for _idx, schema, data in sheet_items:
        title = sheet_title_from_schema(schema)
        if first:
            ws = wb.active
            ws.title = title
            first = False
        else:
            ws = wb.create_sheet(title)
        fill_worksheet_from_schema(ws, schema, data)
    save_workbook(wb, xlsx_out)
    return xlsx_out


def write_class_workbook(class_schemas, xlsx_out: Path) -> Path:
    """Restore __class__.xlsx from kind=0 class schemas (fields as list<__Field__>)."""
    if openpyxl is None:
        raise SystemExit("openpyxl required: pip install openpyxl")
    xlsx_out = Path(xlsx_out)
    if xlsx_out.is_dir() or xlsx_out.suffix.lower() != ".xlsx":
        xlsx_out = Path(xlsx_out) / CLASS_WORKBOOK
    xlsx_out.parent.mkdir(parents=True, exist_ok=True)

    schemas = sorted(class_schemas, key=lambda s: s.get("name") or "")
    max_fields = 1
    for s in schemas:
        max_fields = max(max_fields, len(s.get("fields") or []))
    field_width = max_fields * 4

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "data"

    remarks = ["类型名", "备注名", "字段定义"] + [None] * (field_width - 1) + ["##end"]
    names = ["typename", "comment", "fields"] + [None] * (field_width - 1)
    types = ["string", "string", "list<__Field__>"] + [None] * (field_width - 1)
    constraints = [None, None]
    for i in range(field_width):
        constraints.append([".name", ".type", ".comment", ".tags"][i % 4])
    tags = [None] * (2 + field_width)

    ws.append(remarks)
    ws.append(names)
    ws.append(types)
    ws.append(constraints)
    ws.append(tags)

    fields_end = 2 + field_width
    end_col = fields_end + 1  # includes ##end
    # Style before merge (MergedCell values are read-only).
    paint_header_black(ws, 5, end_col)
    apply_export_column_widths(ws, end_col)
    if field_width > 1:
        for row_idx in (1, 2, 3):
            ws.merge_cells(
                start_row=row_idx,
                start_column=3,
                end_row=row_idx,
                end_column=fields_end,
            )

    for schema in schemas:
        fields = [f for f in (schema.get("fields") or []) if f.get("name")]
        line = [
            schema.get("name") or schema.get("typename") or "",
            schema.get("displayName") or schema.get("comment") or "",
        ]
        for f in fields:
            tags_val = format_tags_cell(f.get("tags"), f.get("group"))
            line.extend([
                f.get("name") or "",
                f.get("type") or "int32",
                f.get("displayName") or f.get("comment") or "",
                tags_val if tags_val else None,
            ])
        while len(line) < fields_end:
            line.append(None)
        line.append(None)  # ##end column
        ws.append(line[:end_col])

    save_workbook(wb, xlsx_out)
    return xlsx_out


def write_enum_workbook(enum_schemas, xlsx_out: Path) -> Path:
    """Restore __enum__.xlsx from enum schemas (kind=0 + enumType, fields as list<__EnumField__>)."""
    if openpyxl is None:
        raise SystemExit("openpyxl required: pip install openpyxl")
    xlsx_out = Path(xlsx_out)
    if xlsx_out.is_dir() or xlsx_out.suffix.lower() != ".xlsx":
        xlsx_out = Path(xlsx_out) / ENUM_WORKBOOK
    xlsx_out.parent.mkdir(parents=True, exist_ok=True)

    schemas = sorted(enum_schemas, key=lambda s: s.get("name") or "")
    max_fields = 1
    for s in schemas:
        max_fields = max(max_fields, len(s.get("fields") or []))
    field_width = max_fields * 4

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "data"

    remarks = ["类型名", "备注名", "底层类型", "可组合", "字段定义"] + [None] * (field_width - 1) + ["##end"]
    names = ["typename", "comment", "enumType", "flags", "fields"] + [None] * (field_width - 1)
    types = ["string", "string", "string", "bool", "list<__EnumField__>"] + [None] * (field_width - 1)
    constraints = [None, None, None, None]
    for i in range(field_width):
        constraints.append([".name", ".value", ".comment", ".tags"][i % 4])
    tags = [None] * (4 + field_width)

    ws.append(remarks)
    ws.append(names)
    ws.append(types)
    ws.append(constraints)
    ws.append(tags)

    fields_end = 4 + field_width
    end_col = fields_end + 1  # includes ##end
    paint_header_black(ws, 5, end_col)
    apply_export_column_widths(ws, end_col)
    if field_width > 1:
        for row_idx in (1, 2, 3):
            ws.merge_cells(
                start_row=row_idx,
                start_column=5,
                end_row=row_idx,
                end_column=fields_end,
            )

    for schema in schemas:
        items = [f for f in (schema.get("fields") or []) if f.get("name")]
        line = [
            schema.get("name") or schema.get("typename") or "",
            schema.get("displayName") or schema.get("comment") or "",
            schema.get("enumType") or "int32",
            1 if schema.get("flags") else 0,
        ]
        for f in items:
            tags_val = format_tags_cell(f.get("tags"), f.get("group"))
            line.extend([
                f.get("name") or "",
                f.get("value") if f.get("value") is not None else None,
                f.get("displayName") or f.get("comment") or "",
                tags_val if tags_val else None,
            ])
        while len(line) < fields_end:
            line.append(None)
        line.append(None)  # ##end column
        ws.append(line[:end_col])

    save_workbook(wb, xlsx_out)
    return xlsx_out


# --- export: schema + json/binary -> xlsx ---

def schema_binary_fields(schema: dict, tags=None) -> list:
    prev_tags = Config.tags
    if tags is not None:
        Config.tags = tags
    try:
        fields = []
        for f in schema.get("fields") or []:
            name = f.get("name")
            if not name:
                continue
            field_tags_str = f.get("tags") or ""
            field_tags = (
                [t.strip() for t in field_tags_str.split(",") if t.strip()]
                if field_tags_str else None
            )
            if not Config.isNeedExportTags(field_tags):
                continue
            fields.append((name, Type.getOrCreate(f.get("type") or "int32")))
        return fields
    finally:
        Config.tags = prev_tags


def read_binary_data(schema: dict, binary_path: Path, tags=None):
    field_types = schema_binary_fields(schema, tags=tags)
    bs = ByteStream()
    bs.ReadFile(str(binary_path))
    if schema.get("kind", KIND_1D) == KIND_1D:
        row = {}
        for name, typ in field_types:
            row[name] = bs.ReadValue(typ)
        return row
    data_row = bs.ReadUInt16()
    rows = []
    for _ in range(data_row):
        row = {}
        for name, typ in field_types:
            row[name] = bs.ReadValue(typ)
        rows.append(row)
    return rows


def load_export_data(schema: dict, json_path=None, binary_path=None, tags=None):
    json_path = Path(json_path) if json_path else None
    binary_path = Path(binary_path) if binary_path else None
    if json_path and json_path.exists():
        return json.loads(json_path.read_text(encoding="utf-8"))
    if binary_path and binary_path.exists():
        return read_binary_data(schema, binary_path, tags=tags)
    return {} if schema.get("kind", KIND_1D) == KIND_1D else []


def register_class_schemas_from_dir(schema_dir: Path) -> None:
    """Load kind=0 (or legacy) class schemas into Type registry for list<Class> encode."""
    schema_dir = Path(schema_dir)
    if not schema_dir.is_dir():
        return
    for path in sorted(schema_dir.glob("*.json")):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not is_class_schema(obj):
            continue
        class_name = obj.get("typename") or ""
        if not class_name:
            continue
        existing = Type.get(class_name)
        if isinstance(existing, Type) and existing.isClass() and existing.fields:
            continue
        fields = []
        for f in obj.get("fields") or []:
            n = f.get("name")
            if not n:
                continue
            fields.append({
                "type": f.get("type") or "int32",
                "name": n,
                "comment": f.get("displayName") or f.get("comment") or "",
                "tags": None,
                "remarks": f.get("remarks") or "",
                "group": f.get("group"),
            })
        if not fields:
            continue
        type_comment = obj.get("displayName") or obj.get("comment") or ""
        if isinstance(existing, Type):
            existing.fields = []
            existing.idFieldIdx = -1
            for f in fields:
                existing.defineField(
                    f["type"], f["name"], comment=f["comment"], remarks=f["remarks"],
                    group=f.get("group"),
                )
            if type_comment:
                existing.comment = type_comment
        else:
            typ = Type.createClass(class_name, fields)
            if type_comment:
                typ.comment = type_comment


def register_enum_schemas_from_dir(schema_dir: Path) -> None:
    """Load enum schemas (kind=0 + enumType) into Type registry."""
    schema_dir = Path(schema_dir)
    if not schema_dir.is_dir():
        return
    for path in sorted(schema_dir.glob("*.json")):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not is_enum_schema(obj):
            continue
        enum_name = obj.get("typename") or ""
        if not enum_name:
            continue
        existing = Type.get(enum_name)
        if isinstance(existing, Type) and existing.isEnum():
            continue
        items = []
        for f in obj.get("fields") or []:
            n = f.get("name")
            if not n:
                continue
            items.append({
                "name": n,
                "value": f.get("value"),
                "comment": f.get("displayName") or f.get("comment") or "",
                "tags": None,
            })
        Type.createEnum(
            enum_name,
            enumType=obj.get("enumType") or "int32",
            items=items,
            comment=obj.get("displayName") or obj.get("comment") or None,
            flags=bool(obj.get("flags")),
        )


def export_one(
    schema_path: Path,
    xlsx_out: Path,
    json_path=None,
    binary_path=None,
    tags=None,
) -> Path:
    schema_path = Path(schema_path)
    register_class_schemas_from_dir(schema_path.parent)
    register_enum_schemas_from_dir(schema_path.parent)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    data = load_export_data(
        schema, json_path=json_path, binary_path=binary_path, tags=tags
    )
    return write_excel_from_schema_json(schema, data, Path(xlsx_out))


def export_dir(from_dir: Path, export_xlsx: Path, tags=None) -> list:
    """Batch: {from_dir}/schema + json/ or binary/ -> export_xlsx dir.

    Tables with the same workbook are merged into one multi-sheet xlsx (sheetIndex order).
    kind=0 class schemas are written to __class__.xlsx.
    """
    schema_dir = Path(from_dir) / "schema"
    json_dir = Path(from_dir) / "json"
    binary_dir = Path(from_dir) / "binary"
    export_xlsx = Path(export_xlsx)
    export_xlsx.mkdir(parents=True, exist_ok=True)
    results = []
    if not schema_dir.is_dir():
        raise SystemExit("schema dir not found: %s" % schema_dir)

    register_class_schemas_from_dir(schema_dir)
    register_enum_schemas_from_dir(schema_dir)
    groups = {}  # workbook filename -> [(sheetIndex, name, schema, data)]
    class_schemas = []
    enum_schemas = []

    for schema_path in sorted(schema_dir.glob("*.json")):
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        if is_enum_schema(schema):
            enum_schemas.append(schema)
            continue
        if is_class_schema(schema):
            class_schemas.append(schema)
            continue
        name = schema_path.stem
        json_path = json_dir / (name + ".json")
        binary_path = binary_dir / (name + ".bytes")
        data = load_export_data(
            schema,
            json_path=json_path if json_path.exists() else None,
            binary_path=binary_path if binary_path.exists() else None,
            tags=tags,
        )
        wb_name = os.path.basename(
            schema.get("workbook") or default_xlsx_path(schema, export_xlsx).name
        )
        sheet_index = schema.get("sheetIndex", 0)
        groups.setdefault(wb_name, []).append((sheet_index, name, schema, data))

    for wb_name, items in sorted(groups.items()):
        items.sort(key=lambda x: (x[0], x[1]))
        out = export_xlsx / wb_name
        path = write_multi_sheet_workbook(
            [(idx, schema, data) for idx, _name, schema, data in items],
            out,
        )
        results.append(str(path))
        print("export", path)

    if class_schemas:
        path = write_class_workbook(class_schemas, export_xlsx / CLASS_WORKBOOK)
        results.append(str(path))
        print("export", path)
    if enum_schemas:
        path = write_enum_workbook(enum_schemas, export_xlsx / ENUM_WORKBOOK)
        results.append(str(path))
        print("export", path)
    return results


# ---- import: xlsx -> schema + json ----

def _top_level_comma(s):
    depth = 0
    for i, ch in enumerate(s or ""):
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth -= 1
        elif ch == "," and depth == 0:
            return i
    return -1


def iter_type_atoms(type_str):
    t = (type_str or "").strip()
    if not t:
        return
    if t.startswith("list<") and t.endswith(">"):
        for a in iter_type_atoms(t[5:-1].strip()):
            yield a
        return
    if t.startswith("map<") and t.endswith(">"):
        inner = t[4:-1]
        comma = _top_level_comma(inner)
        if comma < 0:
            yield t
            return
        for a in iter_type_atoms(inner[:comma].strip()):
            yield a
        for a in iter_type_atoms(inner[comma + 1 :].strip()):
            yield a
        return
    yield t


def collect_needed_class_names(type_strings, class_names_from_file):
    """Closure of __class__ type names referenced by type_strings."""
    class_set = set(class_names_from_file or [])
    needed = set()

    def add_deps(name):
        if name not in class_set or name in needed:
            return
        needed.add(name)
        typ = Type.get(name)
        if typ is None or not typ.isClass() or not typ.fields:
            return
        for f in typ.fields:
            ft = f.type.fullTypename if f.type else ""
            for atom in iter_type_atoms(ft):
                add_deps(atom)

    for ts in type_strings or []:
        for atom in iter_type_atoms(ts):
            add_deps(atom)
    return needed


def write_class_schema(typ, schema_dir, json_dir=None, sheet_index=0):
    """Write kind=0 class schema. Filename = type name.

    Does not write json data (kind=0 is schema/ClassDecl only).
    ``json_dir`` is accepted for call-site compatibility but ignored.
    """
    if typ is None or not typ.isClass() or typ.typename in ("__Field__", "__EnumField__"):
        return ""
    schema = typ.to_schema(name=typ.typename, kind=KIND_CLASS, class_name=typ.typename)
    out = {
        "kind": KIND_CLASS,
        "name": typ.typename,
    }
    if schema.get("displayName"):
        out["displayName"] = schema["displayName"]
    out["typename"] = typ.typename
    out["workbook"] = CLASS_WORKBOOK
    out["sheetName"] = "data"
    out["sheetIndex"] = sheet_index
    out["fields"] = schema["fields"]
    return _write_class_schema_dict(out, schema_dir, json_dir=None)


def write_enum_schema(typ, schema_dir, sheet_index=0):
    """Write enum schema (kind=0 + enumType). Filename = type name."""
    if typ is None or not typ.isEnum():
        return ""
    schema = typ.to_schema(name=typ.typename, kind=KIND_CLASS, class_name=typ.typename)
    out = {
        "kind": KIND_CLASS,
        "name": typ.typename,
    }
    if schema.get("displayName"):
        out["displayName"] = schema["displayName"]
    out["typename"] = typ.typename
    out["enumType"] = schema.get("enumType") or "int32"
    if schema.get("flags"):
        out["flags"] = True
    out["workbook"] = ENUM_WORKBOOK
    out["sheetName"] = "data"
    out["sheetIndex"] = sheet_index
    out["fields"] = schema["fields"]
    return _write_class_schema_dict(out, schema_dir, json_dir=None)


def _write_class_schema_dict(out, schema_dir, json_dir=None):
    os.makedirs(schema_dir, exist_ok=True)
    name = out.get("name") or ""
    schema_path = os.path.join(schema_dir, name + ".json")
    data = json.dumps(out, ensure_ascii=False, indent=2)
    with open(schema_path, "w", encoding="utf-8", newline="\n") as fd:
        fd.write(data)
        if not data.endswith("\n"):
            fd.write("\n")
    # kind=0: never write table/json data
    print("write", schema_dir, name)
    return schema_path


def write_class_schemas_from_excel(excel_dir, schema_dir, class_path=None):
    """Write kind=0 schemas for all classes in __class__ xlsx+json (json overrides).

    Does not mutate the Type registry used by data export.
    ``class_path`` defaults to ``excel_dir``.
    """
    from XlsParser.XlsClass import collect_class_defs
    from XlsParser.Type import Field as TypeField

    base = class_path if class_path is not None else excel_dir
    prev_tags = Config.tags
    Config.tags = []
    written = []
    try:
        defs = collect_class_defs(base, apply_tags_filter=False)
        for typename, entry in defs.items():
            fields = []
            for f in entry.get("fields") or []:
                if not f.get("type") or not f.get("name"):
                    continue
                item = {
                    "name": f["name"],
                    "type": f["type"],
                }
                if f.get("comment"):
                    item["displayName"] = f["comment"]
                tags = TypeField.format_tags(f.get("tags"))
                if tags:
                    item["tags"] = tags
                if f.get("group"):
                    item["group"] = f["group"]
                fields.append(item)
            if not fields:
                continue
            out = {
                "kind": KIND_CLASS,
                "name": typename,
            }
            if entry.get("displayName"):
                out["displayName"] = entry["displayName"]
            out["typename"] = typename
            out["workbook"] = CLASS_WORKBOOK
            out["sheetName"] = "data"
            out["sheetIndex"] = 0
            out["fields"] = fields
            _write_class_schema_dict(out, schema_dir, json_dir=None)
            written.append(typename)
    finally:
        Config.tags = prev_tags
    return written


def write_enum_schemas_from_excel(excel_dir, schema_dir, enum_path=None):
    """Write enum schemas for all enums in __enum__ xlsx+json (json overrides)."""
    from XlsParser.XlsEnum import collect_enum_defs
    from XlsParser.Type import Field as TypeField

    base = enum_path if enum_path is not None else excel_dir
    prev_tags = Config.tags
    Config.tags = []
    written = []
    try:
        defs = collect_enum_defs(base, apply_tags_filter=False)
        for typename, entry in defs.items():
            fields = []
            for f in entry.get("fields") or []:
                if not f.get("name"):
                    continue
                raw_val = f.get("value")
                value = raw_val
                if raw_val is not None and raw_val != "":
                    ok, parsed = Type.parse_enum_int(raw_val)
                    if ok:
                        value = parsed
                item = {
                    "name": f["name"],
                    "value": value,
                }
                if f.get("comment"):
                    item["displayName"] = f["comment"]
                tags = TypeField.format_tags(f.get("tags"))
                if tags:
                    item["tags"] = tags
                if f.get("group"):
                    item["group"] = f["group"]
                fields.append(item)
            out = {
                "kind": KIND_CLASS,
                "name": typename,
            }
            if entry.get("displayName"):
                out["displayName"] = entry["displayName"]
            out["typename"] = typename
            out["enumType"] = entry.get("enumType") or "int32"
            if entry.get("flags"):
                out["flags"] = True
            out["workbook"] = ENUM_WORKBOOK
            out["sheetName"] = "data"
            out["sheetIndex"] = 0
            out["fields"] = fields
            _write_class_schema_dict(out, schema_dir, json_dir=None)
            written.append(typename)
    finally:
        Config.tags = prev_tags
    return written


def import_xlsx_to_dirs(
    xlsx_path,
    schema_dir,
    json_dir,
    sheet_name=None,
):
    """Import workbook sheet(s) to schema+json dirs (no tags filter).

    Loads sibling __class__/__enum__.xlsx before parse so user types resolve.
    Referenced class/enum types are written as kind=0 schemas (enums have enumType).
    Importing __class__/__enum__.xlsx itself writes those schemas only.
    """
    if load_workbook is None:
        raise SystemExit("openpyxl required: pip install openpyxl")

    Config.tags = []
    Config.pretty = True
    Config.classNameFirstUpper = True
    xlsx_path = os.path.abspath(xlsx_path)
    schema_dir = os.path.abspath(schema_dir)
    json_dir = os.path.abspath(json_dir)
    if not os.path.isdir(schema_dir):
        os.makedirs(schema_dir)
    if not os.path.isdir(json_dir):
        os.makedirs(json_dir)

    excel_dir = os.path.dirname(xlsx_path)
    fileName = os.path.basename(xlsx_path)
    enum_names = readEnum(excel_dir) or []
    class_names = readClass(excel_dir) or []

    if fileName.startswith("__enum__"):
        deps = []
        for name in enum_names:
            path = write_enum_schema(Type.get(name), schema_dir, sheet_index=0)
            if path:
                deps.append({
                    "name": name,
                    "kind": KIND_CLASS,
                    "schema": path,
                })
        print(json.dumps({
            "ok": True,
            "name": ENUM_WORKBOOK,
            "tables": [],
            "deps": deps,
            "count": len(deps),
        }, ensure_ascii=False))
        return deps

    if fileName.startswith("__class__"):
        deps = []
        for idx, name in enumerate(class_names):
            path = write_class_schema(Type.get(name), schema_dir, json_dir, sheet_index=0)
            if path:
                deps.append({
                    "name": name,
                    "kind": KIND_CLASS,
                    "schema": path,
                })
        print(json.dumps({
            "ok": True,
            "name": CLASS_WORKBOOK,
            "tables": [],
            "deps": deps,
            "count": len(deps),
        }, ensure_ascii=False))
        return deps

    wb = load_workbook(filename=xlsx_path, data_only=True)
    tables = []
    type_strings = []
    try:
        for idx, sn in enumerate(wb.sheetnames):
            if not is_importable_sheet_title(sn):
                continue
            logical, _ = split_at_display(sn)
            if sheet_name and sn != sheet_name and logical != sheet_name:
                continue
            sheet = Sheet(wb[sn], fileName, sn, idx)
            schema_parser = Xls2SchemaParser(sheet, schema_dir)
            schema_parser.parse()
            json_parser = Xls2JsonParser(sheet, json_dir)
            json_parser.parse()
            schema_path = os.path.join(schema_dir, sheet.filename + ".json")
            tables.append({
                "name": sheet.filename,
                "kind": KIND_1D if sheet.singleton else KIND_2D,
                "sheet": sheet.sheetName,
                "sheetIndex": sheet.sheetIndex,
                "workbook": sheet.xlsFilename,
                "schema": schema_path,
                "data": os.path.join(json_dir, sheet.filename + ".json"),
            })
            try:
                schema_obj = json.loads(Path(schema_path).read_text(encoding="utf-8"))
                for f in schema_obj.get("fields") or []:
                    type_strings.append(f.get("type") or "")
            except Exception:
                pass
    finally:
        wb.close()
    if not tables:
        raise SystemExit("workbook has no importable sheets")

    deps = []
    if class_names:
        needed = collect_needed_class_names(type_strings, class_names)
        for name in sorted(needed):
            path = write_class_schema(Type.get(name), schema_dir, json_dir)
            if path:
                deps.append({
                    "name": name,
                    "kind": KIND_CLASS,
                    "schema": path,
                })
    if enum_names:
        enum_set = set(enum_names)
        needed_enums = set()
        for ts in type_strings:
            for atom in iter_type_atoms(ts):
                if atom in enum_set:
                    needed_enums.add(atom)
        for name in sorted(needed_enums):
            path = write_enum_schema(Type.get(name), schema_dir)
            if path:
                deps.append({
                    "name": name,
                    "kind": KIND_CLASS,
                    "schema": path,
                })

    print(json.dumps({
        "ok": True,
        "name": tables[0]["name"],
        "tables": tables,
        "deps": deps,
        "count": len(tables),
    }, ensure_ascii=False))
    return tables
