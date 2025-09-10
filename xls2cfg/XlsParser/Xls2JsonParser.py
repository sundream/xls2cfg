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
        if self.sheet.singleton:
            self.parseSingletonSheet()
        else:
            self.parseSheet()

    def parseSingletonSheet(self):
        tbl = {}
        line = self.sheet.rows[0]
        for j,key in self.sheet.col2key.items():
            if not self.isNeedExportCol(j):
                continue
            value = line[j]
            tbl[key] = value
        if self.pretty:
            data = json.dumps(tbl,ensure_ascii=False,indent=2)
        else:
            data = json.dumps(tbl,ensure_ascii=False)
        self._write(self.sheet.filename,data)

    def parseSheet(self):
        lst = []
        for row in range(0,self.sheet.dataRow):
            tbl = {}
            for col in range(0,self.sheet.maxCol):
                if not self.isNeedExportCol(col):
                    continue
                value = self.sheet.value(row,col)
                if self.sheet.col2key[col]:
                    tbl[self.sheet.col2key[col]] = value
            lst.append(tbl)
        if self.pretty:
            data = json.dumps(lst,ensure_ascii=False,indent=2)
        else:
            data = json.dumps(lst,ensure_ascii=False)
        self._write(self.sheet.filename,data)