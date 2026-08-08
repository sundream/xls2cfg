## Table of Contents

[toc]

## 构建

- 依赖项

  - 大于等于python3.10
  - pip install pyinstaller
  - pip install openpyxl
  - pip install Jinja2
- 仅对程序有用,当工具代码改变后,需要重新构建时执行
- 执行 build.bat

[Back to TOC](#table-of-contents)

## 用法

双击 gen.bat

[Back to TOC](#table-of-contents)

## 配置

示例见xls2cfg/config-client.json,xls2cfg/config-server.json

### --config

配置文件名

- input
  - 必填
  - 含义: 输入路径(excel 存放路径)
- output
  - 必填
  - 含义: 输出路径(生成配置路径)
- genHeader
  - 可选
  - 含义: 头部是否包含各字段描述信息
  - 格式: genHeader = true/false
- genHeaderDetail
  - 可选
  - 含义: 头部是否包含各字段备注信息
  - 格式: genHeaderDetail = true/false
- outputFormats
  - 可选
  - 含义: 输出格式列表,支持 lua/luacvs/go/csharp/py/json/binary
- defaults
  - 可选
  - 含义: 各类型默认值,没指定为该类型的默认值
  - 格式: defaults = {"类型名":默认值}
- tags
  - 可选
  - 含义: [导出的 tag 列,不填所有列都导出,比如可以自定义 c,s等 tag]
  - 格式: tags=[tag1,tag2,tag3,...]
- i18nDirectory
  - 可选
  - 含义: 国际化翻译目录
- i18nLanguage
  - 可选,如果不指定表示国际化文本不翻译也不导出,i18nDirectory+i18nExtension 必须同时指定
  - 含义: 国际化翻译语言
  - 命名规范
    language[_script]
    language 符合 ISO_639 语言编码,script 为语言变体,可选字段,比如:
    en=英文
    zh_Hans=简体中文
    zh_Hant=繁体中文
- i18nExtension
  - 可选
  - 含义: 国际化文件格式,目前支持 **.po**和**.txt** 和 **.lua**,默认为 **.po**
- i18nSeperator
  - 可选
  - 含义: 分割符,对于.txt 格式翻译文本有效,默认为<:>
- localize
  - 可选
  - 含义: true=对 i18nstring 类型字符串翻译为目标语言文本
- pretty
  - 可选
  - 含义: true=美化导出配置,false=每行配置导出一行,这样不美观,但输出配置文件占用尺寸小
- exclude
  - 可选
  - 含义: 排除的配表文件列表
  - 格式: [文件名 1,文件名 2,...]
- merge
  - 可选
  - 含义: 合并配表
  - 格式: {
    合并到的文件名 : [来源文件名 1,来源文件名 2]
    }

### --onlyExportChange

仅导出 svn 变动的 Excel

[Back to TOC](#table-of-contents)

## 表头行定义

- excel 表头前 5 行用于数据描述定义
- 每行含义
  - 1=备注行
  - 2=名字行
  - 3=类型行
  - 4=约束行
  - 5=标签行,比如脚本可以控制导出带特定标签的列

## 注释行

对行第一列元素前增加#即可

[Back to TOC](#table-of-contents)

## 数据类型

- bool: 取值范围 0/1
- int8
  - 取值范围: 8 位有符号 int
- int16
  - 取值范围: 16 位有符号 int
- int32
  - 取值范围: 32 位有符号 int
  - 别名: int
- int64
  - 取值范围: 64 位有符号 int
  - 别名: long
- uint8
  - 取值范围: 8 位无符号 int
- uint16
  - 取值范围: 16 位无符号 int
- uint32
  - 取值范围: 32 位无有符号 int
- uint64
  - 取值范围: 64 位无符号 int
- bigint
  - 大数
  - 举例: 3.14e3 => 3.14 \* 10^3 => 3140
- float
  - 单精度浮点数
- double
  - 双精度浮点数
- string
  - 字符串(不参与翻译)
- i18nstring
  - 国际化字符串(同 string,可用于标记该列文本会被国际化导出,如果配置 localize=true,导出会自动翻译为目标语言文本,如果没提供本地化文本,则保持原始文本串,你也可以打 not_localize 约束强制该列不导出成目标语言文本)
  - 别名: lang
- bit32
  - 32 位掩码类型,数据格式固定为: [0,1,2],最终结果会自动转换为 uint32,值为 2^0+2^1+2^2
  - 别名: bit
- bit64
  - 64 位掩码类型,数据格式固定为: [0,1,2],最终结果会自动转换为 uint64,值为 2^0+2^1+2^2
- json
  - json 类型
- list
  - 动态数组
  - 格式: list `<type>`,其中 type 为元素类型,支持嵌套
- map
  - 字典
  - 格式: map<keytype,valuetype>,其中 keytype 为键类型,valuetype 为值类型,支持嵌套

[Back to TOC](#table-of-contents)

## 约束

- 格式: k1=v1;k2=v2
- 描述: 所有约束都是可选的
- 约束类型
  - min
    - 可取的最小值
    - 格式: min=最小值
  - max
    - 可取的最大值
    - 格式: max=最大值
  - limit
    - 限制取值集合
    - 格式: limit=[值 1,值 2,值 3]
  - ref
    - 引用表的某列字段
    - 格式: ref=表名-字段名
  - unique
    - 唯一性约束,其中第一列(id 列)固定带 unique 约束,另外 unique 列自带 not_null 约束
  - convert
    - 转换
    - 格式: convert=转换函数名,转换函数可以在 Convert.py 文件中提供
  - default
    - 默认值,没指定时为对应类型的默认值
    - 格式:default=默认值
  - not_null
    - 此列无法为空
  - split
    - 根据此列值拆分表,此约束只允许出现在一列,拆分表名=表名\_$拆分列值
    - 格式: split=列 id(从 1 开始)/列名,比如 split=1 表示此列为拆分列,主键为第 1 列
  - .key
    - 含义: 指定 map 类型的 key 名,可以 map 类型字段拆分成多个单元格填
    - key 可以为任何有效标识符

[Back to TOC](#table-of-contents)

## 自定义类

可以提供**class**.xlsx 文件来定义类,类数据配置语法: [字段 1 数据,字段 2 数据,...],[]也可以用()代替,数据填充顺序需要和字段定义顺序保持一致。自定义的类字段类型不能为 json 类型

## 合并单元格

- 单例表不支持此功能

对于复杂 list/map 类型,我们可以把数据拆分成多个单元格填,该字段的描述/名字/类型合并单元格,单元格数量=数据列数,如此配置后,会将多个单元格数据合并后导出。目前合并单元格类型支持 list `<any>`/map<string,any>,对于 map 类型,我们可以在约束行填固定键名,格式:`.key`,我们也支持容器类型嵌套,比如 list<map<string,any>>,如果同时填了固定键名,那嵌套深度最大为 2

### 拆分填模式

| 模式 | 约束行 | 一列含义 | 例子 |
|------|--------|----------|------|
| P1（有 keys） | `.k1` `.k2` … | map/类的一个字段 | `map` / `list<map>` / `list<Class>` 按字段拆列 |
| P2（无 keys） | 全空 | list 的一个完整元素 | `list<int>` / `list<list<T>>` / `list<Class>` 每列一项 |

导表到 schema 时，拆分布局写入字段的 `layout`（不再把 `.key` 写入 `constraint`）。schema+json 还原 xlsx 时按 `layout` 重建合并单元格与多列数据。

`layout` 字段约定：

```json
{
  "mode": "split",
  "colSpan": 4,
  "keys": ["one", "two"],
  "elementSpan": 2
}
```

| 字段 | 含义 |
|------|------|
| `mode` | 固定为 `split`（缺省/无 layout = 单格填写） |
| `colSpan` | 该逻辑字段在 Excel 中占几列（合并宽度） |
| `keys` | P1：一个元素内的有序字段名；P2：`[]` |
| `elementSpan` | P1：一个 list 元素占几列（通常 = `keys.length`） |
| `elementKeys` | P2 且元素为 Class 时：单格内字段顺序，用于还原 `[v1,v2,...]` |

示例（`template@模板.xlsx`）：

- P1 `list1`：`list<map<string,int32>>`，`keys=["one","two"]`，`colSpan=4`，约束行 `.one|.two|.one|.two`
- P2 `list2`：`list<list<int32>>`，`keys=[]`，`colSpan=2`，每列一个内层 list
- P2 `list4`：`list<Rectangle>`，`keys=[]`，带 `elementKeys`，每列一个 `[length,width]`

[Back to TOC](#table-of-contents)

## 注释

- 在行头增加 `#`能注释本行
- 在列头增加 `#`能注释本列
- 在列头填 `##end`表示本列及之后的列都不被导出
- 在首列头填 `##key`表示此 excel 为单例表,也就是以列模式来填表,此时首行为表头,格式固定为: ##key | type | value | tags | desc

[Back to TOC](#table-of-contents)

## 列表简化配置

列表是以逗号 `,`作为分隔符,工具允许列表省略掉 `最外层[]`

## 示例

- 导出配置见: config.json
- excel 示例配置
  - 多行表: Excel/template@模板.xlsx
    ![image](images/template.png)
  - 单例表: Excel/var@变量.xlsx
    ![image](images/const.png)
  - 单个excel根据sheet名导出多份数据，以下表会导出entity_hero和entity_monster数据
    ![image](images/entity.png)

[Back to TOC](#table-of-contents)

## schema 输出与 Excel 导入/导出

面向 MapEditor 等工具的 **xlsx ↔ schema/json** 往返。正式导表仍用 `gen.bat` / `--config`；下列命令用于编辑器侧导入导出。

### schema 顶层字段

| 字段 | 含义 |
|------|------|
| `kind` | `0`=自定义类，`1`=单例表（列模式），`2`=普通二维表 |
| `name` | 逻辑表名 / 输出文件名（不含扩展名）。`sheetName=="data"` 时为工作簿主名，否则为 `{工作簿主名}_{sheetName}` |
| `displayName` | **仅 sheet 显示名**（见下方命名）；不含工作簿 `@` 后中文 |
| `className` | 代码生成用类名 |
| `workbook` | 完整 xlsx 文件名，如 `entity@场景实体.xlsx`、`__class__.xlsx` |
| `sheetName` | sheet 逻辑名（`Hero` / `data`） |
| `sheetIndex` | sheet 在工作簿中的顺序（导出时按此重建多 sheet） |
| `fields` | 字段列表（见下） |

普通表示例：

```json
{
  "kind": 2,
  "name": "entity_Hero",
  "displayName": "英雄",
  "className": "Entity_Hero",
  "workbook": "entity@场景实体.xlsx",
  "sheetName": "Hero",
  "sheetIndex": 0,
  "fields": []
}
```

自定义类：`gen` / `--import-xlsx` 都会把 `__class__.xlsx` 里的类型写成独立 schema（如 `Rectangle.json`），`kind=0`，并带同样的 workbook 元数据（`__class__.xlsx` 本身不作为数据表导出）：

```json
{
  "kind": 0,
  "name": "Rectangle",
  "displayName": "矩形",
  "className": "Rectangle",
  "workbook": "__class__.xlsx",
  "sheetName": "data",
  "sheetIndex": 0,
  "fields": []
}
```

### 命名约定

- 工作簿文件：`{name}@{中文}.xlsx` 或 `{name}.xlsx`
- Sheet 标题（可选）：`{sheetName}@{displayName}`；无显示名时只用 `sheetName`
- schema / json 文件名 = `name`（类与表统一）

### 字段与 layout

- `type` 保留 Excel 原文（填 `int` 则导出 `int`）
- `displayName` / `remarks` 保留换行；代码 meta（genMeta）导出时再压成单行
- `layout`：
  - 合并拆分：`mode=split`、`colSpan`、`keys`、`elementSpan` / `elementKeys`（见上文）；`.key` 只在 `layout.keys`
  - 整数字面量进制：`intBase` 为 `16`（`0x`）或 `2`（`0b`），字段级，用于还原 Excel 文本；仅针对 int*/uint*（不含 bigint），由首个数据行检测

### CLI

```text
# 单表：schema+json → xlsx
python xls2cfg.py --from-schema=../Output/Client/schema/const.json --from-json=../Output/Client/json/const.json --out=../Excel/const@全局常量.xlsx

# 单表：schema+binary → xlsx（需 --tags 与导表 tags 一致）
python xls2cfg.py --from-schema=../Output/Client/schema/const.json --from-binary=../Output/Client/binary/const.bytes --tags=c --out=../Excel/const@全局常量.xlsx

# 批量：按 workbook + sheetIndex 合并多 sheet；kind=0 写出 __class__.xlsx
python xls2cfg.py --from-dir=../Output/Client --export-xlsx=../ExcelOut

# xlsx → schema + json（全列，不受 tags 过滤）
python xls2cfg.py --import-xlsx=../Excel/entity@场景实体.xlsx --schema-dir=schema --json-dir=json
python xls2cfg.py --import-xlsx=../Excel/__class__.xlsx --schema-dir=schema --json-dir=json
```

- 批量 `--from-dir` 优先 `json/`，否则回退 `binary/`
- import 会加载同目录 `__class__.xlsx`；引用到的类写成 `kind=0` 的 schema。直接 import `__class__.xlsx` 时只写各类 schema，不写数据表

### 支持与限制（往返）

**支持**

- 多 sheet 工作簿：按 `workbook` / `sheetIndex` / `sheetName[@displayName]` 还原
- 合并单元格拆分填（P1/P2）及 `list<Class>` 单格编码（依赖类 schema）
- 字段 `displayName`、`remarks`（批注）、`constraint`、`tags`、`intBase`
- 自定义类 `__class__.xlsx` ↔ `kind=0` schema

**不保证 / 不还原**

- 单元格样式、列宽以外的版式、公式（按计算后的值导入）
- 注释行/列（`#` / `##end` 之外的备注列）往返
- `convert` / `ref` 等运行时约束的 Excel 侧回写语义
- 默认值在 Excel 中表现为空单元格的精确还原
- i18n `localize` 后的译文再导回原文
- **带 tags 过滤的 Client/Server 产物**：编辑器往返请用 **全列** schema/json；不要用 tag 裁剪后的表去做 Excel 还原

[Back to TOC](#table-of-contents)

## Liscense

MIT
