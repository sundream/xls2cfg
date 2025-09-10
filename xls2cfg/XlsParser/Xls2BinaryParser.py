#coding: utf-8
#@author sundream
#@date 2025-09-10

from XlsParser.XlsParser import XlsParser
from XlsParser.ByteStream import ByteStream
import os

class Xls2BinaryParser(XlsParser):
    extension = ".bytes"

    def __init__(self,sheet,output):
        XlsParser.__init__(self,sheet,output)

    def parse(self):
        self.bs = ByteStream()
        if self.isEmpty():
            return
        if self.sheet.singleton:
            self.parseSingletonSheet()
        else:
            self.parseSheet()
        self.bs = None

        # # test readFile
        # output = self.output
        # filename = self.sheet.filename
        # filename = os.path.join(output,filename + self.extension)
        # self.readFile(filename,self.sheet.singleton)

    def parseSingletonSheet(self):
        line = self.sheet.rows[0]
        fieldIndex = -1
        for j,key in self.sheet.col2key.items():
            if not self.isNeedExportCol(j):
                continue
            fieldIndex = fieldIndex + 1
            value = line[j]
            self.bs.WriteValue(self.type.fields[fieldIndex].type,value)
        self.writeFile(self.sheet.filename)

    def parseSheet(self):
        self.bs.WriteUInt16(self.sheet.dataRow)
        for row in range(0,self.sheet.dataRow):
            fieldIndex = -1
            for col in range(0,self.sheet.maxCol):
                if not self.isNeedExportCol(col):
                    continue
                fieldIndex = fieldIndex + 1
                value = self.sheet.value(row,col)
                self.bs.WriteValue(self.type.fields[fieldIndex].type,value)
        self.writeFile(self.sheet.filename)

    def writeFile(self,filename):
        output = self.output
        print("write",output,filename)
        filename = os.path.join(output,filename + self.extension)
        parent_dir = os.path.dirname(filename)
        if parent_dir != "" and not os.path.isdir(parent_dir):
            os.makedirs(parent_dir)
        self.bs.WriteFile(filename)

    def readFile(self,filename,singleton):
        self.bs = ByteStream()
        self.bs.ReadFile(filename)
        data = {}
        if singleton:
            fieldDict = {}
            for field in self.type.fields:
                value = self.bs.ReadValue(field.type)
                fieldDict[field.name] = value
            data = fieldDict
        else:
            dataRow = self.bs.ReadUInt16()
            for i in range(dataRow):
                fieldDict = {}
                for field in self.type.fields:
                    value = self.bs.ReadValue(field.type)
                    fieldDict[field.name] = value
                fieldId = fieldDict[self.type.fields[self.type.idFieldIdx].name]
                data[fieldId] = fieldDict
        self.bs = None
        # print("readFile",data)