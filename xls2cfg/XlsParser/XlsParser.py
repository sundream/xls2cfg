#coding: utf-8
#@author sundream
#@date 2025-09-10

import os
from XlsParser.Type import Type
from XlsParser.CheckType import escapeString
from XlsParser.Config import Config

class XlsParser(object):
    indent = Config.indent      # 缩进符
    codeComment = None          # 代码注释符
    extension = None            # 扩展名

    def __init__(self,sheet,output):
        self.sheet = sheet
        self.output = output    # 输出路径
        self.deepth = 0
        self.pretty = Config.pretty
        self.singleton = self.sheet.singleton
        self.buildType()
        self.buildData()

    def write(self,filename,data):
        self._write(filename,data)
        if Config.genMeta:
            self.writeMeta(filename)

    def writeMeta(self,filename):
        pass

    def _write(self,filename,data):
        output = self.output
        print("write",output,filename)
        filename = os.path.join(output,filename)
        self.writeTo(filename,data)

    @classmethod
    def writeTo(cls,filename,data):
        filename += cls.extension
        parent_dir = os.path.dirname(filename)
        if parent_dir != "" and not os.path.isdir(parent_dir):
            os.makedirs(parent_dir)
        fd = open(filename,"wb")
        fd.write(data.encode())
        fd.close()

    def isEmpty(self):
        if self.sheet.dataRow == 0:
            return True
        if self.sheet.singleton:
            return False
        for col in range(0,self.sheet.maxCol):
            if self.isNeedExportCol(col):
                return False
        return True

    def isNeedExportCol(self,col):
        if not self.sheet.col2type.get(col):
            return False
        tags = self.sheet.col2tags[col]
        return Config.isNeedExportTags(tags)

    typeMaps = {}       # 类型 -> 语言类型映射

    def buildType(self):
        className = self.__class__.formatClassName(self.sheet.filename)
        self.type = Type.createClass(className)
        if self.sheet.comment:
            self.type.comment = self.sheet.comment
        if self.sheet.singleton:
            self.type.singleton = True
        for col in range(0,self.sheet.maxCol):
            if not self.isNeedExportCol(col):
                continue
            fieldTypename = self.sheet.col2type[col].fullTypename
            fieldName = self.sheet.col2key[col]
            fieldComment = self.sheet.col2desc[col]
            if Config.genMetaDetail:
                comment = self.sheet.col2comment[col]
                if comment:
                    fieldComment = fieldComment +"(" + comment + ")"
            fieldTags = self.sheet.col2tags[col]
            idx = self.type.defineField(fieldTypename,fieldName,fieldComment,fieldTags)
            if not self.sheet.singleton and col == self.sheet.idCol:
                self.type.setIdField(idx)


    @classmethod
    def buildTypeContext(cls,typ):
        hasBigInt = False
        for field in typ.fields:
            if field.type.fullTypename.find("bigint") >= 0:
                hasBigInt = True
        typ.context = {}
        typ.context["hasBigInt"] = hasBigInt
        typ.context["className"] = typ.typename
        typ.context["namespace"] = cls.formatNamespace(Config.namespace)
        typ.context["classComment"] = typ.comment if typ.comment else ""
        idField = typ.getIdField()
        if idField:
            typ.context["idName"] = cls.formatFieldName(idField.name)
            typ.context["idTypename"] = cls.formatType(idField.type)
        fields = []
        if len(cls.typeMaps) == 0:
            return
        for field in typ.fields:
            fields.append({
                "_name": field.name,
                "name": cls.formatFieldName(field.name),
                "typename": cls.formatType(field.type),
                "comment": field.comment,
                "index": field.index,
            })
        typ.context["fields"] = fields

    def buildData(self):
        self.dataMap = {}
        self.dataList = []
        for row in range(0,self.sheet.dataRow):
            data = {}
            for col in range(0,self.sheet.maxCol):
                if not self.isNeedExportCol(col):
                    continue
                value = self.sheet.value(row,col)
                if self.sheet.col2key[col]:
                    data[self.sheet.col2key[col]] = value
            if data:
                self.dataList.append(data)

        if not self.sheet.singleton:
            uniqueKey = self.sheet.col2key[self.sheet.idCol]
            for data in self.dataList:
                uniqueId = data[uniqueKey]
                self.dataMap[uniqueId] = data

    # 生成类定义代码
    @classmethod
    def writeClass(typ,output):
        pass

    # 可重写,调用dump+write完成生成配置
    def parse(self):
        pass

    # 可重写,生成全部配置后最后调用
    @classmethod
    def endParse(cls,outputPath):
        pass

    @classmethod
    def writeAllClass(cls,outputPath):
        for typename,typ in Type.types.items():
            if typ.isClass() and typename != "__Field__":
                cls.writeClass(typ,outputPath)

    @classmethod
    def formatNamespace(cls,namespace):
        return namespace

    @classmethod
    def formatType(cls,typ):
        pass

    @classmethod
    def formatClassName(cls,typename):
        if Config.classNameFirstUpper:
            typename = typename[:1].upper() + typename[1:]
        return typename

    @classmethod
    def formatFieldName(cls,fieldName):
        return fieldName

    # 格式化值,对于json/list/map/array返回字符串列表,否则返回字符串
    def formatValue(self,value):
        self.deepth = self.deepth + 1
        typ = type(value)
        if value is None:
            value = self.formatNull(value)
        elif typ == bool:
            value = self.formatBool(value)
        elif typ == int:
            value = self.formatInt(value)
        elif typ == float:
            value = self.formatFloat(value)
        elif typ == str:
            value = self.formatString(value)
        elif typ == list:
            value = self.formatList(value)
        elif typ == dict:
            value = self.formatMap(value)
        else:
            raise Exception(self.sheet._message(0,0,"value=%s,unknow type=%s" % (value,typ)))
        self.deepth = self.deepth - 1
        return value

    # 可重写
    def formatKey(self,key):
        pass

    # 可重写
    def formatNull(self,value):
        pass

    # 可重写
    def formatBool(self,value):
        pass

    # 可重写
    def formatInt(self,value):
        return str(value)

    # 可重写
    def formatFloat(self,value):
        return str(value)

    # 可重写
    def formatString(self,value):
        value = escapeString(value)
        return '"' + value + '"'

    # 可重写
    def formatList(self,value):
        pass

    # 可重写
    def formatMap(self,value):
        pass