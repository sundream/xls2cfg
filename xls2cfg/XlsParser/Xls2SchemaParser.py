#coding: utf-8
#@author sundream
#@date 2026-08-07
"""Export Global/table-compatible schema JSON (all columns; ignore tags filter).

Schema top-level:
  kind, name, displayName?, typename, workbook, sheetName, sheetIndex, fields[]
  enum (kind=0 + enumType): optional flags; fields[].name/value/displayName/tags

fields (table/class): name, type, displayName, remarks, constraint, tags, group, layout
Type uses Excel raw type text (fullTypename). Aliases apply only to internal typename.

layout (optional):
  mode=split, colSpan, keys[], elementSpan?, elementKeys?  — merge-split restore
  intBase=16|2 — field-level int*/uint* literal base (from first data row; not bigint)
  .key constraints live in layout.keys (not in constraint).
"""

from XlsParser.XlsParser import XlsParser
from XlsParser.Config import Config
from XlsParser.Sheet import compose_table_display_name
from XlsParser.Type import Type, Field
import json
import os


KIND_CLASS = 0
KIND_1D = 1
KIND_2D = 2


def format_constraint(constraint, seperator=";"):
    """Rebuild Excel constraint cell text (excludes .key → layout.keys)."""
    if not constraint:
        return ""
    parts = []
    for k, v in constraint.items():
        if k.startswith("."):
            # Moved to field.layout.keys
            continue
        if k in ("unique", "not_null", "not_localize"):
            if v:
                parts.append(k)
        elif k == "split":
            if isinstance(v, int):
                parts.append("split=%d" % (v + 1))
            else:
                parts.append("split=%s" % v)
        elif k == "default":
            if v is None:
                parts.append("default=nil")
            else:
                parts.append("default=%s" % v)
        elif k == "limit":
            parts.append("limit=%s" % v)
        else:
            if v is True:
                parts.append(k)
            elif v is None:
                parts.append(k)
            else:
                parts.append("%s=%s" % (k, v))
    return seperator.join(parts)


def build_field_layout(sheet, col):
    """Build layout dict from mergeCells + col2mapkey (+ intBase). None if empty."""
    layout = None
    merge_cell = sheet.mergeCells.get(col)
    if merge_cell and col == merge_cell.startCol:
        keys_seq = []
        for c in range(merge_cell.startCol, merge_cell.startCol + merge_cell.count):
            mapkey = sheet.col2mapkey.get(c)
            if mapkey is not None:
                keys_seq.append(mapkey)
        keys = []
        for k in keys_seq:
            if k not in keys:
                keys.append(k)
        layout = {
            "mode": "split",
            "colSpan": merge_cell.count,
            "keys": keys,
        }
        if keys:
            layout["elementSpan"] = merge_cell.fieldCount or len(keys)
        else:
            typ = sheet.col2type.get(col)
            if (
                typ is not None
                and typ.typename == "list"
                and typ.valueType is not None
                and typ.valueType.isClass()
                and typ.valueType.fields
            ):
                layout["elementKeys"] = [f.name for f in typ.valueType.fields]
    int_base = sheet.col2intBase.get(col)
    if int_base:
        if layout is None:
            layout = {}
        layout["intBase"] = int_base
    return layout


def format_tags(tags):
    return Field.format_tags(tags)


class Xls2SchemaParser(XlsParser):
    extension = ".json"

    def __init__(self, sheet, output):
        # Skip buildType/buildData (tag-filtered); schema always exports full header.
        self.sheet = sheet
        self.output = output
        self.pretty = Config.pretty
        self.singleton = sheet.singleton

    def parse(self):
        if self.isEmptySchema():
            return
        schema = self.buildSchema()
        if self.pretty:
            data = json.dumps(schema, ensure_ascii=False, indent=2)
        else:
            data = json.dumps(schema, ensure_ascii=False)
        self._writeSchema(self.sheet.filename, data)

    def isEmptySchema(self):
        return len(self.iterFieldCols()) == 0

    def iterFieldCols(self):
        cols = []
        for col in range(0, self.sheet.maxCol):
            key = self.sheet.col2key.get(col)
            typ = self.sheet.col2type.get(col)
            if not key or typ is None:
                continue
            tags = self.sheet.col2tags.get(col)
            if tags and "__ignore" in tags:
                continue
            cols.append(col)
        return cols

    def _ensureSchemaType(self, className):
        """Get or create a Type for schema export; reset fields when reusing."""
        existing = Type.get(className)
        if isinstance(existing, Type):
            typ = existing
            typ.fields = []
            typ.idFieldIdx = -1
        else:
            typ = Type.createClass(className)
        typ.singleton = self.singleton
        # Provisional; buildSchema overwrites with compose_table_display_name.
        typ.comment = compose_table_display_name(self.sheet)
        return typ

    def buildSchema(self):
        name = self.sheet.filename
        className = self.formatClassName(name)
        kind = KIND_1D if self.singleton else KIND_2D
        typ = self._ensureSchemaType(className)
        cols = self.iterFieldCols()
        for col in cols:
            typ.defineField(
                self.sheet.col2type[col].fullTypename,
                self.sheet.col2key[col],
                comment=self.sheet.col2desc.get(col) or "",
                tags=self.sheet.col2tags.get(col),
                remarks=self.sheet.col2comment.get(col) or "",
                group=self.sheet.col2group.get(col),
            )
        schema = typ.to_schema(name=name, kind=kind, class_name=className)
        display = compose_table_display_name(self.sheet)
        if display:
            typ.comment = display
            schema["displayName"] = display
        # Identity / workbook meta (stable key order for editors)
        out = {
            "kind": kind,
            "name": name,
        }
        if display:
            out["displayName"] = display
        elif schema.get("displayName"):
            out["displayName"] = schema["displayName"]
        out["typename"] = className
        out["workbook"] = self.sheet.xlsFilename
        out["sheetName"] = self.sheet.sheetName
        out["sheetIndex"] = self.sheet.sheetIndex
        out["fields"] = schema["fields"]

        name_to_field = {f["name"]: f for f in out["fields"]}
        for col in cols:
            fname = self.sheet.col2key[col]
            entry = name_to_field.get(fname)
            if not entry:
                continue
            if not self.singleton:
                constraint = format_constraint(
                    self.sheet.col2constraint.get(col),
                    self.sheet.constraintSeperator,
                )
                if constraint:
                    entry["constraint"] = constraint
            layout = build_field_layout(self.sheet, col)
            if layout:
                entry["layout"] = layout
        return out

    def _writeSchema(self, filename, data):
        path = os.path.join(self.output, filename + self.extension)
        parent = os.path.dirname(path)
        if parent != "" and not os.path.isdir(parent):
            os.makedirs(parent)
        with open(path, "w", encoding="utf-8", newline="\n") as fd:
            fd.write(data)
            if self.pretty and not data.endswith("\n"):
                fd.write("\n")
        print("write", self.output, filename)
