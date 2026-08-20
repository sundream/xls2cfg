#coding:utf-8
#@author sundream
#@date 2026-08-14

import os
from collections import OrderedDict
from XlsParser.Sheet import Sheet
from XlsParser.Type import Type, parse_tags_cell
from XlsParser.Config import Config
from XlsParser.TypeDefPath import resolve_type_def_paths, load_types_json_list
from openpyxl import load_workbook

ENUM_BASENAME = "__enum__"

def createBuiltinEnumField():
    Type.createClass("__EnumField__",[
        {
            "type" : "string",
            "name" : "name",
            "comment" : "枚举字段名",
            "tags" : [],
        },
        {
            "type" : "string",
            "name" : "value",
            "comment" : "枚举值",
            "tags" : [],
        },
        {
            "type" : "string",
            "name" : "comment",
            "comment" : "枚举注释",
            "tags" : [],
        },
        {
            "type" : "list<string>",
            "name" : "tags",
            "comment" : "枚举标签",
            "tags" : [],
        }
    ])

createBuiltinEnumField()

def parse_bool(value):
    """Accept true/false/1/0/\"1\"/\"0\"; empty → False."""
    if value is None or value == "":
        return False
    if value is True or value == 1 or value == "1":
        return True
    if value is False or value == 0 or value == "0":
        return False
    raise Exception("invalid bool '%s' (expect true/false/1/0)" % value)

def _xlsx_field_to_json_shape(f):
    """Excel nested .comment → displayName for unified normalize."""
    if not isinstance(f, dict):
        return f
    out = dict(f)
    if "displayName" not in out or out.get("displayName") in (None, ""):
        if out.get("comment") not in (None, ""):
            out["displayName"] = out.get("comment")
    return out

def _normalize_enum_fields(raw_fields, apply_tags_filter=True):
    items = []
    if not isinstance(raw_fields, list):
        return items
    for f in raw_fields:
        if not isinstance(f, dict):
            continue
        name = f.get("name")
        if not name:
            continue
        tags, _group = parse_tags_cell(f.get("tags"))
        if apply_tags_filter and not Config.isNeedExportTags(tags):
            continue
        display = f.get("displayName") or f.get("comment") or ""
        items.append({
            "name": name,
            "value": f.get("value"),
            "comment": display,  # createEnum items[].comment
            "tags": tags,
        })
    return items

def _normalize_enum_def(obj, apply_tags_filter=True):
    typename = obj.get("typename")
    if not typename:
        return None
    display = obj.get("displayName") or obj.get("comment") or ""
    enumType = obj.get("enumType") or "int32"
    items = _normalize_enum_fields(obj.get("fields"), apply_tags_filter=apply_tags_filter)
    return {
        "typename": typename,
        "displayName": display,
        "enumType": enumType,
        "flags": parse_bool(obj.get("flags")),
        "exportType": parse_bool(obj.get("exportType")),
        "fields": items,
    }

def collect_enum_defs_from_xlsx(xlsx_path, apply_tags_filter=True):
    """Columns: typename, comment, enumType, flags, exportType, fields — comment column → displayName."""
    defs = OrderedDict()
    if not xlsx_path or not os.path.isfile(xlsx_path):
        return defs
    wb = load_workbook(filename=xlsx_path, data_only=True)
    try:
        sheet = Sheet(wb["data"], os.path.basename(xlsx_path), "data")
        for row in sheet.rows:
            raw_fields = row[5]
            if not isinstance(raw_fields, list):
                raw_fields = []
            raw_fields = [_xlsx_field_to_json_shape(f) for f in raw_fields]
            raw = {
                "typename": row[0],
                "displayName": row[1],
                "enumType": row[2],
                "flags": row[3],
                "exportType": row[4],
                "fields": raw_fields,
            }
            entry = _normalize_enum_def(raw, apply_tags_filter=apply_tags_filter)
            if entry:
                defs[entry["typename"]] = entry
    finally:
        wb.close()
    return defs

def collect_enum_defs_from_json(json_path, apply_tags_filter=True):
    """Load __enum__.json (displayName only on type/fields)."""
    defs = OrderedDict()
    if not json_path or not os.path.isfile(json_path):
        return defs
    for obj in load_types_json_list(json_path):
        entry = _normalize_enum_def(obj, apply_tags_filter=apply_tags_filter)
        if entry:
            defs[entry["typename"]] = entry
    return defs

def collect_enum_defs(path, apply_tags_filter=True):
    """Load __enum__ defs: xlsx first, then json overrides by typename."""
    xlsx, js = resolve_type_def_paths(path, ENUM_BASENAME)
    defs = collect_enum_defs_from_xlsx(xlsx, apply_tags_filter=apply_tags_filter)
    for name, entry in collect_enum_defs_from_json(js, apply_tags_filter=apply_tags_filter).items():
        defs[name] = entry
    return defs

def register_enum_defs(defs):
    if not defs:
        return []
    loaded = []
    for typename, entry in defs.items():
        Type.unregister(typename)
        Type.createEnum(
            typename,
            enumType=entry.get("enumType") or "int32",
            items=entry.get("fields") or [],
            comment=entry.get("displayName"),
            flags=bool(entry.get("flags")),
            exportType=bool(entry.get("exportType")),
        )
        loaded.append(typename)
    return loaded

def readEnum(excelDir=None, path=None):
    """Load __enum__.xlsx + __enum__.json into Type registry (json overrides xlsx).

    ``path`` overrides ``excelDir``: directory, ``__enum__.xlsx``/``.json``, or stem.
    Default: ``excelDir/__enum__``.
    Returns list of loaded enum type names (empty if none).
    """
    base = path if path is not None else excelDir
    if not base:
        return []
    defs = collect_enum_defs(base, apply_tags_filter=True)
    return register_enum_defs(defs)
