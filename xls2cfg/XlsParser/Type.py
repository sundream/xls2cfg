#coding:utf-8
#@author sundream
#@date 2025-09-10

class Type(object):
    types = {}              # 所有类型字典: 类型名 -> Type
    # 类型别名
    typeAlias = {
        "int" : "int32",
        "long" : "int64",
        "lang" : "i18nstring",
        "bit" : "bit32",
        "boolean" : "bool",
        "integer" : "int32",
        "table" : "map",
    }
    basicTypes = {
        "bool" : False,
        "int8" : 0,
        "int16" : 0,
        "int32" : 0,
        "int64" : 0,
        "uint8" : 0,
        "uint16" : 0,
        "uint32" : 0,
        "uint64" : 0,
        "bigint" : "0",
        "float" : 0.0,
        "double" : 0.0,
        "string" : "",
        "i18nstring" : "",
        "bit32" : 0,
        "bit64" : 0,
    }

    containerTypes = {
        "json" : [],
        "list" : [],
        "map" : {},
    }

    #@brief 获取/创建类型
    #@param fullTypename string 类型完整名
    #@return Type 类型
    @staticmethod
    def getOrCreate(fullTypename):
        typ = Type.get(fullTypename)
        if not typ:
            typ = Type.create(fullTypename)
        return typ

    #@brief 创建类型
    #@param fullTypename string 类型完整名
    #@return Type 类型
    @staticmethod
    def create(fullTypename):
        if type(Type.types.get(fullTypename)) == Type:
            raise Exception("repeat typename: %s" % (fullTypename))
        typ = Type(fullTypename)
        Type.types[fullTypename] = typ
        return typ

    #@brief 获取类型
    #@param fullTypename string 类型完整名
    #@return Type 类型
    @staticmethod
    def get(fullTypename):
        return Type.types.get(fullTypename)

    #@brief 判断是否为有效类名
    #@param className string 类型完整名
    #@return bool true=是有效类名
    @staticmethod
    def isClassName(className):
        typ = Type.get(className)
        if not typ:
            return False
        return typ.isClass()

    #@brief 创建类
    #@param className string 类名
    #@param fields list<field dict> 字段列表
    #@return Type 类
    @staticmethod
    def createClass(className,fields=None):
        Type.types[className] = True
        typ = Type.create(className)
        if fields:
            for field in fields:
                typ.defineField(
                    field["type"],
                    field["name"],
                    comment=field.get("comment"),
                    tags=field.get("tags"),
                    remarks=field.get("remarks"),
                )
        return typ

    def __init__(self,fullTypename):
        self.fullTypename = None                    # 完整类型名
        self.typename = None                        # 主类型名
        self.keyType = None                         # 键类型(map类型有用)
        self.valueType = None                       # 值类型(list/map类型有用)
        self.fields = None                          # 类的域定义列表
        self.idFieldIdx = -1                        # id域索引
        self.comment = None                         # 类型备注 / 表 displayName
        self.__fromString(fullTypename)
        self.singleton = False                      # true=单例类型

    @staticmethod
    def __convTypename(fullTypename):
        pos = fullTypename.rfind("[]")
        if pos > 0:
            # 兼容数组格式: type[]
            return "list<%s>" % Type.__convTypename(fullTypename[:pos])
        return fullTypename

    def __fromString(self,fullTypename):
        keyType = None
        valueType = None
        fullTypename = Type.__convTypename(fullTypename)
        pos = fullTypename.find("<")
        if pos > 0:
            typename = fullTypename[0:pos]
            kvtype = fullTypename[pos+1:len(fullTypename)-1]
        else:
            typename = fullTypename
        alias = Type.typeAlias.get(typename)
        if alias:
            typename = alias
        if typename == "json":
            pass
        elif typename == "list":
            vtype = kvtype
            valueType = Type.getOrCreate(vtype)
        elif typename == "map":
            commaPos = kvtype.find(",")
            if commaPos < 0:
                raise Exception("invalid type: %s" % fullTypename)
            ktype = kvtype[0:commaPos]
            vtype = kvtype[commaPos+1:]
            keyType = Type.getOrCreate(ktype)
            valueType = Type.getOrCreate(vtype)
        elif typename in Type.basicTypes:
            pass
        else:
            if typename not in Type.types:
                raise Exception("invalid type: %s" % fullTypename)
        self.typename = typename
        self.keyType = keyType
        self.valueType = valueType
        self.fullTypename = fullTypename

    def defineField(self,fullTypename,name,comment=None,tags=None,remarks=None):
        if not self.fields:
            self.fields = []
        field = Field(
            fullTypename,
            name,
            comment=comment,
            tags=tags,
            remarks=remarks,
        )
        field.index = len(self.fields)
        self.fields.append(field)
        return field.index

    def setIdField(self,idFieldIdx):
        self.idFieldIdx = idFieldIdx

    def getIdField(self):
        if self.idFieldIdx == -1:
            return None
        return self.fields[self.idFieldIdx]

    def isClass(self):
        if not self.fields:
            return False
        return True

    def to_schema(self, name=None, kind=None, class_name=None):
        """Build Global/table schema dict. Field.comment → displayName, Field.remarks → remarks."""
        name = name or self.typename
        class_name = class_name or self.typename
        if kind is None:
            kind = 1 if self.singleton else 2
        fields = []
        for f in self.fields or []:
            entry = {
                "name": f.name,
                "type": f.type.fullTypename if f.type else "int32",
            }
            if f.comment:
                entry["displayName"] = f.comment
            if f.remarks:
                entry["remarks"] = f.remarks
            tags = Field.format_tags(f.tags)
            if tags:
                entry["tags"] = tags
            fields.append(entry)
        schema = {
            "name": name,
            "kind": kind,
            "className": class_name,
        }
        if self.comment:
            schema["displayName"] = self.comment
        schema["fields"] = fields
        return schema

    def __str__(self):
        return self.fullTypename

    def __eq__(self,other):
        if self.fullTypename == other.fullTypename:
            return True
        return False

class Field(object):
    @staticmethod
    def format_tags(tags):
        if not tags:
            return ""
        cleaned = [t for t in tags if t and t != "__ignore"]
        return ",".join(cleaned)

    def __init__(self,fullTypename,name=None,comment=None,tags=None,remarks=None):
        self.type = Type.getOrCreate(fullTypename)
        self.name = name                            # 字段名
        self.comment = comment or ""                # 显示名（对应 schema displayName）
        self.remarks = remarks or ""                # 详细注释（对应 schema remarks）
        self.tags = tags                            # 字段标签列表
        self.index = -1                             # 字段索引

    def codegen_comment(self):
        """Legacy codegen text: comment, or comment(remarks) when genMetaDetail.

        Newlines are flattened for genMeta; schema keeps original multiline text.
        """
        from XlsParser.Config import Config
        c = (self.comment or "").replace("\r\n", "\n").replace("\r", "\n").replace("\n", " ")
        r = (self.remarks or "").replace("\r\n", "\n").replace("\r", "\n").replace("\n", " ")
        if Config.genMetaDetail and c and r:
            return "%s(%s)" % (c, r)
        return c or r
