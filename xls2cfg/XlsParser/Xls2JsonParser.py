#coding: utf-8
#@author sundream
#@date 2025-09-10

from XlsParser.XlsParser import XlsParser
import json

class Xls2JsonParser(XlsParser):
    extension = ".json"

    def __init__(self,sheet,output):
        XlsParser.__init__(self,sheet,output)

    def parse(self):
        if self.isEmpty():
            return
        if self.singleton:
            self.parseSingletonSheet()
        else:
            self.parseSheet()

    def parseSingletonSheet(self):
        data = self.dataList[0]
        if self.pretty:
            data = json.dumps(data,ensure_ascii=False,indent=2)
        else:
            data = json.dumps(data,ensure_ascii=False)
        self._write(self.sheet.filename,data)

    def parseSheet(self):
        if self.pretty:
            data = json.dumps(self.dataList,ensure_ascii=False,indent=2)
        else:
            data = json.dumps(self.dataList,ensure_ascii=False)
        self._write(self.sheet.filename,data)