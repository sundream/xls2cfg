#coding: utf-8
#@author sundream
#@date 2025-09-10

from XlsParser.XlsParser import XlsParser

class Xls2LuaCvsParser(XlsParser):
    codeComment = "---"
    extension = ".lua"

    def __init__(self,sheet,output):
        XlsParser.__init__(self,sheet,output)

    def parse(self):
        if self.isEmpty():
            return
        indent = self.indent
        lines = []
        header = []
        for col in range(0,self.sheet.maxCol):
            if not self.isNeedExportCol(col):
                continue
            key = self.sheet.col2key[col]
            header.append(key)
            fields = self.formatList(header)
            uniqueId = '["header"]'
            if self.pretty:
                fields[0] = "%s = %s" % (uniqueId,fields[0])
                for i,field in enumerate(fields):
                    fields[i] = indent + field
                line = "\n".join(fields)
            else:
                fields[0] = "%s=%s" % (uniqueId,fields[0])
                line = "".join(fields)
        lines.append(line)

        for row in range(0,self.sheet.dataRow):
            lst = []
            for col in range(0,self.sheet.maxCol):
                if not self.isNeedExportCol(col):
                    continue
                value = self.sheet.value(row,col)
                lst.append(value)
            fields = self.formatList(lst)
            if self.sheet.singleton:
                uniqueId = "__singleton"
            else:
                uniqueId = self.sheet.value(row,self.sheet.idCol)
                uniqueId = self.formatKey(uniqueId)
            if self.pretty:
                fields[0] = "%s = %s" % (uniqueId,fields[0])
                for i,field in enumerate(fields):
                    fields[i] = indent + field
                line = "\n".join(fields)
            else:
                fields[0] = "%s=%s" % (uniqueId,fields[0])
                line = "".join(fields)
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