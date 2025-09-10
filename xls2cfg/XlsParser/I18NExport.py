#coding:utf-8
#@author sundream
#@date 2025-09-10

import os
import XlsParser.I18NReadWriter as i18n

sheetI18nTexts = {}                 # 根据xlsFilename分类的国际化文本串: xlsFilename -> {国际化文本串 -> cellname}
i18nTexts = {}                      # 国际化文本串 -> xlsFilename:cellname
localizeTexts = {}                  # 国际化文本串 -> 目标语言文本

def readI18nFile(i18nExportOneFile,i18nDirectory,i18nLanguage,i18nExtension,i18nSeperator):
    texts = []
    dictTexts = {}
    exts = [".txt",".lua",".po"]
    if i18nExtension not in exts:
        raise Exception("unsupported ext: " + i18nExtension)
    if not i18nExportOneFile:
        i18nInputDirectory = os.path.join(i18nDirectory,i18nLanguage)
        for root,dirs,filenames in os.walk(i18nInputDirectory):
            for filename in iter(filenames):
                _,ext = os.path.splitext(filename)
                if ext not in exts:
                    continue
                filename = os.path.join(root,filename)
                tempTexts = i18n.readI18nFile(filename,dictTexts)
                texts.extend(tempTexts)
    else:
        i18nInputFilename = os.path.join(i18nDirectory,i18nLanguage) + i18nExtension
        if not os.path.exists(i18nInputFilename):
            return texts
        texts = i18n.readI18nFile(i18nInputFilename,i18nSeperator,dictTexts)
    global localizeTexts
    localizeTexts = dictTexts
    return texts


def writeI18nFile(i18nExportOneFile,i18nDirectory,i18nLanguage,i18nExtension,i18nSeperator):
    exts = [".txt",".lua",".po"]
    if i18nExtension not in exts:
        raise Exception("unsupported ext: " + i18nExtension)
    if not i18nExportOneFile:
        dirName = os.path.join(i18nDirectory,i18nLanguage)
    else:
        dirName = i18nDirectory
    if not os.path.exists(dirName):
        os.makedirs(dirName)
    print("writeI18nFile",i18nDirectory,i18nLanguage,i18nExtension)
    if not i18nExportOneFile:
        for xlsFilename,dictTexts in sheetI18nTexts.items():
            i18nOutputFilename = os.path.join(dirName,xlsFilename) + i18nExtension
            i18n.writeI18nFile(dictTexts,i18nOutputFilename,i18nSeperator)
    else:
        i18nOutputFilename = os.path.join(i18nDirectory,i18nLanguage) + i18nExtension
        i18n.writeI18nFile(i18nTexts,i18nOutputFilename,i18nSeperator)

def setI18NText(text,filename,comment):
    if filename not in sheetI18nTexts:
        sheetI18nTexts[filename] = {}
    if text in sheetI18nTexts[filename]:
        elem = sheetI18nTexts[filename][text]
        # elem: [原始文本,翻译文本,备注]
        elem[2] = "%s %s" % (elem[2],comment)
    else:
        sheetI18nTexts[filename][text] = [text,"",comment]
    comment = "%s:%s" % (filename,comment)
    if text in i18nTexts:
        elem = i18nTexts[text]
        elem[2] = "%s %s" % (elem[2],comment)
    else:
        i18nTexts[text] = [text,"",comment]

def getLocalizeText(text):
    elem = localizeTexts.get(text)
    if elem and elem[1]:
        return elem[1]
    return None
