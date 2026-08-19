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
    fieldReadonly = True            # true=C# 字段加 readonly（仅 csharp）
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
    # import_xlsx 生成 __class__/__enum__: 0=json+xlsx, 1=json only, 2=xlsx only
    gen_class_xlsx = 0

    @staticmethod
    def gen_class_xlsx_mode():
        try:
            mode = int(Config.gen_class_xlsx)
        except (TypeError, ValueError):
            return 0
        if mode not in (0, 1, 2):
            return 0
        return mode

    @staticmethod
    def gen_class_json_file():
        return Config.gen_class_xlsx_mode() != 2

    @staticmethod
    def gen_class_excel_file():
        return Config.gen_class_xlsx_mode() != 1

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