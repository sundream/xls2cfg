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

    ENUM_REALTYPES = (
        "uint8", "int8", "uint16", "int16",
        "uint32", "int32", "int64", "uint64",
    )

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

    #@brief 判断是否为有效枚举名
    @staticmethod
    def isEnumName(enumName):
        typ = Type.get(enumName)
        if not typ:
            return False
        return typ.isEnum()

    #@brief 创建类
    #@param className string 类名
    #@param fields list<field dict> 字段列表
    #@return Type 类
    @staticmethod
    def unregister(typeName):
        """Remove a registered type so it can be redefined (json override xlsx)."""
        Type.types.pop(typeName, None)

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
                    group=field.get("group"),
                )
        return typ

    @staticmethod
    def parse_enum_int(raw):
        """Parse enum int literal: decimal / 0x hex / 0b binary. Returns (ok, int_or_err)."""
        from XlsParser.CheckType import toInt
        if raw is None or raw == "":
            return False, "empty"
        value, ok = toInt(raw)
        if not ok:
            return False, "invalid int '%s'" % raw
        return True, int(value)

    #@brief 创建枚举
    #@param enumName string 枚举名
    #@param enumType string 底层整数类型
    #@param items list 枚举项 {name,value,comment,tags}
    #@param comment string 备注
    #@param flags bool 是否可组合（等价 C# [Flags]）
    #@return Type
    @staticmethod
    def createEnum(enumName, enumType=None, items=None, comment=None, flags=False):
        enumType = (enumType or "int32").strip() or "int32"
        if enumType not in Type.ENUM_REALTYPES:
            raise Exception("invalid enum enumType '%s' for %s (expect %s)" % (
                enumType, enumName, ",".join(Type.ENUM_REALTYPES)))
        Type.types[enumName] = True
        typ = Type.create(enumName)
        typ._isEnum = True
        typ.enumType = enumType
        typ.flags = bool(flags)
        typ.comment = comment
        typ.enumFields = []
        typ.enumByName = {}
        typ.enumByValue = set()
        next_value = 1 if typ.flags else 0
        for item in items or []:
            name = item.get("name")
            if not name:
                continue
            raw = item.get("value")
            if raw is None or raw == "":
                value = next_value
            else:
                ok, value = Type.parse_enum_int(raw)
                if not ok:
                    raise Exception("invalid enum value '%s' for %s.%s" % (raw, enumName, name))
            if name in typ.enumByName:
                raise Exception("repeat enum item '%s' in %s" % (name, enumName))
            entry = {
                "name": name,
                "value": value,
                "comment": item.get("comment") or "",
                "tags": item.get("tags"),
            }
            typ.enumFields.append(entry)
            typ.enumByName[name] = value
            typ.enumByValue.add(value)
            if typ.flags:
                next_value = (value << 1) if value > 0 else 1
            else:
                next_value = value + 1
        return typ

    def __init__(self,fullTypename):
        self.fullTypename = None                    # 完整类型名
        self.typename = None                        # 主类型名
        self.keyType = None                         # 键类型(map类型有用)
        self.valueType = None                       # 值类型(list/map类型有用)
        self.fields = None                          # 类的域定义列表
        self.idFieldIdx = -1                        # id域索引
        self.comment = None                         # 类型备注 / 表 displayName
        self._isEnum = False                        # true=枚举类型
        self.enumType = None                        # 枚举底层整数类型名
        self.flags = False                          # true=[Flags] 位掩码枚举
        self.enumFields = None                       # 枚举项列表
        self.enumByName = None                      # 枚举名 -> 值
        self.enumByValue = None                     # 合法整数值集合
        self.__fromString(fullTypename)
        self.singleton = False                      # true=单例类型

    @staticmethod
    def __convTypename(fullTypename):
        pos = fullTypename.rfind("[]")
        if pos > 0:
            # 兼容数组格式: type[]
            return "list<%s>" % Type.__convTypename(fullTypename[:pos])
        return fullTypename

    @staticmethod
    def topLevelComma(s):
        """Index of first comma not inside <...>; -1 if none."""
        depth = 0
        for i, ch in enumerate(s or ""):
            if ch == "<":
                depth += 1
            elif ch == ">":
                depth -= 1
            elif ch == "," and depth == 0:
                return i
        return -1

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
            commaPos = Type.topLevelComma(kvtype)
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

    def defineField(self,fullTypename,name,comment=None,tags=None,remarks=None,group=None):
        if not self.fields:
            self.fields = []
        tags, parsed_group = parse_tags_cell(tags)
        if group is None:
            group = parsed_group
        field = Field(
            fullTypename,
            name,
            comment=comment,
            tags=tags,
            remarks=remarks,
            group=group,
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
        if self.isEnum():
            return False
        if not self.fields:
            return False
        return True

    def isEnum(self):
        return bool(getattr(self, "_isEnum", False))

    def underlyingType(self):
        """Type used for codegen / binary IO (enum → enumType)."""
        if self.isEnum():
            return Type.getOrCreate(self.enumType or "int32")
        return self

    def resolveEnumValue(self, value):
        """Map enum field name or allowed int to integer. Returns (ok, value_or_err).

        Flags enums also accept bitmask ints (OR of defined bits) and combined
        names separated by '|' (e.g. FlagA|FlagB or FlagA | FlagC | FlagD).
        """
        if value is None or value == "":
            return True, None
        if isinstance(value, bool):
            return False, "enum does not accept bool"

        def _flags_mask():
            mask = 0
            for v in (self.enumByValue or set()):
                mask |= int(v)
            return mask

        def _accept_int(n):
            if getattr(self, "flags", False):
                allowed = _flags_mask()
                unknown = int(n) & ~allowed
                if unknown != 0:
                    return False, "invalid flags bits %s in %s (unknown %s, allowed mask %s)" % (
                        n, self.typename, unknown, allowed)
                return True, int(n)
            allowed = self.enumByValue or set()
            if n not in allowed:
                return False, "invalid enum value %s in %s (expect one of %s)" % (
                    n, self.typename, sorted(allowed))
            return True, n

        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return _accept_int(int(value))
        s = str(value).strip()
        if s in (self.enumByName or {}):
            return True, self.enumByName[s]
        if getattr(self, "flags", False) and "|" in s:
            parts = [p.strip() for p in s.split("|") if p.strip()]
            if not parts:
                return True, 0
            combined = 0
            for p in parts:
                if p not in (self.enumByName or {}):
                    return False, "unknown enum field '%s' in flags %s" % (p, self.typename)
                combined |= int(self.enumByName[p])
            return _accept_int(combined)
        try:
            ok, n = Type.parse_enum_int(s)
            if not ok:
                raise Exception(n)
        except Exception:
            hint = "name, A|B, or int/0x/0b" if getattr(self, "flags", False) else "name or int/0x/0b"
            return False, "unknown enum field '%s' in %s (expect %s in %s)" % (
                s, self.typename, hint, sorted(self.enumByValue or []))
        return _accept_int(n)

    def to_schema(self, name=None, kind=None, class_name=None):
        """Build Global/table schema dict. Field.comment → displayName, Field.remarks → remarks."""
        name = name or self.typename
        type_name = class_name or self.typename
        if self.isEnum():
            if kind is None:
                kind = 0
            items = []
            for it in self.enumFields or []:
                entry = {
                    "name": it["name"],
                    "value": it["value"],
                }
                if it.get("comment"):
                    entry["displayName"] = it["comment"]
                tags = Field.format_tags(it.get("tags"))
                if tags:
                    entry["tags"] = tags
                items.append(entry)
            schema = {
                "name": name,
                "kind": kind,
                "typename": type_name,
                "enumType": self.enumType or "int32",
                "fields": items,
            }
            if getattr(self, "flags", False):
                schema["flags"] = True
            if self.comment:
                schema["displayName"] = self.comment
            return schema
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
            if f.group:
                entry["group"] = f.group
            fields.append(entry)
        schema = {
            "name": name,
            "kind": kind,
            "typename": type_name,
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

def parse_tags_cell(value):
    """Split Excel tags cell / list<string> into (tags_or_None, group_or_None).

    `group=name` is editor metadata, not an export tag.
    """
    if value is None or value == "":
        return None, None
    if isinstance(value, (list, tuple)):
        tokens = [str(t).strip() for t in value if t is not None and str(t).strip()]
    else:
        tokens = [t.strip() for t in str(value).split(",") if t.strip()]
    tags = []
    group = None
    for t in tokens:
        if t.startswith("group="):
            name = t[6:].strip()
            if not name:
                raise Exception("invalid tags group, expire group=name")
            if group is not None:
                raise Exception("multiple group= in tags")
            group = name
        else:
            tags.append(t)
    return (tags if tags else None), group


def format_tags_cell(tags, group=None):
    """Excel tags row: real tags plus group=name (export/import round-trip)."""
    if isinstance(tags, str):
        parts = [t.strip() for t in tags.split(",") if t.strip() and not t.strip().startswith("group=")]
    else:
        parts = [t for t in (tags or []) if t and t != "__ignore" and not str(t).startswith("group=")]
    if group:
        parts.append("group=%s" % group)
    return ",".join(parts)


class Field(object):
    @staticmethod
    def format_tags(tags):
        if not tags:
            return ""
        cleaned = [t for t in tags if t and t != "__ignore" and not str(t).startswith("group=")]
        return ",".join(cleaned)

    def __init__(self,fullTypename,name=None,comment=None,tags=None,remarks=None,group=None):
        self.type = Type.getOrCreate(fullTypename)
        self.name = name                            # 字段名
        self.comment = comment or ""                # 显示名（对应 schema displayName）
        self.remarks = remarks or ""                # 详细注释（对应 schema remarks）
        self.tags = tags                            # 字段标签列表（不含 group=）
        self.group = group                          # 编辑器字段分组
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
