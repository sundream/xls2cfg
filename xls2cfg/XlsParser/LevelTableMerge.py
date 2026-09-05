#coding: utf-8
#@author sundream
#@date 2026-09-02
"""Level-table merge helpers (export validation + runtime WithLevel type/schema).

Schema convention (base table ``id`` column constraint)::

    levelTable=skillLevel

- Base table primary key: ``int32`` / ``uint32``.
- Level table primary key: ``int64`` / ``uint64``, ``baseId * factor + level`` (``level`` 从 **0** 起，范围 0..999).
- Base table must define ``maxLevel`` / ``int32``；导出校验 ``maxLevel >= max(level, 1)``。
- ``{base}WithLevel`` is a **runtime-only merged view** (schema carries ``baseTable`` + ``levelTable``):
  generates C# type + schema JSON, **no** ``{base}WithLevel.json`` data file.
- Generated ``{base}WithLevel(baseRow, levelRow)`` copies base then applies level overrides; ``Id`` equals ``levelRow.Id``.
- ``{base}WithLevel(baseRow, level)`` copies base only; ``Id = baseId * factor + level``，``Level = level``（等级表无对应行时使用）。
- ``MergeTable(baseTable, levelTable)`` 遍历 base 表每行的 ``level=0..maxLevel``；有等级行则合并，否则用 base 行。
- Level table must define ``level`` / ``int32`` (等级，从 0 起).
"""

from __future__ import annotations

import json
import os

DEFAULT_LEVEL_ID_FACTOR = 1000
MAX_LEVEL_PER_BASE = 999


_ID_PROMOTE = {
    "int32": "int64",
    "int": "int64",
    "uint32": "uint64",
    "uint": "uint64",
}


def is_with_level_schema(schema) -> bool:
    """True for synthesized ``{base}WithLevel`` schema (has ``baseTable``)."""
    return bool(schema and schema.get("baseTable"))


def promote_id_type_name(base_id_type: str) -> str:
    """Promote base-table id scalar type to WithLevel id type."""
    atom = (base_id_type or "int32").strip()
    promoted = _ID_PROMOTE.get(atom)
    if promoted is None:
        raise Exception(
            "unsupported base id type '%s' for WithLevel (expect int32 or uint32)" % atom
        )
    return promoted


def parse_level_table_from_constraint(constraint):
    """Parse ``levelTable=xxx`` from Excel/schema constraint text or dict."""
    if not constraint:
        return None
    if isinstance(constraint, dict):
        value = constraint.get("levelTable")
        if value is None:
            return None
        text = str(value).strip()
        return text or None
    text = str(constraint).strip()
    if not text:
        return None
    for part in text.split(";"):
        part = part.strip()
        if not part:
            continue
        if part.startswith("levelTable="):
            name = part.split("=", 1)[1].strip()
            return name or None
    return None


def parse_level_table_from_schema(schema):
    """Return bound level-table stem from a base-table schema object."""
    if not schema:
        return None
    for field in schema.get("fields") or []:
        if field.get("name") == "id":
            return parse_level_table_from_constraint(field.get("constraint"))
    if schema.get("fields"):
        return parse_level_table_from_constraint(schema["fields"][0].get("constraint"))
    return None


def remove_level_table_constraint(constraint) -> str:
    """Strip ``levelTable=...`` from constraint text for derived WithLevel schema."""
    if not constraint:
        return ""
    if isinstance(constraint, dict):
        parts = []
        for key, value in constraint.items():
            if key.startswith("_") or key == "levelTable":
                continue
            if value is True:
                parts.append(key)
            elif value is not None:
                parts.append("%s=%s" % (key, value))
        return ";".join(parts)
    parts = []
    for part in str(constraint).split(";"):
        part = part.strip()
        if not part or part.startswith("levelTable="):
            continue
        parts.append(part)
    return ";".join(parts)


def decode_level_id(row_id, factor=DEFAULT_LEVEL_ID_FACTOR):
    row_id = int(row_id)
    factor = int(factor)
    level = row_id % factor
    base_id = row_id // factor
    return base_id, level


def with_level_table_name(base_table_name: str) -> str:
    return base_table_name + "WithLevel"


def extract_sheet_row_dicts(sheet):
    """Convert a loaded Sheet to list[dict] (merge columns stored at start col only)."""
    rows = []
    for row_idx in range(sheet.dataRow):
        data = {}
        for col in range(sheet.maxCol):
            key = sheet.col2key.get(col)
            if not key:
                continue
            if col in sheet.mergeCells:
                merge_cell = sheet.mergeCells[col]
                if col != merge_cell.startCol:
                    continue
            data[key] = sheet.rows[row_idx][col]
        rows.append(data)
    return rows


def validate_level_rows(base_ids, level_row_map, level_id_factor=DEFAULT_LEVEL_ID_FACTOR):
    """Ensure every level row points at an existing base id and valid level."""
    for row_id in level_row_map:
        base_id, level = decode_level_id(row_id, level_id_factor)
        if level < 0 or level > MAX_LEVEL_PER_BASE:
            raise Exception(
                "invalid level row id=%s (level must be 0..%d)"
                % (row_id, MAX_LEVEL_PER_BASE)
            )
        if base_id not in base_ids:
            raise Exception(
                "level row id=%s references missing base id=%s" % (row_id, base_id)
            )


def validate_base_table_max_level(base_rows, sheet_name):
    """Base table ``maxLevel`` must be >= ``level`` and >= 1 when both fields exist."""
    for row in base_rows:
        if "maxLevel" not in row:
            continue
        max_level = row.get("maxLevel")
        if max_level is None:
            continue
        level = row.get("level", 0)
        if level is None:
            level = 0
        min_required = max(int(level), 1)
        if int(max_level) < min_required:
            raise Exception(
                "base table '%s' id=%s: maxLevel=%s must be >= level(%s) and >= 1"
                % (sheet_name, row.get("id"), max_level, level)
            )


def validate_level_table_has_level_field(level_sheet, level_table_name):
    """Level table must define ``level`` / ``int32`` (等级)."""
    for col in range(level_sheet.maxCol):
        key = level_sheet.col2key.get(col)
        if key != "level":
            continue
        typ = level_sheet.col2type.get(col)
        if typ is None:
            continue
        if typ.typename not in ("int32", "int"):
            raise Exception(
                "level table '%s' field 'level' must be int32, got '%s'"
                % (level_table_name, typ.typename)
            )
        return
    raise Exception(
        "level table '%s' must define int32 field 'level' (等级)"
        % level_table_name
    )


def validate_level_table_bindings(sheets, level_id_factor=DEFAULT_LEVEL_ID_FACTOR):
    """Validate base↔level table bindings at export; does not emit WithLevel data."""
    for sheet_name, sheet in sheets.items():
        if getattr(sheet, "singleton", False) or sheet.splitCol != -1:
            continue
        level_table_name = sheet.getConstraint(sheet.idCol, "levelTable")
        if not level_table_name:
            continue
        level_sheet = sheets.get(level_table_name)
        if level_sheet is None:
            raise Exception(
                "levelTable '%s' not found for base table '%s'"
                % (level_table_name, sheet_name)
            )
        validate_level_table_has_level_field(level_sheet, level_table_name)
        base_rows = extract_sheet_row_dicts(sheet)
        level_rows = extract_sheet_row_dicts(level_sheet)
        base_ids = set()
        for row in base_rows:
            if "id" not in row:
                raise Exception("base table '%s' row missing id" % sheet_name)
            base_ids.add(row["id"])
        level_row_map = {}
        for row in level_rows:
            if "id" not in row:
                raise Exception("level table '%s' row missing id" % level_table_name)
            level_row_map[row["id"]] = row
        validate_base_table_max_level(base_rows, sheet_name)
        validate_level_rows(base_ids, level_row_map, level_id_factor)
        print(
            "validateLevelTable,base=%s,level=%s,baseRows=%d,levelRows=%d"
            % (sheet_name, level_table_name, len(base_rows), len(level_rows))
        )


def synthesize_with_level_schema(base_schema, level_table_name=None):
    """Build WithLevel schema JSON (type-only, runtime merge)."""
    name = base_schema.get("name")
    if not name:
        return None
    wl_name = with_level_table_name(name)
    typename = base_schema.get("typename") or name
    if typename[:1].islower():
        wl_typename = typename[:1].upper() + typename[1:] + "WithLevel"
    else:
        wl_typename = typename + "WithLevel"

    fields = []
    for field in base_schema.get("fields") or []:
        entry = dict(field)
        if entry.get("name") == "id":
            entry["type"] = promote_id_type_name(entry.get("type") or "int32")
            if entry.get("constraint"):
                cleaned = remove_level_table_constraint(entry["constraint"])
                if cleaned:
                    entry["constraint"] = cleaned
                else:
                    entry.pop("constraint", None)
        fields.append(entry)

    display = base_schema.get("displayName") or name
    return {
        "kind": base_schema.get("kind", 2),
        "name": wl_name,
        "displayName": display + " (等级合并)",
        "typename": wl_typename,
        "workbook": base_schema.get("workbook", ""),
        "sheetName": base_schema.get("sheetName", "data"),
        "sheetIndex": base_schema.get("sheetIndex", 0),
        "fields": fields,
        "baseTable": name,
        "levelTable": level_table_name,
    }


def validate_level_schema_has_level_field(schema, table_name):
    """Schema-level check: level table defines ``level`` / ``int32``."""
    for field in schema.get("fields") or []:
        if field.get("name") != "level":
            continue
        ftype = (field.get("type") or "").strip()
        if ftype not in ("int32", "int"):
            raise Exception(
                "level table '%s' field 'level' must be int32, got '%s'"
                % (table_name, ftype)
            )
        return
    raise Exception(
        "level table '%s' must define int32 field 'level' (等级)" % table_name
    )


def append_with_level_schemas(class_schemas):
    """Append synthesized WithLevel schemas for base tables bound to a level table."""
    existing = {schema.get("name") for schema in class_schemas if schema.get("name")}
    by_name = {schema.get("name"): schema for schema in class_schemas if schema.get("name")}
    extras = []
    for schema in class_schemas:
        if is_with_level_schema(schema):
            continue
        level_table = parse_level_table_from_schema(schema)
        if not level_table:
            continue
        level_schema = by_name.get(level_table)
        if level_schema is not None:
            validate_level_schema_has_level_field(level_schema, level_table)
        wl_name = with_level_table_name(schema.get("name") or "")
        if not wl_name or wl_name in existing:
            continue
        wl_schema = synthesize_with_level_schema(schema, level_table)
        if wl_schema is None:
            continue
        extras.append(wl_schema)
        existing.add(wl_name)
    if not extras:
        return class_schemas
    return list(class_schemas) + extras


def _schema_from_sheet(sheet):
    from XlsParser.Xls2SchemaParser import Xls2SchemaParser

    parser = Xls2SchemaParser(sheet, "")
    return parser.buildSchema()


def write_runtime_with_level_schemas(sheets, schema_output_dir, pretty=True):
    """Write ``{base}WithLevel`` schema JSON files (no data json)."""
    if not schema_output_dir:
        return
    os.makedirs(schema_output_dir, exist_ok=True)
    for sheet_name, sheet in sheets.items():
        if getattr(sheet, "singleton", False) or sheet.splitCol != -1:
            continue
        level_table_name = sheet.getConstraint(sheet.idCol, "levelTable")
        if not level_table_name:
            continue
        wl_name = with_level_table_name(sheet_name)
        base_schema = _schema_from_sheet(sheet)
        wl_schema = synthesize_with_level_schema(base_schema, level_table_name)
        if wl_schema is None:
            continue
        path = os.path.join(schema_output_dir, wl_name + ".json")
        text = json.dumps(wl_schema, ensure_ascii=False, indent=2 if pretty else None)
        if pretty and not text.endswith("\n"):
            text += "\n"
        with open(path, "w", encoding="utf-8", newline="\n") as fd:
            fd.write(text)
        print("write", schema_output_dir, wl_name + ".json")


def _type_fields_from_schema_fields(fields):
    from XlsParser.XlsImportExport import _schema_fields_to_type_fields
    return _schema_fields_to_type_fields(fields)


def register_with_level_types(sheets):
    """Register synthesized WithLevel Type entries for C# codegen (Excel export)."""
    from XlsParser.Type import Type

    for sheet_name, sheet in sheets.items():
        if getattr(sheet, "singleton", False) or sheet.splitCol != -1:
            continue
        level_table_name = sheet.getConstraint(sheet.idCol, "levelTable")
        if not level_table_name:
            continue
        base_schema = _schema_from_sheet(sheet)
        wl_schema = synthesize_with_level_schema(base_schema, level_table_name)
        if wl_schema is None:
            continue
        wl_typename = wl_schema.get("typename") or wl_schema.get("name")
        if not wl_typename:
            continue
        Type.unregister(wl_typename)
        typ = Type.createClass(wl_typename, _type_fields_from_schema_fields(wl_schema.get("fields")))
        typ.comment = wl_schema.get("displayName") or wl_schema.get("comment") or None
        typ.baseTable = sheet_name
        typ.levelTable = level_table_name
        if typ.fields:
            id_idx = 0
            for i, field in enumerate(typ.fields):
                if field.name == "id":
                    id_idx = i
                    break
            typ.setIdField(id_idx)
