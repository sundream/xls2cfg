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
        data = template.render(typ.context)
        cls.writeTo(os.path.join(outputPath,typ.context["className"]),data)

    @classmethod
    def formatFieldFromJson(cls,typ,fieldIndex):
        field = typ.fields[fieldIndex]
        fieldInitStatment = ""
        fieldTypename = field.type.typename
        fieldName = field.name
        langFieldName = typ.context["fields"][field.index]["name"]
        if field.type.isClass():
            fieldInitStatment = 'this.{langFieldName} = jsonNode["{fieldName}"];'.format(fieldName=fieldName,langFieldName=langFieldName)
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
            fieldInitStatment = 'this.{langFieldName} = JSON.Parse<{fieldFullTypename}>(jsonNode["{fieldName}"]);'.format(fieldName=fieldName,langFieldName=langFieldName,fieldFullTypename=cls.formatType(field.type))
        elif fieldTypename == "map":
            fieldInitStatment = 'this.{langFieldName} = JSON.Parse<{fieldFullTypename}>(jsonNode["{fieldName}"]);'.format(fieldName=fieldName,langFieldName=langFieldName,fieldFullTypename=cls.formatType(field.type))
        else:
            raise Exception("unsupported type: %s" % field.type.fullTypename)
        return fieldInitStatment

    @classmethod
    def formatFieldFromBinary(cls,typ,fieldIndex):
        field = typ.fields[fieldIndex]
        fieldInitStatment = ""
        fieldTypename = field.type.typename
        fieldName = field.name
        langFieldName = typ.context["fields"][field.index]["name"]
        if field.type.isClass():
            fieldInitStatment = 'if err = ReadStruct(bs,&o.{langFieldName}); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
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
            value_readFunc = cls.getReadFunc(field.type.valueType)
            fieldInitStatment = '{{int length = bs.ReadUInt8(); this.{langFieldName} = new List<{valueType}>(length); for (int i = 0; i < length; i++) {{ this.{langFieldName}.Add(bs.{value_readFunc}()); }} }}'.format(fieldName=fieldName,langFieldName=langFieldName,valueType=cls.formatType(field.type.valueType),value_readFunc=value_readFunc)
        elif fieldTypename == "map":
            key_readFunc = cls.getReadFunc(field.type.keyType)
            value_readFunc = cls.getReadFunc(field.type.valueType)
            fieldInitStatment = '{{int length = bs.ReadUInt8(); this.{langFieldName} = new Dictionary<{keyType}, {valueType}>(length); for (int i = 0; i < length; i++) {{ this.{langFieldName}.Add(bs.{key_readFunc}(), bs.{value_readFunc}()); }} }}'.format(fieldName=fieldName,langFieldName=langFieldName,keyType=cls.formatType(field.type.keyType), valueType=cls.formatType(field.type.valueType),key_readFunc=key_readFunc,value_readFunc=value_readFunc)
        else:
            raise Exception("unsupported type: %s" % field.type.fullTypename)
        return fieldInitStatment

    @classmethod
    def formatFieldToString(cls,typ,fieldIndex):
        field = typ.fields[fieldIndex]
        fieldTypename = field.type.typename
        fieldName = field.name
        langFieldName = typ.context["fields"][field.index]["name"]
        if fieldTypename == "bigint" or fieldTypename == "list" or fieldTypename == "map":
            return 'jsonNode["{fieldName}"] = this.{langFieldName}.ToString();'.format(fieldName=fieldName,langFieldName=langFieldName)
        else:
            return 'jsonNode["{fieldName}"] = this.{langFieldName};'.format(fieldName=fieldName,langFieldName=langFieldName)

    @classmethod
    def getReadFunc(cls, typ):
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