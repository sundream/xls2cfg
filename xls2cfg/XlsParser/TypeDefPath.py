#coding:utf-8
#@author sundream
#@date 2026-08-14

import json
import os


def resolve_type_def_paths(path, basename):
    """Resolve __class__/__enum__ xlsx+json paths from a dir, file, or stem.

    ``path`` may be:
    - a directory containing ``{basename}.xlsx`` / ``{basename}.json``
    - a file path ``.../{basename}.xlsx`` or ``.../{basename}.json``
    - a stem path without extension ``.../{basename}``

    Returns (xlsx_path_or_None, json_path_or_None) for files that exist.
    """
    if not path:
        return None, None
    path = os.path.abspath(path)
    if os.path.isdir(path):
        stem = os.path.join(path, basename)
    else:
        root, ext = os.path.splitext(path)
        if ext.lower() in (".xlsx", ".json"):
            stem = root
        else:
            stem = path
    xlsx = stem + ".xlsx"
    js = stem + ".json"
    return (
        xlsx if os.path.isfile(xlsx) else None,
        js if os.path.isfile(js) else None,
    )


def load_types_json_list(json_path):
    """Load type-def JSON as a list of objects.

    Accepts:
    - array of type objects
    - ``{"types": [...]}``
    - map ``{TypeName: {...}, ...}``
    - single type object with typename
    """
    with open(json_path, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        raise Exception("invalid type def json (expect list or object): %s" % json_path)
    if isinstance(data.get("types"), list):
        return data["types"]
    if data.get("typename"):
        return [data]
    items = []
    for key, val in data.items():
        if key in ("types", "kind", "workbook", "sheetName", "sheetIndex"):
            continue
        if not isinstance(val, dict):
            continue
        item = dict(val)
        item.setdefault("typename", key)
        item.setdefault("name", key)
        items.append(item)
    return items
