# 系统域变更分析场景用例（sys_domain_change_usecase）

从 MySQL `solution_knowledge` 库抽取、清洗、关联 `feature_sub_system_gaia` 等 5 张源表的数据，生成一张 **单表** `sys_domain_change_usecase`，同时输出 Excel 与回写 MySQL。

## 快速开始

```bash
pip install -r requirements.txt
python run.py
```

运行时长 ~3 分钟（7200 行），输出：

- `output/sys_domain_change_usecase.xlsx`：单 Sheet 10 列
- MySQL 单表 `sys_domain_change_usecase`（7200 行，PK = `rdc_number`）
- `output/run.log`：完整运行日志（含 DEBUG 级）

## 数据源

| 表 | 用途 |
|---|---|
| **feature_sub_system_gaia** | **驱动表**，按 `rdc_number` 遍历 |
| root_feature_change_analysis_sub | 特性域变更分析（5 字段） |
| root_in_sub_system_process_sub | 波及组件（含 subSystem 分组） |
| root_component_main | 波及模块（sender / receiver / business_flow 等） |
| root_system_change_analysis_sub | 波及的变更点（含 sub_system_name） |

gaia 表无 `rdc_id` 字段，跨表查询用 `CONCAT('[', rdc_number, ']')`。

## 输出字段

单表 10 列：

| # | 列名 | 来源 | 处理 |
|---|---|---|---|
| 1 | `rdc_number` | gaia.rdc_number | 主键 |
| 2 | `title`（方案） | gaia.title | 清洗：去末尾 `-盖亚创建` |
| 3 | `feature_change_analysis`（特性域变更分析结果） | root_feature_change_analysis_sub | **JSON 数组**，5 字段 × N 行 |
| 4 | `description`（需求描述） | gaia.description | 直接 |
| 5 | `algorithm`（算法描述） | gaia.algorithm | 直接 |
| 6 | `implementation`（实现思路） | gaia.implementation | 直接 |
| 7 | `sub_systems`（波及子系统） | gaia.sub_system JSON 字段 | **JSON 数组**，去重：`["SPA","PHY"]` |
| 8 | `affected_components`（波及组件） | root_in_sub_system_process_sub | **JSON 大对象**：按 subSystem 分组 |
| 9 | `affected_modules`（波及模块） | root_component_main | **JSON 数组**，6 字段 × N 行 |
| 10 | `change_points`（波及的变更点） | root_system_change_analysis_sub | **JSON 数组**，2 字段 × N 行 |

### 列类型与存储

- **所有列用 MEDIUMTEXT**（16 MB 上限）—— TEXT 的 64 KB 不够（实测有 78 KB 的 affected_components）。
- DB 存紧凑 JSON（无空格），Excel 渲染时自动 `indent=2` 多行展示。

### JSON 列形态示意

`affected_components` 例：
```json
[
  {
    "subSystem": "SPA",
    "波及组件": [
      {"business_number": "1", "source_system": "HUC",  "business_flow": "Msg1Ta", "aim_system": "MCC", "change_type": "新增", "change_describe": "..."},
      {"business_number": "2", "source_system": "MCC",  "business_flow": "小区NI", "aim_system": "UPA", "change_type": "修改", "change_describe": "..."}
    ]
  },
  {"subSystem": "PHY", "波及组件": [...]}
]
```

`affected_modules` 例：
```json
[
  {"sender":"RACH","receiver":"UAC对外接口管理","business_flow":"Msg1Ta","output_strategy":"","change_type":"新增","remarks":"转发Msg1Ta"},
  {"sender":"ULRKC","receiver":"UAC对外接口管理","business_flow":"小区NI","output_strategy":"","change_type":"修改","remarks":"..."}
]
```

## 项目结构

```
.
├── config/
│   ├── db_config.py                # 真实连接参数（已 gitignore）
│   └── db_config.example.py        # 模板（提交到 git）
├── src/
│   ├── main.py                     # 流水线编排 + 进度日志
│   ├── db/
│   │   ├── connector.py            # pymysql + DBUtils 连接池
│   │   └── queries.py              # 6 个 SQL + DDL + JSON 工具函数
│   ├── extractors/
│   │   └── usecase_extractor.py    # 单一抽取器，处理一个 rdc_number → 10 字段
│   ├── models/
│   │   └── sys_domain_change_usecase.py  # 单 dataclass
│   ├── exporters/
│   │   ├── excel_exporter.py       # 单 Sheet + JSON 缩进展示
│   │   └── db_exporter.py          # 建表 / TEXT→MEDIUMTEXT 迁移 / UPSERT
│   └── utils/
│       ├── text_clean.py           # clean_solution_title + sanitize_for_excel
│       └── logger.py               # loguru 配置
├── tests/
│   └── test_new.py                 # 15 个单元测试
├── run.py                          # 启动入口
├── requirements.txt
└── README.md
```

## 运行流程

```
1. DBExporter.ensure_tables()   ─ 建表 + TEXT→MEDIUMTEXT 迁移（如需要）
2. SELECT FROM feature_sub_system_gaia   ─ 拉 7200 条 rdc_number
3. UsecaseExtractor.extract(gaia_row) ─ 每条 → SysDomainChangeUsecase
4. ExcelExporter.export(records)    ─ 单 Sheet 10 列
5. DBExporter.upsert_all(records)   ─ 分批 UPSERT（2000/批）
```

## 关键设计决策

| 维度 | 决策 | 原因 |
|---|---|---|
| **存储** | 单表 10 列 | 用户已删除 4 张子表的设计 |
| **行粒度** | 1 行 / rdc_number | 列表型字段内嵌为 JSON |
| **驱动表** | feature_sub_system_gaia | 不为空（其他源表都有空架子） |
| **列表型存储** | 紧凑 JSON 字符串（TEXT/MEDIUMTEXT 列） | 比关系表简单，Python 一行序列化 |
| **列表型展示** | Excel `indent=2` 多行 JSON | 不再是一坨长字符串 |
| **JSON 列类型** | MySQL TEXT（不用 JSON 类型） | 不需要 SQL JSON 查询 |
| **schema 迁移** | 启动时自动检查并 `ALTER TABLE` | 旧 TEXT → MEDIUMTEXT 兼容 |
| **重复运行** | UPSERT（不 truncate） | 幂等，可重复执行 |

## 测试

```bash
python -m pytest tests/ -v
```

15 个单元测试覆盖：

- `clean_solution_title`（去 `-盖亚创建`）
- `sanitize_for_excel`（快速路径 set 查找）
- 4 个 JSON 格式化函数（affected_components / modules / features / change_points）

## 进度与跳过

- **进度日志**：抽取阶段每 5% 一行 + ETA，Excel 导出 4 阶段进度，DB UPSERT 分批进度
- **跳过 Excel**：`SKIP_EXCEL=1 python run.py`（适合只想要 DB 输出的场景）

## 性能特征

实测（7200 行）：

| 阶段 | 耗时 |
|---|---|
| 抽取 | ~113 秒（约 63 rdc/s） |
| Excel 导出 | ~54 秒 |
| DB UPSERT | ~4 秒 |
| **总用时** | **~170 秒** |

## 后续可扩展

1. **子表 Excel 拆分**：当前单 Sheet，未来可按字段拆多 Sheet（特性 / 组件 / 模块各独立 Sheet）
2. **增量更新**：当前全量 UPSERT，未来加 `source_updated_at` 实现增量
3. **JSON 列索引**：如果业务方需要"按 source_system = X 查"，可升级为 MySQL JSON 类型 + 加生成列索引

## 调试

```bash
# 跳过 Excel，只跑 DB
SKIP_EXCEL=1 python run.py

# 看完整日志（包括 DEBUG 级抽取器日志）
cat output/run.log

# 清空目标表后重跑
python3 -c "
import sys; sys.path.insert(0, '.')
from config.db_config import DEFAULT_CONFIG
from src.db.connector import MySQLConnector
MySQLConnector(DEFAULT_CONFIG).execute('TRUNCATE TABLE sys_domain_change_usecase')
"
```
