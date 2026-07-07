# 系统域变更分析场景用例（sys_domain_change_usecase）

从 MySQL `solution_knowledge` 库的 6 张业务表抽取、清洗、关联数据，生成"系统域变更分析场景用例"汇总表，同时输出 Excel 和回写 MySQL。

## 数据源

| 表 | 用途 |
|---|---|
| `feature_sub_system_gaia` | 主表（驱动），提供 rdc_number / title / description / algorithm / implementation |
| `root_feature_change_analysis_sub` | 特性域变更分析（5 字段） |
| `root_system_change_analysis_sub` | **驱动行数展开**：按 `sub_system_name` 展开，每个子系统一行 |
| `root_in_sub_system_process_sub` | 波及组件（source_system / aim_system） |
| `root_component_main` | 波及模块（sender/receiver/business_flow/...，含去重合并） |

`feature_sub_system_gaia` 没有 `rdc_id` 字段，关联键为 `CONCAT('[', rdc_number, ']')`。

## 字段映射

### 主表（按 sub_system 展开）
| 列 | 来源 | 处理 |
|---|---|---|
| rdc_id | CONCAT('[', rdc_number, ']') | 关联键 |
| rdc_number | gaia.rdc_number | 直接 |
| 方案 | gaia.title | 去 `-盖亚创建` 后缀 |
| 特性域变更分析结果 | root_feature_change_analysis_sub | 5 字段 `\|` 拼接为多行 |
| 需求描述 | gaia.description | 直接 |
| 算法描述 | gaia.algorithm | 直接（暂不处理 icenter 链接） |
| 实现思路 | gaia.implementation | 直接 |
| 波及子系统 | root_system_change_analysis_sub.sub_system_name | 每行一个 |
| 波及的变更点 | root_system_change_analysis_sub.system_change_describe | 同 sub_system 下多条 `\n` 拼接 |

### 波及组件 Sheet
`(rdc_id, sub_system, source_system, aim_system)`，按双键 `(rdc_id, sub_system)` 从 `root_in_sub_system_process_sub` 取。

### 波及模块 Sheet
`(rdc_id, sub_system, sender, receiver, business_flow, output_strategy, change_type, remarks)`，按双键从 `root_component_main` 取。

**去重合并规则**：当 `sender/receiver/output_strategy/change_type/remarks` 全部相同，但 `business_flow` 不同时，合并为一行，`business_flow` 字段用 `\n` 拼接。

## 运行

```bash
# 安装依赖
pip install -r requirements.txt

# 执行
python run.py
```

### 输出
- `output/sys_domain_change_usecase.xlsx`：3 个 Sheet（主表 / 波及组件 / 波及模块）
- MySQL 三张目标表：
  - `sys_domain_change_usecase`
  - `sys_domain_change_usecase_component`
  - `sys_domain_change_usecase_module`
- `output/run.log`：运行日志

## 项目结构

```
.
├── config/db_config.py             # DB 连接配置（支持环境变量覆盖）
├── src/
│   ├── main.py                     # 主程序：编排 + 双导出
│   ├── db/
│   │   ├── connector.py            # pymysql + DBUtils 连接池
│   │   └── queries.py              # 全部 SQL 常量
│   ├── extractors/                 # 各字段独立抽取器
│   │   ├── base.py
│   │   ├── gaia_base_extractor.py
│   │   ├── feature_change_extractor.py
│   │   ├── subsystem_change_extractor.py   # 驱动行数展开
│   │   ├── component_extractor.py
│   │   └── module_extractor.py             # 含去重合并
│   ├── models/
│   │   └── sys_domain_change_usecase.py
│   ├── utils/
│   │   ├── text_clean.py
│   │   └── logger.py
│   └── exporters/
│       ├── excel_exporter.py       # openpyxl，3-Sheet
│       └── db_exporter.py          # 建表 + UPSERT 回写
├── tests/
│   └── test_text_clean.py          # pytest
├── run.py
└── requirements.txt
```

## 测试

```bash
python -m pytest tests/ -v
```

## 边界处理

- `rdc_id` 在 `root_system_change_analysis_sub` 无记录 → 输出 1 行（波及子系统等为空）
- `sub_system_name` 为空的脏数据 → 过滤掉，不驱动行展开
- 单个 `rdc_id` 处理异常 → 记录日志后跳过，不影响整体流程

## 后续可扩展

1. **增量更新**：在目标表加 `source_updated_at` 列，按源表 `last_date` 增量同步
2. **icenter 算法链接**：当前仅取 `algorithm` 文本；后续若需要拉 icenter 内容，可在 `AlgorithmExtractor` 加分支
3. **目标表重跑策略**：当前是 UPSERT 全量；如需按时间窗口分区，可改造 `_upsert_*` 方法