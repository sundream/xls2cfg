#coding:utf-8
#@author sundream
#@date 2025-09-10

import os
from collections import OrderedDict
from XlsParser.Sheet import Sheet
from XlsParser.Type import Type, parse_tags_cell
from XlsParser.Config import Config
from XlsParser.TypeDefPath import resolve_type_def_paths, load_types_json_list
from openpyxl import load_workbook

CLASS_BASENAME = "__class__"

def createBuiltinClass():
    Type.createClass("__Field__",[
        {
            "type" : "string",
            "name" : "name",
            "comment" : "字段名",
            "tags" : [],
        },
        {
            "type" : "string",
            "name" : "type",
            "comment" : "字段类型",
            "tags" : [],
        },
        {
            "type" : "string",
            "name" : "comment",
            "comment" : "字段备注",
            "tags" : [],
        },
        {
            "type" : "list<string>",
            "name" : "tags",
            "comment" : "字段标签列表",
            "tags" : [],
        }
    ])

createBuiltinClass()

def _xlsx_field_to_json_shape(f):
    """Excel nested .comment → displayName for unified normalize."""
    if not isinstance(f, dict):
        return f
    out = dict(f)
    if "displayName" not in out or out.get("displayName") in (None, ""):
        if out.get("comment") not in (None, ""):
            out["displayName"] = out.get("comment")
    return out

def _normalize_class_fields(raw_fields, apply_tags_filter=True):
    fields = []
    for f in raw_fields or []:
        name = f.get("name")
        ftype = f.get("type")
        if not name or not ftype:
            continue
        tags, group = parse_tags_cell(f.get("tags"))
        if apply_tags_filter and not Config.isNeedExportTags(tags):
            continue
        display = f.get("displayName") or f.get("comment") or ""
        entry = {
            "type": ftype,
            "name": name,
            "comment": display,  # Type.defineField / Field.comment storage
            "tags": tags,
        }
        if f.get("remarks"):
            entry["remarks"] = f.get("remarks")
        if group or f.get("group"):
            entry["group"] = group or f.get("group")
        fields.append(entry)
    return fields

def _normalize_class_def(obj, apply_tags_filter=True):
    typename = obj.get("typename")
    if not typename:
        return None
    display = obj.get("displayName") or obj.get("comment") or ""
    fields = _normalize_class_fields(obj.get("fields"), apply_tags_filter=apply_tags_filter)
    if not fields:
        return None
    return {
        "typename": typename,
        "displayName": display,
        "fields": fields,
    }

def collect_class_defs_from_xlsx(xlsx_path, apply_tags_filter=True):
    """OrderedDict typename -> def from __class__.xlsx (column comment → displayName)."""
    defs = OrderedDict()
    if not xlsx_path or not os.path.isfile(xlsx_path):
        return defs
    wb = load_workbook(filename=xlsx_path, data_only=True)
    try:
        sheet = Sheet(wb["data"], os.path.basename(xlsx_path), "data")
        for row in sheet.rows:
            raw_fields = [_xlsx_field_to_json_shape(f) for f in (row[2] if len(row) > 2 else []) or []]
            raw = {
                "typename": row[0],
                "displayName": row[1],
                "fields": raw_fields,
            }
            entry = _normalize_class_def(raw, apply_tags_filter=apply_tags_filter)
            if entry:
                defs[entry["typename"]] = entry
    finally:
        wb.close()
    return defs

def collect_class_defs_from_json(json_path, apply_tags_filter=True):
    """OrderedDict typename -> def from __class__.json (displayName only)."""
    defs = OrderedDict()
    if not json_path or not os.path.isfile(json_path):
        return defs
    for obj in load_types_json_list(json_path):
        entry = _normalize_class_def(obj, apply_tags_filter=apply_tags_filter)
        if entry:
            defs[entry["typename"]] = entry
    return defs

def collect_class_defs(path, apply_tags_filter=True):
    """Load __class__ defs: xlsx first, then json overrides by typename."""
    xlsx, js = resolve_type_def_paths(path, CLASS_BASENAME)
    defs = collect_class_defs_from_xlsx(xlsx, apply_tags_filter=apply_tags_filter)
    for name, entry in collect_class_defs_from_json(js, apply_tags_filter=apply_tags_filter).items():
        defs[name] = entry
    return defs

def register_class_defs(defs):
    """Register collected class defs into Type. Returns list of typenames."""
    if not defs:
        return []
    loaded = []
    for typename, entry in defs.items():
        Type.unregister(typename)
        Type.createClass(typename, entry["fields"])
        if entry.get("displayName"):
            Type.get(typename).comment = entry["displayName"]
        loaded.append(typename)
    return loaded

def readClass(excelDir=None, path=None):
    """Load __class__.xlsx + __class__.json into Type registry (json overrides xlsx).

    ``path`` overrides ``excelDir``: directory, ``__class__.xlsx``/``.json``, or stem.
    Default: ``excelDir/__class__``.
    Returns list of loaded class type names (empty if none).
    """
    base = path if path is not None else excelDir
    if not base:
        return []
    defs = collect_class_defs(base, apply_tags_filter=True)
    return register_class_defs(defs)
