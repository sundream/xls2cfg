#coding: utf-8
#@author sundream
#@date 2025-09-10

import os
from XlsParser.XlsParser import XlsParser

class Xls2LuaParser(XlsParser):
    codeComment = "---"
    extension = ".lua"

    def __init__(self,sheet,output):
        XlsParser.__init__(self,sheet,output)

    def parse(self):
        if self.isEmpty():
            return
        if self.sheet.singleton:
            self.parseSingletonSheet()
        else:
            self.parseSheet()

    def parseSingletonSheet(self):
        # 解析单例表(单条记录)
        table = {}
        line = self.sheet.rows[0]
        for j,key in self.sheet.col2key.items():
            if not self.isNeedExportCol(j):
                continue
            value = line[j]
            table[key] = value
        tableLines = self.formatMap(table)
        tableLines[0] = "return " + tableLines[0]
        if self.pretty:
            data = "\n".join(tableLines)
        else:
            data = "".join(tableLines)
        self.write(self.sheet.filename,data)

    def parseSheet(self):
        # 解析正常表(多条记录)
        indent = self.indent
        lines = []
        for row in range(0,self.sheet.dataRow):
            table = {}
            orderKeys = []
            for col in range(0,self.sheet.maxCol):
                if not self.isNeedExportCol(col):
                    continue
                key = self.sheet.col2key[col]
                value = self.sheet.value(row,col)
                table[key] = value
                orderKeys.append(key)
            tableLines = self.formatMap(table,orderKeys)
            uniqueId = self.sheet.value(row,self.sheet.idCol)
            uniqueId = self.formatKey(uniqueId)
            if self.pretty:
                tableLines[0] = "%s = %s" % (uniqueId,tableLines[0])
                for i,field in enumerate(tableLines):
                    tableLines[i] = indent + field
                line = "\n".join(tableLines)
            else:
                tableLines[0] = "%s=%s" % (uniqueId,tableLines[0])
                line = "".join(tableLines)
            lines.append(line)
        data = "return {\n%s\n}" % ",\n".join(lines)
        self.write(self.sheet.filename,data)

    def formatKey(self,key):
        if type(key) == int:
            return '[%d]' % key
        else:
            if key.isascii() and (key[0].isalpha() or key[0] == "_"):
                return key
            else:
                return '["%s"]' % key

    def formatNull(self,value):
        return "nil"

    def formatBool(self,value):
        if value == False:
            return "false"
        else:
            return "true"

    def formatList(self,value):
        result = []
        result.append('{')
        lst = value
        length = len(lst)
        for i in range(0,length):
            v = lst[i]
            lines = self.formatValue(v)
            if type(lines) != list:
                lines = [lines]
            if self.pretty:
                for j,line in enumerate(lines):
                    lines[j] = self.indent + line
            if i != length - 1:
                lines[len(lines)-1] = lines[len(lines)-1] + ","
            result.extend(lines)
        result.append('}')
        return result

    def formatMap(self,value,orderKeys=None):
        result = []
        result.append('{')
        map = value
        if orderKeys is None:
            orderKeys = list(map.keys())
        length = len(orderKeys)
        for i in range(0,length):
            k = orderKeys[i]
            v = map[k]
            k = self.formatKey(k)
            lines = self.formatValue(v)
            if type(lines) != list:
                lines = [lines]
            if self.pretty:
                lines[0] = "%s = %s" % (k,lines[0])
                for j,line in enumerate(lines):
                    lines[j] = self.indent + line
            else:
                lines[0] = "%s=%s" % (k,lines[0])
            if i != length -1:
                lines[len(lines)-1] = lines[len(lines)-1] + ","
            result.extend(lines)
        result.append('}')
        return result

    def writeMeta(self,filename):
        codeComment = self.codeComment
        lines = []
        if self.type.comment:
            lines.append("%s%s" % (codeComment,self.type.comment))
        lines.append("%s@class Cfg.%s" % (codeComment,self.type.fullTypename))
        for field in self.type.fields:
            lines.append("%s@field %-48s%-32s%s" % (codeComment,field.name,field.type.fullTypename,field.comment))
        data = "\n".join(lines) + "\n\n"
        filename = os.path.join("meta",filename)
        self._write(filename,data)

