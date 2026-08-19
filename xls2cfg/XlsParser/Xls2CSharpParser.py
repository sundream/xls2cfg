#coding: utf-8
#@author sundream
#@date 2026-01-20

from XlsParser.XlsParser import XlsParser
from XlsParser.Sheet import getSheets
from XlsParser.Config import Config
from jinja2 import Template
import os.path

class Xls2CSharpParser(XlsParser):
    codeComment = "//"
    extension = ".cs"

    typeMaps = {
        "bool" : "bool",
        "int8": "sbyte",
        "int16": "short",
        "int32" : "int",
        "int64" : "long",
        "uint8" : "byte",
        "uint16": "ushort",
        "uint32": "uint",
        "uint64": "ulong",
        "bigint": "decimal",
        "float" : "float",
        "double" : "double",
        "string" : "string",
        "i18nstring" : "string",
        "json" : "JSONNode",
        "bit32" : "int",
        "bit64" : "long",
        "list" : "List",
        "map" : "Dictionary",
    }

    readFuncs = {
        "bool" : "ReadBool",
        "int8": "ReadInt8",
        "int16": "ReadInt16",
        "int32" : "ReadInt32",
        "int64" : "ReadInt64",
        "uint8" : "ReadUInt8",
        "uint16": "ReadUInt16",
        "uint32": "ReadUInt32",
        "uint64": "ReadUInt64",
        "bigint": "ReadDecimal",
        "float" : "ReadFloat",
        "double" : "ReadDouble",
        "string" : "ReadString",
        "i18nstring" : "ReadString",
        "json" : "ReadJson",
        "bit32" : "ReadInt32",
        "bit64" : "ReadInt64",
        "list" : "ReadList<{valueType}>",
        "map" : "ReadDictionary<{keyType},{valueType}>",
    }

    writeFuncs = {
        "bool" : "WriteBool",
        "int8": "WriteInt8",
        "int16": "WriteInt16",
        "int32" : "WriteInt32",
        "int64" : "WriteInt64",
        "uint8" : "WriteUInt8",
        "uint16": "WriteUInt16",
        "uint32": "WriteUInt32",
        "uint64": "WriteUInt64",
        "bigint": "WriteDecimal",
        "float" : "WriteFloat",
        "double" : "WriteDouble",
        "string" : "WriteString",
        "i18nstring" : "WriteString",
        "json" : "WriteJson",
        "bit32" : "WriteInt32",
        "bit64" : "WriteInt64",
    }

    def __init__(self,sheet,output):
        XlsParser.__init__(self,sheet,output)

    @classmethod
    def writeClass(cls,typ,outputPath):
        cls.buildTypeContext(typ)
        classTemplateFilename = "../runtimes/csharp/class.txt"
        if not typ.getIdField():
            classTemplateFilename = "../runtimes/csharp/singleton_class.txt"
        template = Template(open(classTemplateFilename,encoding="utf-8").read())
        typ.context["formatFieldFromJson"] = lambda fieldIndex: cls.formatFieldFromJson(typ,fieldIndex)
        typ.context["formatFieldFromBinary"] = lambda fieldIndex: cls.formatFieldFromBinary(typ,fieldIndex)
        typ.context["formatFieldToString"] = lambda fieldIndex: cls.formatFieldToString(typ,fieldIndex)
        typ.context["formatFieldToJson"] = lambda fieldIndex: cls.formatFieldToJson(typ,fieldIndex)
        typ.context["formatFieldToBinary"] = lambda fieldIndex: cls.formatFieldToBinary(typ,fieldIndex)
        data = template.render(typ.context)
        cls.writeTo(os.path.join(outputPath,typ.context["className"]),data)

    @classmethod
    def formatFieldFromJson(cls,typ,fieldIndex):
        field = typ.fields[fieldIndex]
        fieldInitStatment = ""
        fieldType = field.type.underlyingType() if field.type.isEnum() else field.type
        fieldTypename = fieldType.typename
        fieldName = field.name
        langFieldName = typ.context["fields"][field.index]["name"]
        if fieldType.isClass():
            fieldInitStatment = 'this.{langFieldName} = new {className}(jsonNode["{fieldName}"]);'.format(
                fieldName=fieldName,
                langFieldName=langFieldName,
                className=cls.formatClassName(fieldType.typename),
            )
        elif fieldTypename == "bool":
            fieldInitStatment = 'this.{langFieldName} = jsonNode["{fieldName}"];'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "int8" or fieldTypename == "int16" or fieldTypename == "int32" or fieldTypename == "int64" \
          or fieldTypename == "uint8" or fieldTypename == "uint16" or fieldTypename == "uint32" or fieldTypename == "uint64" \
          or fieldTypename == "bit32" or fieldTypename == "bit64":
            fieldInitStatment = 'this.{langFieldName} = jsonNode["{fieldName}"];'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "bigint":
            fieldInitStatment = 'this.{langFieldName} = JSON.Parse<decimal>(jsonNode["{fieldName}"]);'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "float" or fieldTypename == "double":
            fieldInitStatment = 'this.{langFieldName} = jsonNode["{fieldName}"];'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "string" or fieldTypename == "i18nstring":
            fieldInitStatment = 'this.{langFieldName} = jsonNode["{fieldName}"];'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "json":
            fieldInitStatment = 'this.{langFieldName} = jsonNode["{fieldName}"];'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "list":
            if fieldType.valueType is not None and fieldType.valueType.isClass():
                className = cls.formatClassName(fieldType.valueType.typename)
                valueType = cls.formatType(fieldType.valueType)
                fieldInitStatment = (
                    '{{ this.{langFieldName} = new List<{valueType}>(); '
                    'var _ln{fid} = jsonNode["{fieldName}"]; '
                    'if (_ln{fid} != null && !_ln{fid}.IsNull && _ln{fid}.IsArray) {{ '
                    'foreach (JSONNode _le{fid} in _ln{fid}) {{ '
                    'this.{langFieldName}.Add(new {className}(_le{fid})); }} }} }}'
                ).format(
                    fieldName=fieldName,
                    langFieldName=langFieldName,
                    valueType=valueType,
                    className=className,
                    fid=field.index,
                )
            else:
                fieldInitStatment = 'this.{langFieldName} = JSON.Parse<{fieldFullTypename}>(jsonNode["{fieldName}"]);'.format(fieldName=fieldName,langFieldName=langFieldName,fieldFullTypename=cls.formatType(fieldType))
        elif fieldTypename == "map":
            if fieldType.valueType is not None and fieldType.valueType.isClass():
                className = cls.formatClassName(fieldType.valueType.typename)
                keyType = cls.formatType(fieldType.keyType)
                valueType = cls.formatType(fieldType.valueType)
                fieldInitStatment = (
                    '{{ this.{langFieldName} = new Dictionary<{keyType},{valueType}>(); '
                    'var _kn{fid} = jsonNode["{fieldName}"]; '
                    'if (_kn{fid} != null && !_kn{fid}.IsNull && _kn{fid}.IsObject) {{ '
                    'foreach (var _ke{fid} in _kn{fid}.Linq) {{ '
                    'this.{langFieldName}[_ke{fid}.Key] = new {className}(_ke{fid}.Value); }} }} }}'
                ).format(
                    fieldName=fieldName,
                    langFieldName=langFieldName,
                    keyType=keyType,
                    valueType=valueType,
                    className=className,
                    fid=field.index,
                )
            else:
                fieldInitStatment = 'this.{langFieldName} = JSON.Parse<{fieldFullTypename}>(jsonNode["{fieldName}"]);'.format(fieldName=fieldName,langFieldName=langFieldName,fieldFullTypename=cls.formatType(fieldType))
        else:
            raise Exception("unsupported type: %s" % field.type.fullTypename)
        return fieldInitStatment

    @classmethod
    def formatFieldFromBinary(cls,typ,fieldIndex):
        field = typ.fields[fieldIndex]
        fieldInitStatment = ""
        fieldType = field.type.underlyingType() if field.type.isEnum() else field.type
        fieldTypename = fieldType.typename
        fieldName = field.name
        langFieldName = typ.context["fields"][field.index]["name"]
        if fieldType.isClass():
            fieldInitStatment = 'this.{langFieldName} = new {className}(bs);'.format(
                langFieldName=langFieldName,
                className=cls.formatClassName(fieldType.typename),
            )
        elif fieldTypename == "bool":
            fieldInitStatment = 'this.{langFieldName} = bs.ReadBool();'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "int8":
            fieldInitStatment = 'this.{langFieldName} = bs.ReadInt8();'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "int16":
            fieldInitStatment = 'this.{langFieldName} = bs.ReadInt16();'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "int32":
            fieldInitStatment = 'this.{langFieldName} = bs.ReadInt32();'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "int64":
            fieldInitStatment = 'this.{langFieldName} = bs.ReadInt64();'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "uint8":
            fieldInitStatment = 'this.{langFieldName} = bs.ReadUInt8();'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "uint16":
            fieldInitStatment = 'this.{langFieldName} = bs.ReadUInt16();'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "uint32":
            fieldInitStatment = 'this.{langFieldName} = bs.ReadUInt32();'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "uint64":
            fieldInitStatment = 'this.{langFieldName} = bs.ReadUInt64();'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "bit32":
            fieldInitStatment = 'this.{langFieldName} = bs.ReadInt32();'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "bit64":
            fieldInitStatment = 'this.{langFieldName} = bs.ReadInt64();'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "bigint":
            fieldInitStatment = 'this.{langFieldName} = bs.ReadDecimal();'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "float":
            fieldInitStatment = 'this.{langFieldName} = bs.ReadFloat();'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "double":
            fieldInitStatment = 'this.{langFieldName} = bs.ReadDouble();'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "string" or fieldTypename == "i18nstring":
            fieldInitStatment = 'this.{langFieldName} = bs.ReadString();'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "json":
            fieldInitStatment = 'this.{langFieldName} = bs.ReadJson();'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "list":
            value_expr = cls._read_expr(fieldType.valueType)
            fieldInitStatment = '{{int length = bs.ReadUInt8(); this.{langFieldName} = new List<{valueType}>(length); for (int i = 0; i < length; i++) {{ this.{langFieldName}.Add({value_expr}); }} }}'.format(langFieldName=langFieldName,valueType=cls.formatType(fieldType.valueType),value_expr=value_expr)
        elif fieldTypename == "map":
            key_expr = cls._read_expr(fieldType.keyType)
            value_expr = cls._read_expr(fieldType.valueType)
            fieldInitStatment = '{{int length = bs.ReadUInt8(); this.{langFieldName} = new Dictionary<{keyType}, {valueType}>(length); for (int i = 0; i < length; i++) {{ this.{langFieldName}.Add({key_expr}, {value_expr}); }} }}'.format(langFieldName=langFieldName,keyType=cls.formatType(fieldType.keyType), valueType=cls.formatType(fieldType.valueType),key_expr=key_expr,value_expr=value_expr)
        else:
            raise Exception("unsupported type: %s" % field.type.fullTypename)
        return fieldInitStatment

    @classmethod
    def formatFieldToString(cls,typ,fieldIndex):
        field = typ.fields[fieldIndex]
        fieldType = field.type.underlyingType() if field.type.isEnum() else field.type
        fieldTypename = fieldType.typename
        fieldName = field.name
        langFieldName = typ.context["fields"][field.index]["name"]
        if fieldTypename == "bigint" or fieldTypename == "list" or fieldTypename == "map":
            return 'jsonNode["{fieldName}"] = this.{langFieldName}.ToString();'.format(fieldName=fieldName,langFieldName=langFieldName)
        else:
            return 'jsonNode["{fieldName}"] = this.{langFieldName};'.format(fieldName=fieldName,langFieldName=langFieldName)

    @classmethod
    def _json_value(cls, typ, expr, depth, fid):
        """Return (stmts, node_expr) that evaluate to a JSONNode."""
        if typ.isEnum():
            typ = typ.underlyingType()
        if typ.isClass():
            return "", "%s.ToJson()" % expr
        typename = typ.typename
        if typename == "bigint":
            return "", "%s.ToString()" % expr
        if typename == "list":
            arr = "_ja%d_%d" % (fid, depth)
            idx = "_ji%d_%d" % (fid, depth)
            inner_stmts, inner_expr = cls._json_value(typ.valueType, "%s[%s]" % (expr, idx), depth + 1, fid)
            stmts = (
                "JSONArray %s = new JSONArray(); "
                "if (%s != null) { for (int %s = 0; %s < %s.Count; %s++) { %s %s.Add(%s); } }"
            ) % (arr, expr, idx, idx, expr, idx, inner_stmts, arr, inner_expr)
            return stmts, arr
        if typename == "map":
            obj = "_jo%d_%d" % (fid, depth)
            kv = "_jk%d_%d" % (fid, depth)
            inner_stmts, inner_expr = cls._json_value(typ.valueType, "%s.Value" % kv, depth + 1, fid)
            key_type = typ.keyType.typename
            if key_type == "string" or key_type == "i18nstring":
                key_expr = "%s.Key" % kv
            else:
                key_expr = "%s.Key.ToString()" % kv
            stmts = (
                "JSONObject %s = new JSONObject(); "
                "if (%s != null) { foreach (var %s in %s) { %s %s[%s] = %s; } }"
            ) % (obj, expr, kv, expr, inner_stmts, obj, key_expr, inner_expr)
            return stmts, obj
        return "", expr

    @classmethod
    def formatFieldToJson(cls,typ,fieldIndex):
        field = typ.fields[fieldIndex]
        fieldName = field.name
        langFieldName = typ.context["fields"][field.index]["name"]
        expr = "this." + langFieldName
        fieldType = field.type.underlyingType() if field.type.isEnum() else field.type
        stmts, node_expr = cls._json_value(fieldType, expr, 0, fieldIndex)
        assign = 'jsonNode["%s"] = %s;' % (fieldName, node_expr)
        if stmts:
            return stmts + " " + assign
        return assign

    @classmethod
    def _binary_value(cls, typ, expr, depth):
        if typ.isEnum():
            typ = typ.underlyingType()
        if typ.isClass():
            return "%s.Serialize(bs);" % expr
        typename = typ.typename
        write = cls.writeFuncs.get(typename)
        if write:
            if typename in ("string", "i18nstring"):
                return "bs.%s(%s ?? \"\");" % (write, expr)
            return "bs.%s(%s);" % (write, expr)
        if typename == "list":
            lvar = "_bl%d" % depth
            nvar = "_bn%d" % depth
            idx = "_bi%d" % depth
            inner = cls._binary_value(typ.valueType, "%s[%s]" % (lvar, idx), depth + 1)
            return (
                "{var %s = %s; int %s = %s == null ? 0 : %s.Count; "
                "if (%s > 255) throw new Exception(\"list length > 255\"); "
                "bs.WriteUInt8((byte)%s); for (int %s = 0; %s < %s; %s++) { %s }}"
            ) % (lvar, expr, nvar, lvar, lvar, nvar, nvar, idx, idx, nvar, idx, inner)
        if typename == "map":
            mvar = "_bm%d" % depth
            nvar = "_bn%d" % depth
            kv = "_bk%d" % depth
            bkey = cls._binary_value(typ.keyType, "%s.Key" % kv, depth + 1)
            bval = cls._binary_value(typ.valueType, "%s.Value" % kv, depth + 1)
            return (
                "{var %s = %s; int %s = %s == null ? 0 : %s.Count; "
                "if (%s > 255) throw new Exception(\"map length > 255\"); "
                "bs.WriteUInt8((byte)%s); if (%s != null) { foreach (var %s in %s) { %s %s } }}"
            ) % (mvar, expr, nvar, mvar, mvar, nvar, nvar, mvar, kv, mvar, bkey, bval)
        raise Exception("unsupported write type: %s" % typ.fullTypename)

    @classmethod
    def formatFieldToBinary(cls,typ,fieldIndex):
        field = typ.fields[fieldIndex]
        langFieldName = typ.context["fields"][field.index]["name"]
        fieldType = field.type.underlyingType() if field.type.isEnum() else field.type
        return cls._binary_value(fieldType, "this." + langFieldName, 0)

    @classmethod
    def _read_expr(cls, typ):
        if typ.isEnum():
            typ = typ.underlyingType()
        if typ.isClass():
            return "new %s(bs)" % cls.formatClassName(typ.typename)
        return "bs.%s()" % cls.getReadFunc(typ)

    @classmethod
    def getReadFunc(cls, typ):
        if typ.isEnum():
            typ = typ.underlyingType()
        typename = typ.typename
        readFunc = cls.readFuncs.get(typename)
        if typename == "list":
            valueType = cls.formatType(typ.valueType)
            readFunc = readFunc.format(valueType = valueType)
        elif typename == "map":
            keyType = cls.formatType(typ.keyType)
            valueType = cls.formatType(typ.valueType)
            readFunc = readFunc.format(keyType=keyType,valueType=valueType)
        elif readFunc is None:
            # class
            readFunc = "ReadValue<{typename}>".format(typename = cls.formatClassName(typename))
        return readFunc

    @classmethod
    def endParse(cls,outputPath):
        cls.writeAllClass(outputPath)
        if cls.ignoreGenTables:
            return
        sheets = getSheets()
        context = {
            "namespace" : Config.namespace,
            "sheets" : [],
        }
        for sheetName,sheet in sheets.items():
            idName = cls.formatFieldName(sheet.col2key[sheet.idCol])
            idTypename = cls.formatType(sheet.col2type[sheet.idCol])
            instName = cls.formatFieldName(sheetName)
            className = cls.formatClassName(sheetName)
            context["sheets"].append({
                "classComment" : sheet.comment,
                "instName" : instName,
                "className" : className,
                "fileName" : sheetName,
                "singleton" : sheet.singleton,
                "idName" : idName,
                "idTypename" : idTypename,
            })
        tableTemplateFilename = "../runtimes/csharp/tables.txt"
        template = Template(open(tableTemplateFilename,encoding="utf-8").read())
        data = template.render(context)
        cls.writeTo(os.path.join(outputPath,"Tables"),data)

    @classmethod
    def formatType(cls,typ):
        typename = typ.typename
        if typ.isEnum():
            return cls.formatType(typ.underlyingType())
        if typ.isClass():
            return typename
        if cls.typeMaps[typename] is None:
            raise Exception("unknow typename: %s" % typename)
        langTypename = cls.typeMaps[typename]
        if typename == "list":
            langTypename = "%s<%s>" % (langTypename,cls.formatType(typ.valueType))
        elif typename == "map":
            langTypename = "%s<%s,%s>" % (langTypename,cls.formatType(typ.keyType),cls.formatType(typ.valueType))
        return langTypename

    @classmethod
    def formatFieldName(cls,fieldName):
        if Config.fieldNameFirstUpper:
            fieldName = fieldName[:1].upper() + fieldName[1:]
        return fieldName