#coding:utf-8
#@author sundream
#@date 2025-09-10

import json
import ast
from XlsParser.Type import Type
from XlsParser.I18NExport import setI18NText,getLocalizeText
from openpyxl.utils import get_column_letter

xlsFilename = None
row = None
col = None

min_int8 = -128
max_int8 =  127
min_int16 = -32768
max_int16 =  32767
min_int32 = -2147483648
max_int32 =  2147483647
min_int64 = -9223372036854775808
max_int64 =  9223372036854775807

min_uint8 = 0
max_uint8 = 255
min_uint16 = 0
max_uint16 = 65535
min_uint32 = 0
max_uint32 = 4294967295
min_uint64 = 0
max_uint64 = 18446744073709551615

def isInt8(value):
    return min_int8 <= value and value <= max_int8

def isInt16(value):
    return min_int16 <= value and value <= max_int16

def isInt32(value):
    return min_int32 <= value and value <= max_int32

def isInt64(value):
    return min_int64 <= value and value <= max_int64

def isUInt8(value):
    return min_uint8 <= value and value <= max_uint8

def isUInt16(value):
    return min_uint16 <= value and value <= max_uint16

def isUInt32(value):
    return min_uint32 <= value and value <= max_uint32

def isUInt64(value):
    return min_uint64 <= value and value <= max_uint64

def toBool(value):
    result,ok = toInt(value)
    if not ok:
        return value,False
    if result == 0 or result == 1:
        return bool(result),True
    return value,False

def toInt(value):
    if type(value) != int:
        try:
            result = int(value)
            return result,True
        except Exception as e:
            return value,False
    return value,True

def toBigInt(value):
    if type(value) != str:
        value = str(value)
    pos = value.find('e')
    if pos > -1:
        a,b = value[0:pos],int(value[pos+1:])
        dotPos = a.find('.')
        if dotPos > -1:
            a1,a2 = a[0:dotPos],a[dotPos+1:]
            assert(b >= len(a2))
            b = b - len(a2)
            a = a1 + a2
        if b > 0:
            result = a + '0' * b
        else:
            result = a
    else:
        if not value.isdigit():
            return value,False
        result = value
    return result,True

def toFloat(value):
    if type(value) == int:
        return value,True
    if type(value) != float:
        try:
            result = float(value)
            return result,True
        except Exception as e:
            return value,False
    return value,True


escapeChars = {'\\n':'\n','\\r':'\r','\\t':'\t','\\"':'\"',"\\'":"\'"}

def toString(value):
    if type(value) == str:
        for k,v in escapeChars.items():
            value = value.replace(k,v)
    else:
        value = str(value)
    return value,True

def escapeString(value):
    for k,v in escapeChars.items():
        value = value.replace(v,k)
    return value

def toMask(value):
    if value[0] != '[' or value[len(value)-1] != ']':
        return value,False
    try:
        result = 0
        lst = ast.literal_eval(value)
        for power in lst:
            if type(power) != int:
                return value,False
            if power == -1:
                return -1,True
            result += pow(2,power)
        return result,True
    except Exception as e:
        return value,False

def toJson(value):
    try:
        if type(value) == str:
            value = json.loads(value)
        return value,True
    except Exception as e:
        return value,False

def toList(value,typ,options):
    try:
        if type(value) == str:
            length = len(value)
            if value[0] != '[' and value[length-1] != ']':
                value = '[' + value + ']'
            value = ast.literal_eval(value)
        if type(value) != list:
            return value,False
        result = []
        for i,v in enumerate(value):
            ok,v = toValue(v,typ.valueType,options)
            if not ok:
                return value,False
            result.append(v)
        value = result
        return value,True
    except Exception as e:
        return value,False

def toMap(value,typ,options):
    try:
        if type(value) == str:
            value = ast.literal_eval(value)
        if type(value) != dict:
            return value,False
        result = {}
        for k,v in value.items():
            ok,v = toValue(v,typ.valueType,options)
            if not ok:
                return value,False
            result[k] = v
        value = result
        return value,True
    except Exception as e:
        return value,False

def toClass(value,typ,options):
    try:
        if type(value) == str:
            value = ast.literal_eval(value)
        if type(value) != tuple and type(value) != list:
            return value,False
        result = {}
        for i,v in enumerate(value):
            field = typ.fields[i]
            fieldType = field.type
            ok,v = toValue(v,fieldType,options)
            if not ok:
                return value,False
            result[field.name] = v
        value = result
        return value,True
    except Exception as e:
        return value,False

def toValue(value,typ,options=None):
    global xlsFilename,row,col
    localize = False
    if options:
        xlsFilename = options["xlsFilename"]
        row = options["row"]
        col = options["col"]
        localize = options["localize"]

    if not typ:
        return False,"type is None"
    typename = typ.typename
    pythonType = type(value)
    if value is None:
        pass
    elif typename == "bool":
        value,ok = toBool(value)
        if not ok:
            return False,"bool expect 0/1"
    elif typename == "int8":
        value,ok = toInt(value)
        if not ok or not isInt8(value):
            return False,"expect '%s',but got python type '%s',value=%s" % (typename,pythonType,value)
    elif typename == "int16":
        value,ok = toInt(value)
        if not ok or not isInt16(value):
            return False,"expect '%s',but got python type '%s',value=%s" % (typename,pythonType,value)
    elif typename == "int32":
        value,ok = toInt(value)
        if not ok or not isInt32(value):
            return False,"expect '%s',but got python type '%s',value=%s" % (typename,pythonType,value)
    elif typename == "int64":
        value,ok = toInt(value)
        if not ok or not isInt64(value):
            return False,"expect '%s',but got python type '%s',value=%s" % (typename,pythonType,value)
    elif typename == "uint8":
        value,ok = toInt(value)
        if not ok or not isInt8(value):
            return False,"expect '%s',but got python type '%s',value=%s" % (typename,pythonType,value)
    elif typename == "uint16":
        value,ok = toInt(value)
        if not ok or not isInt16(value):
            return False,"expect '%s',but got python type '%s',value=%s" % (typename,pythonType,value)
    elif typename == "uint32":
        value,ok = toInt(value)
        if not ok or not isInt32(value):
            return False,"expect '%s',but got python type '%s',value=%s" % (typename,pythonType,value)
    elif typename == "uint64":
        value,ok = toInt(value)
        if not ok or not isInt64(value):
            return False,"expect '%s',but got python type '%s',value=%s" % (typename,pythonType,value)
    elif typename == "bigint":
        value,ok = toBigInt(value)
        if not ok:
            return False,"expect '%s',but got python type '%s',value=%s" % (typename,pythonType,value)
    elif typename == "float":
        value,ok = toFloat(value)
        if not ok:
            return False,"expect '%s',but got python type '%s',value=%s" % (typename,pythonType,value)
    elif typename == "double":
        value,ok = toFloat(value)
        if not ok:
            return False,"expect '%s',but got python type '%s',value=%s" % (typename,pythonType,value)
    elif typename == "string" or typename == "i18nstring":
        value,ok = toString(value)
        if not ok:
            return False,"expect '%s',but got python type '%s',value=%s" % (typename,pythonType,value)
        if typename == "i18nstring":
            setI18NText(value,xlsFilename,"%s%s" % (get_column_letter(col+1),row+1))
            if localize:
                value = getLocalizeText(value) or value
    elif typename == "bit32":
        value,ok = toMask(value)
        if not ok or not isInt32(value):
            return False,"not a valid bit32 format"
    elif typename == "bit64":
        value,ok = toMask(value)
        if not ok or not isInt64(value):
            return False,"not a valid bit64 format"
    elif typename == "json":
        value,ok = toJson(value)
        if not ok:
            return False,"not a valid json format"
    elif typename == "list":
        value,ok = toList(value,typ,options)
        if not ok:
            return False,"expect %s,but got python type '%s',value='%s'" % (typ.fullTypename,pythonType,value)
    elif typename == "map":
        value,ok = toMap(value,typ,options)
        if not ok:
            return False,"expect %s,but got python type '%s',value='%s'" % (typ.fullTypename,pythonType,value)
    elif typ.isClass():
        value,ok = toClass(value,typ,options)
        if not ok:
            return False,"expect %s,but got python type '%s',value='%s'" % (typ.fullTypename,pythonType,value)
    else:
        return False,"invalid type '%s'" % (typename)
    return True,value