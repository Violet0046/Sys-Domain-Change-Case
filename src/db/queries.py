"""所有 SQL 常量集中管理。

驱动表：root_system_change_analysis_sub（其 rdc_id 原生带 [RAN-XXX] 方括号）
辅助表：feature_sub_system_gaia 等
"""

# ---------- 驱动表：feature_sub_system_gaia ----------
# gaia 的 rdc_number 不带方括号，但其他 5 张表的 rdc_id 都是 [RAN-XXX] 格式。
# 这里把 gaia 的方案级字段全部 SELECT 出来，bundle 创建时一次性预填，
# 跨表 JOIN 时再用 f"[{rdc_number}]" 构造 rdc_id。
SQL_DRIVER_BASE = """
SELECT
    rdc_number,
    title,
    description,
    algorithm,
    implementation
FROM feature_sub_system_gaia
WHERE rdc_number IS NOT NULL AND rdc_number != ''
ORDER BY id
"""

SQL_SYSTEM_CHANGE_BY_RDC = """
SELECT
    sub_system_name,
    system_change_describe
FROM root_system_change_analysis_sub
WHERE rdc_id = %s AND sub_system_name IS NOT NULL AND sub_system_name != ''
ORDER BY id
"""

# ---------- 主表：feature_sub_system_gaia ----------
# gaia 表没有 rdc_id 字段，通过 CONCAT('[', rdc_number, ']') 与 driver 对齐
SQL_GAIA_BY_RDC = """
SELECT
    rdc_number,
    title,
    description,
    algorithm,
    implementation
FROM feature_sub_system_gaia
WHERE rdc_number IS NOT NULL AND rdc_number != ''
  AND CONCAT('[', rdc_number, ']') = %s
LIMIT 1
"""

# ---------- 特性域变更分析 ----------
SQL_FEATURE_CHANGE_BY_RDC = """
SELECT
    feature_name,
    feature_change_type,
    usecase_name,
    usecase_change_type,
    change_point
FROM root_feature_change_analysis_sub
WHERE rdc_id = %s
ORDER BY id
"""

# ---------- 波及组件 ----------
SQL_COMPONENT_BY_RDC_SUBSYSTEM = """
SELECT
    sub_system,
    business_flow,
    change_type,
    change_describe,
    source_system,
    aim_system
FROM root_in_sub_system_process_sub
WHERE rdc_id = %s AND sub_system = %s
ORDER BY id
"""

# ---------- 波及模块 ----------
SQL_MODULE_BY_RDC_SUBSYSTEM = """
SELECT
    sub_system,
    sender,
    receiver,
    business_flow,
    output_strategy,
    change_type,
    remarks
FROM root_component_main
WHERE rdc_id = %s AND sub_system = %s
ORDER BY id
"""

# ---------- 目标表 DDL ----------
# 主表：1 行/rdc_id（不动 sub_system 维度）
DDL_TARGET_TABLE = """
CREATE TABLE IF NOT EXISTS sys_domain_change_usecase (
    rdc_id              VARCHAR(64)  NOT NULL,
    sub_system          TEXT,
    solution            TEXT,
    feature_change_analysis TEXT,
    requirement         TEXT,
    algorithm           TEXT,
    implementation      TEXT,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (rdc_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

# 用于检测旧 schema（包含 rdc_number 列说明表结构过时）
TARGET_TABLE_HAS_RDC_NUMBER_COLUMN = "rdc_number"

# 子系表：1 行/(rdc_id, sub_system)，存 change_points
DDL_SUBSYSTEM_TABLE = """
CREATE TABLE IF NOT EXISTS sys_domain_change_usecase_subsystem (
    rdc_id          VARCHAR(64)  NOT NULL,
    sub_system      VARCHAR(128) NOT NULL,
    change_points   TEXT,
    PRIMARY KEY (rdc_id, sub_system)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

# 组件子表
DDL_COMPONENT_TABLE = """
CREATE TABLE IF NOT EXISTS sys_domain_change_usecase_component (
    rdc_id          VARCHAR(64)  NOT NULL,
    sub_system      VARCHAR(128) NOT NULL,
    business_flow   VARCHAR(256),
    source_system   VARCHAR(128) NOT NULL,
    aim_system      VARCHAR(128) NOT NULL,
    change_type     VARCHAR(128),
    change_describe TEXT,
    PRIMARY KEY (rdc_id, sub_system, business_flow, source_system, aim_system)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

# 模块子表
DDL_MODULE_TABLE = """
CREATE TABLE IF NOT EXISTS sys_domain_change_usecase_module (
    rdc_id          VARCHAR(64)  NOT NULL,
    sub_system      VARCHAR(128) NOT NULL,
    business_flow   VARCHAR(256) NOT NULL DEFAULT '',
    sender          VARCHAR(128),
    receiver        VARCHAR(128),
    output_strategy VARCHAR(256),
    change_type     VARCHAR(128),
    remarks         TEXT,
    PRIMARY KEY (rdc_id, sub_system, business_flow)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

# 旧模块表识别：没有 PK
MODULE_TABLE_OLD_NO_PK = "__no_pk_marker__"

# 旧主表识别列（如果存在 change_points 列，说明是旧的多行/rdc_id 结构）
TARGET_TABLE_OLD_SCHEMA_COLUMN = "change_points"
# 旧组件表识别列（同前一轮）
COMPONENT_TABLE_OLD_SCHEMA_COLUMN = "usecase_name"
