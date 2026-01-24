#coding: utf-8
#@author sundream
#@date 2025-09-10

from XlsParser.XlsParser import XlsParser
from XlsParser.Sheet import getSheets
from XlsParser.Config import Config
from jinja2 import Template
import os.path

class Xls2GoParser(XlsParser):
    codeComment = "//"
    extension = ".go"

    typeMaps = {
        "bool" : "bool",
        "int8": "int8",
        "int16": "int16",
        "int32" : "int32",
        "int64" : "int64",
        "uint8" : "uint8",
        "uint16": "uint16",
        "uint32": "uint32",
        "uint64": "uint64",
        "bigint": "BigInt",
        "float" : "float32",
        "double" : "float64",
        "string" : "string",
        "i18nstring" : "string",
        "json" : "any",
        "bit32" : "int32",
        "bit64" : "int64",
        "list" : "[]",
        "map" : "map",
    }

    def __init__(self,sheet,output):
        XlsParser.__init__(self,sheet,output)

    @classmethod
    def writeClass(cls,typ,outputPath):
        cls.buildTypeContext(typ)
        classTemplateFilename = "../runtimes/go/class.txt"
        template = Template(open(classTemplateFilename,encoding="utf-8").read())
        typ.context["formatFieldFromJson"] = lambda fieldIndex: cls.formatFieldFromJson(typ,fieldIndex)
        typ.context["formatFieldFromBinary"] = lambda fieldIndex: cls.formatFieldFromBinary(typ,fieldIndex)
        data = template.render(typ.context)
        cls.writeTo(os.path.join(outputPath,typ.context["className"].lower()),data)

    @classmethod
    def formatFieldFromJson(cls,typ,fieldIndex):
        field = typ.fields[fieldIndex]
        fieldInitStatment = ""
        fieldTypename = field.type.typename
        fieldName = field.name
        langFieldName = typ.context["fields"][field.index]["name"]
        if field.type.isClass():
            fieldInitStatment = 'if err := DeserializeStructFromJson(&o.{langFieldName},jsonData["{fieldName}"]); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "bool":
            fieldInitStatment = 'if err:= DeserializeBoolFromJson(&o.{langFieldName},jsonData["{fieldName}"]); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "int8" or fieldTypename == "int16" or fieldTypename == "int32" or fieldTypename == "int64" \
          or fieldTypename == "uint8" or fieldTypename == "uint16" or fieldTypename == "uint32" or fieldTypename == "uint64" \
          or fieldTypename == "bit32" or fieldTypename == "bit64":
            fieldInitStatment = 'if err := DeserializeIntFromJson(&o.{langFieldName},jsonData["{fieldName}"]); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "bigint":
            fieldInitStatment = 'if err := DeserializeBigIntFromJson(&o.{langFieldName},jsonData["{fieldName}"]); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "float" or fieldTypename == "double":
            fieldInitStatment = 'if err := DeserializeFloatFromJson(&o.{langFieldName},jsonData["{fieldName}"]); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "string" or fieldTypename == "i18nstring":
            fieldInitStatment = 'if err := DeserializeStringFromJson(&o.{langFieldName},jsonData["{fieldName}"]); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "json":
            fieldInitStatment = 'if err := DeserializeJsonFromJson(&o.{langFieldName},jsonData["{fieldName}"]); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "list":
            fieldInitStatment = 'if err := DeserializeListFromJson(&o.{langFieldName},jsonData["{fieldName}"]); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "map":
            fieldInitStatment = 'if err := DeserializeMapFromJson(&o.{langFieldName},jsonData["{fieldName}"]); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
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
            fieldInitStatment = 'if o.{langFieldName}, err = bs.ReadBool(); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "int8":
            fieldInitStatment = 'if o.{langFieldName}, err = bs.ReadInt8(); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "int16":
            fieldInitStatment = 'if o.{langFieldName}, err = bs.ReadInt16(); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "int32":
            fieldInitStatment = 'if o.{langFieldName}, err = bs.ReadInt32(); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "int64":
            fieldInitStatment = 'if o.{langFieldName}, err = bs.ReadInt64(); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "uint8":
            fieldInitStatment = 'if o.{langFieldName}, err = bs.ReadUInt8(); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "uint16":
            fieldInitStatment = 'if o.{langFieldName}, err = bs.ReadUInt16(); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "uint32":
            fieldInitStatment = 'if o.{langFieldName}, err = bs.ReadUInt32(); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "uint64":
            fieldInitStatment = 'if o.{langFieldName}, err = bs.ReadUInt64(); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "bit32":
            fieldInitStatment = 'if o.{langFieldName}, err = bs.ReadInt32(); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "bit64":
            fieldInitStatment = 'if o.{langFieldName}, err = bs.ReadInt64(); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "bigint":
            fieldInitStatment = 'if o.{langFieldName}, err = bs.ReadBigInt(); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "float":
            fieldInitStatment = 'if o.{langFieldName}, err = bs.ReadFloat32(); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "double":
            fieldInitStatment = 'if o.{langFieldName}, err = bs.ReadFloat64(); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "string" or fieldTypename == "i18nstring":
            fieldInitStatment = 'if o.{langFieldName}, err = bs.ReadString(); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "json":
            fieldInitStatment = 'if o.{langFieldName}, err = bs.ReadJson(); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "list":
            fieldInitStatment = 'if err = ReadList(bs,&o.{langFieldName}); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        elif fieldTypename == "map":
            fieldInitStatment = 'if err = ReadMap(bs,&o.{langFieldName}); err != nil {{ return err }}'.format(fieldName=fieldName,langFieldName=langFieldName)
        else:
            raise Exception("unsupported type: %s" % field.type.fullTypename)
        return fieldInitStatment

    @classmethod
    def endParse(cls,outputPath):
        cls.writeAllClass(outputPath)
        sheets = getSheets()
        context = {
            "namespace" : cls.formatNamespace(Config.namespace),
            "sheets" : [],
        }
        for sheetName,sheet in sheets.items():
            instName = cls.formatFieldName(sheetName)
            className = cls.formatClassName(sheetName)
            idName = cls.formatFieldName(sheet.col2key[sheet.idCol])
            idTypename = cls.formatType(sheet.col2type[sheet.idCol])
            context["sheets"].append({
                "instName" : instName,
                "className" : className,
                "fileName" : sheetName,
                "singleton" : sheet.singleton,
                "idName" : idName,
                "idTypename" : idTypename,
            })
        tableTemplateFilename = "../runtimes/go/tables.txt"
        template = Template(open(tableTemplateFilename,encoding="utf-8").read())
        data = template.render(context)
        cls.writeTo(os.path.join(outputPath,"tables"),data)

    @classmethod
    def formatNamespace(cls,namespace):
        return namespace.lower()

    @classmethod
    def formatType(cls,typ):
        typename = typ.typename
        if typ.isClass():
            return typename
        if cls.typeMaps[typename] is None:
            raise Exception("unknow typename: %s" % typename)
        langTypename = cls.typeMaps[typename]
        if typename == "list":
            langTypename = "%s%s" % (langTypename,cls.formatType(typ.valueType))
        elif typename == "map":
            langTypename = "%s[%s]%s" % (langTypename,cls.formatType(typ.keyType),cls.formatType(typ.valueType))
        return langTypename

    @classmethod
    def formatClassName(cls,typename):
        return typename[:1].upper() + typename[1:]

    @classmethod
    def formatFieldName(cls,fieldName):
        return fieldName[:1].upper() + fieldName[1:]