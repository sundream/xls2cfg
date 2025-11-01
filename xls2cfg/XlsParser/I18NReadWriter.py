#coding:utf-8
#@author sundream
#@date 2025-09-10

import os
import sys
import io
import string
import json
import re

def _readI18nTxtFile(filename,i18nSeperator,dictTexts):
    if not os.path.exists(filename):
        return []
    texts = []
    fd = open(filename,"rb")
    if not fd:
        raise Exception("file not exists: " + filename)
    comment = None
    for line in fd.read().splitlines():
        line = line.decode()
        if line.startswith("#: "):
            comment = line[3:]
        else:
            k,v = line.split(i18nSeperator)
            if k != "" and dictTexts.get(k) is None:
                elem = [k,v,comment]
                texts.append(elem)
                dictTexts[k] = elem
            comment = None
    fd.close()
    return texts

def _readI18nLuaFile(filename,dictTexts):
    if not os.path.exists(filename):
        return []
    patten = re.compile(r'\s*\["(.+)"\] = "(.*)"',re.S)
    texts = []
    fd = open(filename,"rb")
    if not fd:
        raise Exception("file not exists: " + filename)
    comment = None
    for line in fd.read().splitlines():
        line = line.decode()
        if line == "return {" or line == "}":
            continue
        if line.startswith("    -- "):
            comment = line[8:]
        else:
            matchObj = patten.match(line)
            if not matchObj:
                raise Exception("invalid text format,filename=%s,line=%s" % (filename,line))
            k,v = matchObj.group(1),matchObj.group(2)
            if k != "" and dictTexts.get(k) is None:
                elem = [k,v,comment]
                texts.append(elem)
                dictTexts[k] = elem
            comment = None
    fd.close()
    return texts

def _readI18nPoFile(filename,dictTexts):
    if not os.path.exists(filename):
        return []
    texts = []
    fd = open(filename,"rb")
    if not fd:
        raise Exception("file not exists: " + filename)
    msgid = None
    msgstr = None
    comment = None
    for line in fd.read().splitlines():
        line = line.decode()
        length = len(line)
        if line.startswith("#: "):
            comment = line[3:]
        elif line[0:6] == "msgid ":
            if msgid:
                raise Exception("invalid format,i18nInputFile=%s" % filename)
            msgid = line[7:length-1]
        elif line[0:7] == "msgstr ":
            if not msgid:
                raise Exception("invalid format,i18nInputFile=%s" % filename)
            msgstr = line[8:length-1]
            if msgid != "" and dictTexts.get(msgid) is None:
                elem = [msgid,msgstr,comment]
                texts.append(elem)
                dictTexts[msgid] = elem
            msgid = None
            comment = None
    return texts

def _writeI18nTxtFile(filename,newDictTexts,i18nSeperator):
    change = False
    oldDictTexts = {}
    oldTexts = _readI18nTxtFile(filename,i18nSeperator,oldDictTexts)
    dictTexts = {}
    for k,elem in newDictTexts.items():
        oldElem = oldDictTexts.get(k)
        if oldElem:
            if oldElem[2] != elem[2]:
                # update comment
                change = True
                oldElem[2] = elem[2]
            if oldElem[1] == "" and elem[1] != "":
                # merge text
                change = True
                oldElem[1] = elem[1]
        else:
            change = True
            dictTexts[k] = elem
    if not change:
        return
    listTexts = list(dictTexts.keys())
    listTexts.sort()
    for i in range(len(listTexts)):
        k = listTexts[i]
        oldTexts.append([k,dictTexts[k][1],dictTexts[k][2]])
    lines = []
    for elem in oldTexts:
        k = elem[0]
        v = elem[1]
        comment = elem[2]
        if comment and False:
            # txt格式不写入注释
            line = "#: " + comment + "\n"
        else:
            line = ""
        line = line + "%s%s%s" % (k,i18nSeperator,v)
        lines.append(line)
    data = "\n".join(lines)
    fd = open(filename,"wb")
    fd.write(data.encode())
    fd.close()

def _writeI18nLuaFile(filename,newDictTexts):
    change = False
    oldDictTexts = {}
    oldTexts = _readI18nLuaFile(filename,oldDictTexts)
    dictTexts = {}
    for k,elem in newDictTexts.items():
        oldElem = oldDictTexts.get(k)
        if oldElem:
            if oldElem[2] != elem[2]:
                # update comment
                change = True
                oldElem[2] = elem[2]
            if oldElem[1] == "" and elem[1] != "":
                # merge text
                change = True
                oldElem[1] = elem[1]
        else:
            change = True
            dictTexts[k] = elem
    if not change:
        return
    listTexts = list(dictTexts.keys())
    listTexts.sort()
    for i in range(len(listTexts)):
        k = listTexts[i]
        oldTexts.append([k,dictTexts[k][1],dictTexts[k][2]])
    lines = []
    for elem in oldTexts:
        k = elem[0]
        v = elem[1]
        comment = elem[2]
        if comment:
            line = "    -- " + comment + "\n"
        else:
            line = ""
        line = line + '    ["%s"] = "%s"' % (k,v)
        lines.append(line)
    data = ",\n".join(lines)
    data = "return {\n" + data + "\n}"
    fd = open(filename,"wb")
    fd.write(data.encode())
    fd.close()

def _writeI18nPoFile(filename,newDictTexts):
    change = False
    oldDictTexts = {}
    oldTexts = _readI18nPoFile(filename,oldDictTexts)
    dictTexts = {}
    for k,elem in newDictTexts.items():
        oldElem = oldDictTexts.get(k)
        if oldElem:
            if oldElem[2] != elem[2]:
                # update comment
                change = True
                oldElem[2] = elem[2]
            if oldElem[1] == "" and elem[1] != "":
                # merge text
                change = True
                oldElem[1] = elem[1]
        else:
            change = True
            dictTexts[k] = elem
    if not change:
        return
    listTexts = list(dictTexts.keys())
    listTexts.sort()
    for i in range(len(listTexts)):
        k = listTexts[i]
        oldTexts.append([k,dictTexts[k][1],dictTexts[k][2]])
    lines = []
    for elem in oldTexts:
        k = elem[0]
        v = elem[1]
        comment = elem[2]
        if comment:
            line = "#: " + comment + "\n"
        else:
            line = ""
        line = line + 'msgid "%s"\nmsgstr "%s"\n' % (k,v)
        lines.append(line)
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    fd = open(filename,"wb")
    data = "\n".join(lines)
    fd.write(data.encode())
    fd.close()

def readI18nFile(i18nInputFilename,i18nSeperator,dictTexts):
    texts = []
    exts = [".txt",".lua",".po"]
    i18nExtension = os.path.splitext(i18nInputFilename)[1]
    if i18nExtension not in exts:
        raise Exception("unsupported ext: " + i18nExtension)
    if not os.path.exists(i18nInputFilename):
        return texts
    if i18nExtension == ".txt":
        texts = _readI18nTxtFile(i18nInputFilename,i18nSeperator,dictTexts)
    elif i18nExtension == ".lua":
        texts = _readI18nLuaFile(i18nInputFilename,dictTexts)
    elif i18nExtension == ".po":
        texts = _readI18nPoFile(i18nInputFilename,dictTexts)
    return texts

def writeI18nFile(texts,i18nOutputFilename,i18nSeperator):
    exts = [".txt",".lua",".po"]
    i18nExtension = os.path.splitext(i18nOutputFilename)[1]
    if i18nExtension not in exts:
        raise Exception("unsupported ext: " + i18nExtension)
    if i18nExtension == ".txt":
        _writeI18nTxtFile(i18nOutputFilename,texts,i18nSeperator)
    elif i18nExtension == ".lua":
        _writeI18nLuaFile(i18nOutputFilename,texts)
    elif i18nExtension == ".po":
        _writeI18nPoFile(i18nOutputFilename,texts)