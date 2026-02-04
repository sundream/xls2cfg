#coding:utf-8
#@author sundream
#@date 2025-09-10

import os
from openpyxl.utils import get_column_letter
from XlsParser.CheckType import toValue
from XlsParser.Type import Type
from XlsParser import Convert
from XlsParser.Config import Config
from copy import deepcopy

sheets = {}

def getSheets():
    return sheets

class MergeCell(object):
    # list<any> 和 map<string,any>类型允许拆分单元格填值
    def __init__(self,startCol,count):
        self.startCol = startCol                # 起始列号(0-based)
        self.count = count                      # 占据单元格数
        self.type = None                        # 类型
        self.mapkeys = {}                       # key字典: key -> True
        self.fieldCount = None                  # 元素字段数

    def setType(self,type):
        self.type = type
        if self.type.typename == "list" and self.type.valueType.isClass():
            self.fieldCount = len(self.type.valueType.fields)

class Sheet(object):
    def __init__(self,sheet,xlsFilename,sheetName):
        self.xlsFilename = xlsFilename
        self.sheetName = sheetName
        fileNameList = self.xlsFilename.split("@")
        if len(fileNameList) == 1:
            self.filename = os.path.splitext(fileNameList[0])[0]
            self.comment = None
        else:
            self.filename = fileNameList[0]
            self.comment = os.path.splitext(fileNameList[1])[0]
        if sheetName != "data":
            self.filename = self.filename + "_" + sheetName
        self.defaults = deepcopy(Config.defaults)
        for k,v in Type.basicTypes.items():
            if not self.defaults.get(k):
                self.defaults[k] = v
        for k,v in Type.containerTypes.items():
            if not self.defaults.get(k):
                self.defaults[k] = v
        self.constraintSeperator = Config.constraintSeperator
        self.sheet = sheet
        # 前5行为头部信息(1-based),1=描述,2=字段name,3=类型,4=约束,5=tag标签
        self.headerRow = 5              # 表头5行
        self.col2desc = {}              # 列号 -> 描述(0-based)
        self.col2comment = {}           # 列号 -> 批注
        self.col2key = {}               # 列号 -> 变量名
        self.col2type = {}              # 列号 -> 类型
        self.col2constraint = {}        # 列号 -> 约束
        self.col2tags = {}              # 列号 -> [tag,...]
        self.idCol = 0                  # id列
        self.splitCol = -1              # 拆分列
        self.splitIdCol = -1            # 拆分主键列
        self.col2uniques = {}           # 列唯一性检查表
        self.key2col = {}               # 变量名 -> 列号,方便引用检查
        self.rows = []                  # 表格数据
        self.maxRow = 0                 # 最大行号
        self.maxCol = 0                 # 最大列号
        self.dataRow = 0                # 有效数据行数(不包括表头行)
        self.mergeCells = {}            # 列号 -> 合并单元格信息{col: 合并到单元格的列号, type: 类型, count=合并单元格数, mapkeys=固定key字典}
        self.col2mapkey = {}            # 列号 -> mapkey
        if self.sheet == None:
            return
        self.maxRow = self.sheet.max_row
        self.maxCol = self.sheet.max_column
        self.singleton = False          # True=单例表
        for firstRow in self.sheet.iter_rows(min_row=1,max_row=self.headerRow):
            for j in range(0,self.maxCol):
                cell = firstRow[j]
                if cell.value:
                    if cell.value.startswith("#"):
                        if cell.value == "##end":
                            self.maxCol = j
                        elif cell.value == "##key" and j == 0:
                            self.singleton = True
                        else:
                            self.col2tags[j] = ["__ignore"]
            break
        if self.singleton:
            self.initSingletonSheet()
            return
        # 依据第3行合并的单元格信息确定哪些数据需要合并单元格
        for mergedCell in self.sheet.merged_cells.ranges:
            # 1-based
            startCol,startRow,endCol,endRow = mergedCell.bounds
            assert(startRow == endRow)
            if startRow > 3:
                raise("mergeCell only allow in first 3 rows")
            startCol -= 1
            if startRow == 3:
                self.mergeCells[startCol] = MergeCell(startCol,endCol-startCol)
                for i in range(startCol,endCol):
                    self.mergeCells[i] = self.mergeCells[startCol]

        i = 0
        for row in self.sheet.iter_rows(min_row=1,max_row=self.headerRow):
            i = i + 1
            for j in range(0,self.maxCol):
                cell = row[j]
                if i == 1:
                    if cell.value is None:
                        self.col2desc[j] = None
                    else:
                        self.col2desc[j] = cell.value.replace('\n',' ')
                    if cell.comment is None:
                        self.col2comment[j] = None
                    else:
                        self.col2comment[j] = cell.comment.text.replace('\n',' ')
                elif i == 2:
                    name = cell.value
                    if name is not None:
                        name = name.strip()
                        if Config.isKeyword(name):
                            raise Exception(self._message(i,j,name + " is keywords"))
                        if name in self.key2col:
                            raise Exception(self._message(i,j,"repeat key=%s" % name))
                        self.col2key[j] = name
                        self.key2col[name] = j
                    else:
                        self.col2key[j] = None
                elif i == 3:
                    self.col2type[j] = None
                    typename = cell.value
                    if typename is None:
                        if self.col2key.get(j) is None:
                            # 空列,可能是备注列
                            continue
                        raise Exception(self.message(i,j,"typename required"))
                    try:
                        typ = Type.getOrCreate(typename)
                    except Exception as e:
                        raise Exception(self.message(i,j,e))
                    self.col2type[j] = typ
                    if j in self.mergeCells:
                        self.mergeCells[j].setType(typ)
                elif i == 4:
                    self.col2constraint[j] = {}
                    typ = self.col2type[j]
                    if cell.value is not None:
                        kvs = cell.value.split(self.constraintSeperator)
                        for kv in kvs:
                            lst = kv.split("=")
                            k = lst[0]
                            v = None
                            if len(lst) > 1:
                                v = lst[1]
                            if k == "convert" or k == "ref":
                                if v is None:
                                    raise Exception(self._message(i,j,"expire format '%s=value'" % k))
                                self.col2constraint[j][k] = v
                            elif k == "min" or k == "max":
                                if v is None:
                                    raise Exception(self._message(i,j,"expire format '%s=value'" % k))
                                self.col2constraint[j][k] = int(v)
                            elif k == "default":
                                if v is None:
                                    raise Exception(self._message(i,j,"expire format '%s=value'" % k))
                                # allow default=nil or default=None
                                if v == "nil" or v == "None":
                                    v = None
                                else:
                                    ok,v = toValue(v,typ)
                                    if not ok:
                                        errMsg = v
                                        raise Exception(self._message(i,j,errMsg))
                                self.col2constraint[j][k] = v
                            elif k == "unique":
                                self.col2constraint[j][k] = True
                            elif k == "not_null":
                                self.col2constraint[j][k] = True
                            elif k == "not_localize":
                                self.col2constraint[j][k] = True
                            elif k == "split":
                                try:
                                    # 1-based
                                    v = int(v) - 1
                                except Exception as e:
                                    if v not in self.key2col:
                                        raise Exception("invalid split column: %s" % v)
                                    v = self.key2col[v]
                                self.col2constraint[j][k] = v
                                if self.splitCol != -1 and self.splitCol != j:
                                    raise Exception("multiple split constraint")
                                self.splitCol = j
                                self.splitIdCol = v
                                if self.splitCol == self.splitIdCol:
                                    raise Exception("split column == id column")
                                if self.splitIdCol < 0:
                                    raise Exception("split id column < 0")
                            elif k == "limit":
                                if v is None:
                                    raise Exception(self._message(i,j,"expire format '%s=value'" % k))
                                self.col2constraint[j][k] = eval(v)
                            elif k.startswith("."):
                                mapkey = k[1:]
                                self.col2mapkey[j] = mapkey
                                mergeCell = self.mergeCells[j]
                                mergeCell.mapkeys[mapkey] = True
                                mergeColType = mergeCell.type
                                if mergeColType.typename != "map":
                                    mergeColType = mergeColType.valueType
                                if mergeColType.typename != "map" and not mergeColType.isClass():
                                    raise Exception(self._message(i,j,"invalid mapkey '%s',merge cell type exepect map/class,but got '%s'" % (k,mergeColType)))
                            else:
                                raise Exception(self._message(i,j,"invalid constraint,value='%s',constraint seperator is '%s'" % (cell.value,self.constraintSeperator)))
                    if self.getConstraint(j,"unique") and not self.getConstraint(j,"not_null"):
                        # unique列自带not_null约束
                        self.col2constraint[j]["not_null"] = True
                elif i == 5:
                    mergeCell = self.mergeCells.get(j)
                    if mergeCell and len(mergeCell.mapkeys) > 0:
                        mergeCell.fieldCount = len(mergeCell.mapkeys)
                    if cell.value:
                        tags = cell.value.split(",")
                        if j not in self.col2tags:
                            self.col2tags[j] = []
                        self.col2tags[j].extend(tags)
                    elif j not in self.col2tags:
                        self.col2tags[j] = None

        if self.splitCol == -1 and not self.getConstraint(0,"unique"):
            self.col2constraint[0]["unique"] = True

        for i,row in enumerate(self.sheet.iter_rows(min_row=self.headerRow+1,max_row=self.maxRow,values_only=True)):
            if row[0] is None or (type(row[0]) == str and row[0].isspace()):
                # 遇到空行则结束
                break
            if type(row[0]) == str and row[0].startswith("#"):
                # 忽略注释行
                continue
            self.dataRow = self.dataRow + 1
            line = []
            self.rows.append(line)
            # 约束检查
            for j in range(0,self.maxCol):
                value = row[j]
                not_null = self.getConstraint(j,"not_null")
                if not_null and value is None:
                    raise Exception(self.message(i,j,"can not be null"))
                typ = self.getColType(j)
                if typ is None:
                    # 空列/备注列
                    line.append(value)
                    continue
                localize = Config.localize
                if self.getConstraint(j,"not_localize"):
                    localize = False
                ok,errMsg = toValue(value,typ,{
                    "xlsFilename":self.filename,
                    "row":i,
                    "col":j,
                    "localize":localize,
                    "depth":0,
                })
                if not ok:
                    raise Exception(self.message(i,j,errMsg))
                else:
                    value = errMsg
                typename = typ.typename
                if value is None:
                    value = self.getDefault(i,j)
                else:
                    convert = self.getConvert(j)
                    if convert:
                        value = convert(value)
                unique = self.getConstraint(j,"unique")
                if unique:
                    if j not in self.col2uniques:
                        uniques = {}
                        self.col2uniques[j] = uniques
                    else:
                        uniques = self.col2uniques[j]
                    if value in uniques:
                        raise Exception(self.message(i,j,"not unique,conflict with cell %s" % (self.cellname(uniques[value],j))))
                    uniques[value] = self.headerRow + i
                minValue = self.getConstraint(j,"min")
                if minValue is not None and value < minValue:
                    raise Exception(self.message(i,j,"min=%s,value=%s" % (minValue,value)))
                maxValue = self.getConstraint(j,"max")
                if maxValue is not None and value > maxValue:
                    raise Exception(self.message(i,j,"max=%s,value=%s" % (maxValue,value)))
                limit = self.getConstraint(j,"limit")
                if limit is not None and value not in limit:
                    raise Exception(self.message(i,j,"limit=%s,value=%s" % (limit,value)))
                if j in self.mergeCells:
                    mergeCell = self.mergeCells[j]
                    mergeCellType = mergeCell.type
                    mergeStartCol = mergeCell.startCol
                    if mergeCellType.typename == "list":
                        if j == mergeStartCol:
                            lst = []
                            line.append(lst)
                        else:
                            lst = line[mergeStartCol]
                        if j in self.col2mapkey:
                            # type: list<map<string,any>>  or list<Class>
                            mapkey = self.col2mapkey[j]
                            assert(mergeCellType.valueType.typename == "map" or mergeCellType.valueType.isClass())
                            fieldCount = mergeCell.fieldCount
                            elemIdx = (j - mergeStartCol) // fieldCount
                            if (j - mergeStartCol) % fieldCount == 0:
                                map = {}
                                lst.append(map)
                            else:
                                map = lst[elemIdx]
                            map[mapkey] = value
                        else:
                            # type: list<any>
                            lst.append(value)
                    elif mergeCellType.typename == "map":
                        # type: map<string,any>
                        if j == mergeStartCol:
                            map = {}
                            line.append(map)
                        else:
                            map = line[mergeStartCol]
                        mapkey = self.col2mapkey[j]
                        map[mapkey] = value
                    if j != mergeStartCol:
                        # 空值占位
                        line.append(None)
                else:
                    line.append(value)

        print("loadSheet,xlsFilename=%s,sheetName=%s,maxRow=%d,maxCol=%d,dataRow=%d" % (self.xlsFilename,self.sheetName,self.maxRow,self.maxCol,self.dataRow))

    def initSingletonSheet(self):
        # 首行为表头行,固定名字为: key | type | value | tags | desc
        self.headerRow = 1
        self.header = {}            # col -> keyword
        for row in self.sheet.iter_rows(min_row=1,max_row=self.headerRow):
            for j in range(0,self.maxCol):
                cell = row[j]
                value = cell.value
                if value is None:
                    continue
                if value == "##key":
                    self.header[j] = "key"
                elif value == "type":
                    self.header[j] = "type"
                elif value == "value":
                    self.header[j] = "value"
                elif value == "tags":
                    self.header[j] = "tags"
                elif value == "desc":
                    self.header[j] = "desc"
        line = []
        self.rows.append(line)
        for i,row in enumerate(self.sheet.iter_rows(min_row=self.headerRow+1,max_row=self.maxRow,values_only=True)):
            if row[0] is None or (type(row[0]) == str and row[0].isspace()):
                # 遇到空行则结束
                break
            if type(row[0]) == str and row[0].startswith("#"):
                # 忽略注释行
                self.col2type[i] = None
                line.append(None)
                continue
            for j in range(0,self.maxCol):
                value = row[j]
                self.col2comment[i] = None
                if self.header[j] == "key":
                    if Config.isKeyword(value):
                        raise Exception(self.message(i,j,value + " is keywords"))
                    if value in self.key2col:
                        raise Exception(self.message(i,j,"repeat key=%s" % value))
                    self.col2key[i] = value
                    self.key2col[value] = j
                elif self.header[j] == "type":
                    try:
                        typ = Type.getOrCreate(value)
                    except Exception as e:
                        raise Exception(self.message(i,j,e))
                    self.col2type[i] = typ
                elif self.header[j] == "value":
                    if value is None:
                        value = self.getDefault(j,i)
                    ok,value = toValue(value,typ)
                    if not ok:
                        errMsg = value
                        raise Exception(self.message(i,j,errMsg))
                    line.append(value)
                elif self.header[j] == "tags":
                    if value:
                        tags = value.split(",")
                        self.col2tags[i] = tags
                    else:
                        self.col2tags[i] = None
                elif self.header[j] == "desc":
                    self.col2desc[i] = value
        self.dataRow = 1
        self.maxCol = self.maxRow
        self.maxRow = self.headerRow + 1    # 1 row
        print("loadSingletonSheet,xlsFilename=%s,sheetName=%s,maxRow=%d,maxCol=%d,dataRow=%d" % (self.xlsFilename,self.sheetName,self.maxRow,self.maxCol,self.dataRow))


    def message(self,row,col,msg):
        return self._message(self.headerRow+row,col,msg)

    def _message(self,row,col,msg):
        return "xlsFilename=%s,sheetName=%s,cell=%s,value=%s,msg=%s" % (self.xlsFilename,self.sheetName,self.cellname(row,col),self.sheet.cell(row+1,col+1).value,msg)

    def cellname(self,row,col):
        return "%s%s" % (get_column_letter(col+1),row+1)

    def value(self,row,col):
        val = self.rows[row][col]
        return val

    # def row(self,i):
    #     return self.rows[i]

    def getColType(self,col):
        if col in self.mergeCells:
            mergeCell = self.mergeCells[col]
            typ = mergeCell.type
            valueType = typ.valueType
            if valueType.typename == "map":
                # list<map<keytype,valuetype>>
                valueType = valueType.valueType
            elif valueType.isClass():
                # list<Class>
                if col in self.col2mapkey:
                    mapkey = self.col2mapkey[col]
                    for field in valueType.fields:
                        if field.name == mapkey:
                            valueType = field.type
            typ = valueType
        else:
            typ = self.col2type[col]
        return typ

    def getDefault(self,row,col):
        typ = self.getColType(col)
        typename = typ.typename
        constraint = self.col2constraint.get(col)
        if constraint and "default" in constraint:
            default = constraint["default"]
        else:
            default = self.defaults.get(typename)
        return default

    def getConvert(self,col):
        convert = self.getConstraint(col,"convert")
        if convert:
            return getattr(Convert,convert)

    def getConstraint(self,col,key):
        constraint = self.col2constraint[col]
        return constraint.get(key)

    def checkRef(self):
        if self.singleton:
            return
        for i,row in enumerate(self.rows):
            for j,value in enumerate(row):
                if value:
                    ref = self.getConstraint(j,"ref")
                    if ref:
                        refList = ref.split(".")
                        if len(refList) != 2:
                            raise Exception(self.message(i,j,"reference constraint expire format 'ref=refFilename.refColname',but got value='%s'" % ref))
                        refFilename,refColname = refList
                        refSheet = self.getSheet(refFilename)
                        if refSheet is None:
                            raise Exception(self.message(i,j,"reference's excel not exist,refFilename=%s,refColname=%s" % (refFilename,refColname)))
                        refSheetCol = refSheet.key2col.get(refColname)
                        if refSheetCol is None:
                            raise Exception(self.message(i,j,"reference's column not exist,refFilename=%s,refColname=%s" % (refFilename,refColname)))
                        ok = False
                        for refRow in refSheet.rows:
                            if value == refRow[refSheetCol]:
                                ok = True
                                break
                        if not ok:
                            raise Exception(self.message(i,j,"reference's value not exist,refFilename=%s,refColname=%s" % (refFilename,refColname)))

    def mergeFrom(self,fromSheet):
        for row in fromSheet.rows:
            self.dataRow = self.dataRow + 1
            self.rows.append(row)

    def splitSheets(self):
        if self.splitCol == -1:
            return None
        sheetDict = {}
        for i in range(0,self.dataRow):
            row = self.rows[i]
            val = row[self.splitCol]
            sheet = sheetDict.get(val)
            if sheet is None:
                sheet = Sheet(None,self.xlsFilename,self.sheetName)
                sheet.idCol = self.splitIdCol
                # 复制属性
                sheet.col2desc = self.col2desc
                sheet.col2comment = self.col2comment
                sheet.col2key = self.col2key
                sheet.col2type = self.col2type
                sheet.col2constraint = self.col2constraint
                sheet.col2tags = self.col2tags
                sheet.col2uniques = self.col2uniques
                sheet.key2col = self.key2col
                sheet.splitCol = self.splitCol
                sheet.maxRow = self.maxRow
                sheet.maxCol = self.maxCol
                sheet.mergeCells = self.mergeCells
                sheet.col2mapkey = self.col2mapkey

                sheet.filename += "_" + str(val)
                sheetDict[val] = sheet
            sheet.dataRow = sheet.dataRow + 1
            sheet.rows.append(row)
        return sheetDict.values()

    def getSheet(self,filename):
        global sheets
        return sheets.get(filename)