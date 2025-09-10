#coding: utf-8
#@author: sundream
#@email: linguanglianglgl@gmail.com
#@date: 2021-02-05
#@version: 0.1.0

import sys
import optparse
import os
import json
import subprocess
from XlsParser.Xls2PyParser import Xls2PyParser
from XlsParser.Xls2LuaParser import Xls2LuaParser
from XlsParser.Xls2LuaCvsParser import Xls2LuaCvsParser
from XlsParser.Xls2JsonParser import Xls2JsonParser
from XlsParser.Xls2BinaryParser import Xls2BinaryParser
from XlsParser.Xls2CSharpParser import Xls2CSharpParser
from XlsParser.Sheet import Sheet
from XlsParser.Sheet import getSheets
from XlsParser.I18NExport import readI18nFile,writeI18nFile
from XlsParser.XlsClass import readClass
from XlsParser.Config import Config
from openpyxl import load_workbook

def main():
    usage = \
"""usage: python %prog [options]
e.g:
    python %prog --config=config.json"""
    parser = optparse.OptionParser(usage=usage,version="%prog 0.0.1")
    parser.add_option("-c","--config",help="[required] json config file")
    parser.add_option("-x","--onlyExportChange",action="store_true",default=False,help="[optional] only export change files")
    options,args = parser.parse_args()
    required = ["config"]
    for r in required:
        if options.__dict__.get(r) is None:
            parser.error("option '%s' required" % r)
    configFileName = options.config
    if not configFileName.endswith(".json"):
        parser.error("config file need json")
        return
    fp = open(configFileName,"r",encoding="utf-8")
    txtConfig = fp.read()
    fp.close()
    jsonConfig = json.loads(txtConfig)
    inputDir = jsonConfig.get("input")
    if inputDir is None:
        parser.error("config 'input' required")
    outputDir = jsonConfig.get("output")
    if outputDir is None:
        parser.error("config 'output' required")
    outputFormats = jsonConfig.get("outputFormats")
    if outputFormats is None:
        parser.error("config 'outputFormat' required")
    onlyExportChange = options.onlyExportChange
    exportFileList = []
    if onlyExportChange:
        result = subprocess.check_output(["svn", "status", inputDir], universal_newlines=True)
        lines = result.splitlines()
        for line in lines:
            lst = line.split(maxsplit=1)
            tag,fileName = lst[0],lst[1]
            if tag == "A" or tag == "M" or tag == "?":
                fileName = fileName.replace("\\","/")
                exportFileList.append(fileName)
    i18nExportOneFile = jsonConfig.get("i18nExportOneFile")
    i18nDirectory = jsonConfig.get("i18nDirectory")
    i18nLanguage = jsonConfig.get("i18nLanguage")
    i18nExtension = jsonConfig.get("i18nExtension") or ".po"
    i18nSeperator = jsonConfig.get("i18nSeperator") or "<:>"
    exclude = jsonConfig.get("exclude") or []

    if "genHeader" in jsonConfig:
        Config.genHeader = jsonConfig.get("genHeader")
    if "genHeaderDetail" in jsonConfig:
        Config.genHeaderDetail = jsonConfig.get("genHeaderDetail")
    if "pretty" in jsonConfig:
        Config.pretty = jsonConfig.get("pretty")
    if "defaults" in jsonConfig:
        Config.defaults = jsonConfig.get("defaults")
    if "tags" in jsonConfig:
        Config.tags = jsonConfig.get("tags")
    if "classNameFirstUpper" in jsonConfig:
        Config.classNameFirstUpper = jsonConfig.get("classNameFirstUpper")
    if "constraintSeperator" in jsonConfig:
        Config.constraintSeperator = jsonConfig.get("constraintSeperator")
    if "indent" in jsonConfig:
        Config.indent = jsonConfig.get("indent")
    if "localize" in jsonConfig:
        Config.localize = jsonConfig.get("localize")
    if "keywords" in jsonConfig:
        keywords = jsonConfig.get("keywords") or []
        Config.keywords = dict.fromkeys(keywords,True)

    # print(inputDir,outputDir,outputFormats,Config.genHeader,Config.genHeaderDetail,i18nDirectory,i18nLanguage,i18nExportOneFile,i18nExtension,Config.pretty,exclude,Config.classNameFirstUpper,Config.localize)
    # 载入本地化文本
    if i18nLanguage:
        readI18nFile(i18nExportOneFile,i18nDirectory,i18nLanguage,i18nExtension,i18nSeperator)
    sheets = getSheets()
    readClass(inputDir)
    # 载入所有表
    for root,dirs,files in os.walk(inputDir):
        for dirname in dirs:
            for outputFormat in outputFormats:
                outputPath = os.path.join(outputDir,outputFormat,dirname)
                if not os.path.exists(outputPath):
                    os.makedirs(outputPath)
        for fileName in files:
            if fileName.startswith("~$"):
                # 临时文件
                continue
            if fileName.startswith("__class__"):
                # 类定义文件
                continue
            fullFileName = root + "/" + fileName
            if onlyExportChange and fullFileName not in exportFileList:
                continue
            relativeDirName = os.path.relpath(root,inputDir)
            if relativeDirName != "" and relativeDirName != ".":
                fullFileName = os.path.join(relativeDirName,fileName)
            else:
                fullFileName = fileName
            if fullFileName in exclude:
                continue
            wb = load_workbook(filename = os.path.join(root,fileName),data_only=True)
            for sheetName in wb.sheetnames:
                if sheetName.startswith("_") or sheetName.startswith("Sheet") or not sheetName.isascii():
                    continue
                sheet = Sheet(wb[sheetName],fullFileName,sheetName)
                sheets[sheet.filename] = sheet
        # 表的引用检查(当onlyExportChange存在时,检查引用可能失效,此时你应该采用导出全表方式)
    if not onlyExportChange:
        for sheetName,sheet in sheets.items():
            sheet.checkRef()
    # 拆分表
    splitSheets = {}
    for sheetName,sheet in sheets.items():
        if sheet.splitCol != -1:
            splitSheets[sheet.filename] = sheet
    for sheetName,sheet in splitSheets.items():
        sheets.pop(sheetName)
        tempSheets = sheet.splitSheets()
        for tempSheet in tempSheets:
            sheets[tempSheet.filename] = tempSheet
            print("splitSheet,filename=%s,maxCol=%s,dataRow=%s,idCol=%d" % (tempSheet.filename,tempSheet.maxCol,tempSheet.dataRow,tempSheet.idCol))

    # 合并表
    merge = jsonConfig.get("merge")
    if merge != None:
        for toFileName,fromFileNames in merge.items():
            toSheet = sheets.get(toFileName)
            if toSheet != None:
                for fromFileName in fromFileNames:
                    fromSheet = sheets.get(fromFileName)
                    if fromSheet != None:
                        sheets.pop(fromFileName)
                        toSheet.mergeFrom(fromSheet)
    for outputFormat in outputFormats:
        print("xls2cfg,outputDir=%s,outputFormat=%s" % (outputDir,outputFormat))
        if outputFormat == "lua":
            Parser = Xls2LuaParser
        elif outputFormat == "luacvs":
            Parser = Xls2LuaCvsParser
        elif outputFormat == "py":
            Parser = Xls2PyParser
        elif outputFormat == "json":
            Parser = Xls2JsonParser
        elif outputFormat == "binary":
            Parser = Xls2BinaryParser
        elif outputFormat == "csharp":
            Parser = Xls2CSharpParser

        # 生成配置文件
        output = os.path.join(outputDir,outputFormat)
        for sheetName,sheet in sheets.items():
            parser = Parser(sheet,output)
            parser.parse()
        Parser.endParse(output)

    # 生成国际化待翻译文本(如果目标文件已存在,则合并翻译文本)
    if not onlyExportChange and i18nLanguage:
        writeI18nFile(i18nExportOneFile,i18nDirectory,i18nLanguage,i18nExtension,i18nSeperator)

if __name__ == "__main__":
    main()
