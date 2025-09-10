#coding:utf-8
#@author sundream
#@date 2025-09-10

import os
from XlsParser.Sheet import Sheet
from XlsParser.Type import Type
from XlsParser.Config import Config
from openpyxl import load_workbook

def createBuiltinClass():
    Type.createClass("__Field__",[
        {
            "type" : "string",
            "name" : "name",
            "comment" : "字段名",
            "tags" : [],
        },
        {
            "type" : "string",
            "name" : "type",
            "comment" : "字段类型",
            "tags" : [],
        },
        {
            "type" : "string",
            "name" : "comment",
            "comment" : "字段备注",
            "tags" : [],
        },
        {
            "type" : "list<string>",
            "name" : "tags",
            "comment" : "字段标签列表",
            "tags" : [],
        }
    ])

def readClass(excelDir):
    filename = os.path.join(excelDir,"__class__.xlsx")
    if not os.path.exists(filename):
        return
    createBuiltinClass()
    sheetName = "data"
    wb = load_workbook(filename = filename,data_only=True)
    sheet = Sheet(wb[sheetName],filename,sheetName)
    for row in sheet.rows:
        typename = row[0]
        comment = row[1]
        fields = row[2]
        for j in range(len(fields)-1,-1,-1):
            if fields[j]["type"] == '' or not Config.isNeedExportTags(fields[j]["tags"]):
                fields.pop(j)
        if len(fields) > 0:
            typ = Type.createClass(typename,fields)
            if comment:
                typ.comment = comment