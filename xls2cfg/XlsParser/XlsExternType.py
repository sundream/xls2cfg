#coding:utf-8
#@author sundream
#@date 2026-08-20

import os
from XlsParser.Config import Config
from XlsParser.Type import Type
from XlsParser.TypeDefPath import resolve_type_def_paths, load_types_json_list

EXTERN_BASENAME = "__externtype__"


def _as_str_list(value, field_name, typename):
    if value is None:
        return []
    if isinstance(value, str):
        items = [x.strip() for x in value.split(",") if x.strip()]
        return items
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    raise Exception("%s.%s must be string or list" % (typename, field_name))


def load_extern_type_entries(path):
    """Load externtype json. ``path`` is required file/dir/stem; empty -> []."""
    if not path:
        return []
    _xlsx, js = resolve_type_def_paths(path, EXTERN_BASENAME)
    if not js:
        raise Exception("extern-type file not found: %s (expect %s.json)" % (path, EXTERN_BASENAME))
    return load_types_json_list(js)


def _pick_mapper(mappers, tags, output_format, typename):
    hits = []
    tag_set = set(tags or [])
    for mapper in mappers:
        mapper_tags = set(mapper.get("tags") or [])
        mapper_formats = set(mapper.get("formats") or [])
        if output_format not in mapper_formats:
            continue
        if tag_set and mapper_tags:
            if not (tag_set & mapper_tags):
                continue
        elif mapper_tags and not tag_set:
            continue
        hits.append(mapper)
    if not hits:
        return None
    if len(hits) > 1:
        raise Exception("extern type %s: multiple mappers match tags=%s format=%s" % (
            typename, tags, output_format))
    return hits[0]


def apply_extern_types(path, output_format):
    """Apply matching extern mappers onto Type registry for this export.

    ``path`` None/empty: clear mappings only (default: no extern conversion).
    Does not add a kind/enum flag in json: looks up typename in Type.
    Class mapper requires constructor (internal→external) and reverseConstructor (external→internal).
    Enum mapper: both optional (default: cast via underlying integer).
    """
    for name, typ in list(Type.types.items()):
        if isinstance(typ, Type):
            typ.externType = None
            typ.externConstructor = None
            typ.externReverseConstructor = None

    if not path:
        return []

    entries = load_extern_type_entries(path)
    applied = []
    for obj in entries:
        typename = obj.get("typename")
        if not typename:
            raise Exception("extern type missing typename")
        typ = Type.get(typename)
        if not isinstance(typ, Type) or not (typ.isClass() or typ.isEnum()):
            raise Exception("extern type %s is not a defined class or enum" % typename)
        mappers = []
        for raw in obj.get("mappers") or []:
            if not isinstance(raw, dict):
                continue
            ext_type = (raw.get("type") or "").strip()
            if not ext_type:
                raise Exception("extern type %s mapper missing type" % typename)
            mapper = {
                "tags": _as_str_list(raw.get("tags"), "tags", typename),
                "formats": _as_str_list(raw.get("formats"), "formats", typename),
                "type": ext_type,
                "constructor": (raw.get("constructor") or "").strip() or None,
                "reverseConstructor": (raw.get("reverseConstructor") or "").strip() or None,
            }
            if not mapper["formats"]:
                raise Exception("extern type %s mapper missing formats" % typename)
            if not mapper["tags"]:
                raise Exception("extern type %s mapper missing tags" % typename)
            mappers.append(mapper)
        hit = _pick_mapper(mappers, Config.tags, output_format, typename)
        if not hit:
            continue
        if typ.isClass():
            if not hit["constructor"]:
                raise Exception(
                    "extern class %s mapper requires constructor (e.g. ExternTypeUtil.FromVec3)" % typename)
            if not hit["reverseConstructor"]:
                raise Exception(
                    "extern class %s mapper requires reverseConstructor (e.g. ExternTypeUtil.ToVec3)" % typename)
        typ.externType = hit["type"]
        typ.externConstructor = hit["constructor"]
        typ.externReverseConstructor = hit["reverseConstructor"]
        applied.append(typename)
    return applied
