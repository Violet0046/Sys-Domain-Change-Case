"""所有 SQL 常量集中管理。

驱动表：feature_sub_system_gaia
子系/组件/模块/特性域 全部以 (rdc_id, sub_system) 双键定位。
"""
import json

# ---------- 驱动表：feature_sub_system_gaia ----------
SQL_DRIVER_BASE = """
SELECT
    rdc_number,
    title,
    description,
    algorithm,
    implementation,
    sub_system
FROM feature_sub_system_gaia
WHERE rdc_number IS NOT NULL AND rdc_number != ""
ORDER BY id
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
SQL_COMPONENT_BY_RDC = """
SELECT
    sub_system,
    business_number,
    source_system,
    business_flow,
    aim_system,
    change_type,
    change_describe
FROM root_in_sub_system_process_sub
WHERE rdc_id = %s
ORDER BY id
"""

# ---------- 波及模块 ----------
SQL_MODULE_BY_RDC = """
SELECT
    sub_system,
    sender,
    receiver,
    business_flow,
    output_strategy,
    change_type,
    remarks
FROM root_component_main
WHERE rdc_id = %s
ORDER BY id
"""

# ---------- 波及的变更点 ----------
SQL_CHANGE_POINTS_BY_RDC = """
SELECT
    sub_system_name,
    system_change_describe
FROM root_system_change_analysis_sub
WHERE rdc_id = %s AND sub_system_name IS NOT NULL AND sub_system_name != ""
ORDER BY id
"""

# ---------- 目标表 DDL ----------
DDL_TARGET_TABLE = """
CREATE TABLE IF NOT EXISTS sys_domain_change_usecase (
    rdc_number                 VARCHAR(64)  NOT NULL,
    title                      MEDIUMTEXT,
    feature_change_analysis    MEDIUMTEXT,
    description                MEDIUMTEXT,
    algorithm                  MEDIUMTEXT,
    implementation             MEDIUMTEXT,
    sub_systems                MEDIUMTEXT,
    affected_components        MEDIUMTEXT,
    affected_modules           MEDIUMTEXT,
    change_points              MEDIUMTEXT,
    created_at                 DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at                 DATETIME DEFAULT CURRENT_TIMESTAMP
                                        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (rdc_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

# 帮助工具
def build_sub_systems_json(gaia_sub_system_str: str) -> str:
    """从 gaia.sub_system 字段提取 subSystem 字段并去重 → JSON 数组。

    输入是 gaia 表里的 JSON 字段，类似：
      '[{"cases":[{"case":"...","subSystem":"PHY",...}],"feature":"..."}]'
    输出：'["PHY","SPA"]'
    """
    if not gaia_sub_system_str:
        return json.dumps([], ensure_ascii=False)
    try:
        items = json.loads(gaia_sub_system_str)
    except Exception:
        return json.dumps([], ensure_ascii=False)
    seen = []
    seen_set = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        for case in item.get("cases", []) or []:
            ss = (case.get("subSystem") or "").strip()
            if ss and ss not in seen_set:
                seen.append(ss)
                seen_set.add(ss)
    return json.dumps(seen, ensure_ascii=False)
