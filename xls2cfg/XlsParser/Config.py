#conding: utf-8

class Config(object):
    genMeta = False               # true=生成字段备注
    genMetaDetail = False         # true=生成详细字段备注(包含excel中的注释)
    genMetaHeader = False           # true=生成注解放到lua文件头
    pretty = True                   # true=美化输出
    tags = []                       # 导出的标签列表,[]=导出所有标签,否则仅导出列表内的标签
    defaults = {}                   # 类型默认值字典: 类型名 -> 默认值
    classNameFirstUpper = False     # true=导出的类名首字母大写
    fieldNameFirstUpper = False     # true=导出的字段名首字母大写
    namespace = "Cfg"               # 命名空间
    constraintSeperator = ';'       # 约束分隔符
    indent = "    ";                # 缩进符
    localize = False                # true=国际化文本导出成目标语言
    i18nDirectory = "../Output/I18N"
    i18nLanguage = "zh_CN"
    i18nExtension = ".po"
    i18nSeperator = "<:>"
    # 保留字（不可作字段名）；命令行/--config 未指定时使用此默认值
    keywords = dict.fromkeys((
        "int",
        "int8",
        "int16",
        "int32",
        "int64",
        "string",
        "bool",
        "float",
        "double",
        "default",
        "enum",
        "object",
        "function",
        "end",
        "break",
        "continue",
        "return",
        "for",
        "while",
        "do",
        "if",
        "else",
        "elseif",
        "elif",
    ), True)
    maxCol = 256                    # 最大列数

    @staticmethod
    def isNeedExportTags(tags):
        if tags:
            if "__ignore" in tags:
                return False
            if len(Config.tags) > 0:
                for tag in tags:
                    if tag in Config.tags:
                        return True
                return False
        return True

    @staticmethod
    def isKeyword(name):
        return Config.keywords.get(name)