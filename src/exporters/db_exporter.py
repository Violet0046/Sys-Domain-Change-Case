"""DB 导出器：建表（含迁移）+ 回写 4 张表。"""
from typing import List

from src.db.connector import MySQLConnector
from src.db.queries import (
    DDL_COMPONENT_TABLE, DDL_MODULE_TABLE, DDL_SUBSYSTEM_TABLE, DDL_TARGET_TABLE,
    COMPONENT_TABLE_OLD_SCHEMA_COLUMN, TARGET_TABLE_OLD_SCHEMA_COLUMN,
    TARGET_TABLE_HAS_RDC_NUMBER_COLUMN,
)
from src.models.sys_domain_change_usecase import SysDomainChangeBundle
from src.utils.logger import get_logger

log = get_logger(__name__)


class DBExporter:
    TABLE_MAIN = "sys_domain_change_usecase"
    TABLE_SUBSYSTEM = "sys_domain_change_usecase_subsystem"
    TABLE_COMPONENT = "sys_domain_change_usecase_component"
    TABLE_MODULE = "sys_domain_change_usecase_module"

    def __init__(self, connector: MySQLConnector):
        self.connector = connector

    # ---------- 建表（含迁移）----------
    def ensure_tables(self):
        for ddl in (DDL_TARGET_TABLE, DDL_SUBSYSTEM_TABLE, DDL_COMPONENT_TABLE, DDL_MODULE_TABLE):
            self.connector.execute(ddl)
        self._migrate_target_table()
        self._migrate_component_table()
        self._migrate_module_table()
        log.info("目标表已就绪")

    def _table_has_primary_key(self, table: str) -> bool:
        """检测表是否有主键。"""
        rows = self.connector.fetch_all(
            f"SHOW KEYS FROM {table} WHERE Key_name = 'PRIMARY'"
        )
        return bool(rows)

    def _migrate_module_table(self):
        """检测旧 module 表（无主键）→ DROP 重建，加 PK。

        旧 module 表无 PK 时 UPSERT 不工作，必须重建。
        """
        if not self._table_has_primary_key(self.TABLE_MODULE):
            log.warning("检测到 module 表无主键，DROP 后重建")
            self.connector.execute(f"DROP TABLE IF EXISTS {self.TABLE_MODULE}")
            self.connector.execute(DDL_MODULE_TABLE)
            log.info("已用 3 字段 PK (rdc_id, sub_system, business_flow) 重建 {}", self.TABLE_MODULE)

    def _column_exists(self, table: str, column: str) -> bool:
        rows = self.connector.fetch_all(
            "SELECT 1 FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
            (table, column),
        )
        return bool(rows)

    def _migrate_target_table(self):
        """检测旧主表 schema → DROP 重建。触发条件：
        1. 含 change_points 列（旧多行结构）
        2. 含 rdc_number 列（旧冗余字段）
        新主表只有 1 行/rdc_id，且不含 rdc_number。
        """
        needs_drop = (
            self._column_exists(self.TABLE_MAIN, TARGET_TABLE_OLD_SCHEMA_COLUMN)
            or self._column_exists(self.TABLE_MAIN, TARGET_TABLE_HAS_RDC_NUMBER_COLUMN)
        )
        if needs_drop:
            log.warning("检测到旧主表 schema，DROP 后重建")
            self.connector.execute(f"DROP TABLE IF EXISTS {self.TABLE_MAIN}")
            self.connector.execute(DDL_TARGET_TABLE)
            log.info("已用新 schema 重建 {}", self.TABLE_MAIN)

    def _migrate_component_table(self):
        if self._column_exists(self.TABLE_COMPONENT, COMPONENT_TABLE_OLD_SCHEMA_COLUMN):
            log.warning("检测到旧 component 表（存在 {} 列），DROP 后重建", COMPONENT_TABLE_OLD_SCHEMA_COLUMN)
            self.connector.execute(f"DROP TABLE IF EXISTS {self.TABLE_COMPONENT}")
            self.connector.execute(DDL_COMPONENT_TABLE)
            log.info("已用新 schema 重建 {}", self.TABLE_COMPONENT)

    # ---------- 回写 ----------
    def upsert_all(self, bundles: List[SysDomainChangeBundle]):
        self._upsert_main(bundles)
        self._upsert_subsystems(bundles)
        self._upsert_components(bundles)
        self._upsert_modules(bundles)

    def _upsert_main(self, bundles: List[SysDomainChangeBundle]):
        rows = []
        for b in bundles:
            if b.main is None:
                continue
            m = b.main
            rows.append((
                m.rdc_id,
                m.sub_system or "",
                m.solution or "",
                m.feature_change_analysis or "",
                m.requirement or "",
                m.algorithm or "",
                m.implementation or "",
            ))
        if not rows:
            return
        sql = f"""
        INSERT INTO {self.TABLE_MAIN}
            (rdc_id, sub_system, solution, feature_change_analysis,
             requirement, algorithm, implementation)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            sub_system = VALUES(sub_system),
            solution = VALUES(solution),
            feature_change_analysis = VALUES(feature_change_analysis),
            requirement = VALUES(requirement),
            algorithm = VALUES(algorithm),
            implementation = VALUES(implementation)
        """
        n = self.connector.execute_many(sql, rows)
        log.info("主表回写 {} 行", n)

    def _upsert_subsystems(self, bundles: List[SysDomainChangeBundle]):
        rows = []
        for b in bundles:
            for s in b.subsystems:
                cps = "\n".join(s.change_points) if s.change_points else ""
                rows.append((s.rdc_id, s.sub_system, cps))
        if not rows:
            return
        sql = f"""
        INSERT INTO {self.TABLE_SUBSYSTEM}
            (rdc_id, sub_system, change_points)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            change_points = VALUES(change_points)
        """
        n = self.connector.execute_many(sql, rows)
        log.info("子系表回写 {} 行", n)

    def _upsert_components(self, bundles: List[SysDomainChangeBundle]):
        rows = [(c.rdc_id, c.sub_system,
                 c.business_flow,
                 c.source_system, c.aim_system,
                 c.change_type, c.change_describe)
                for b in bundles for c in b.components]
        if not rows:
            return
        sql = f"""
        INSERT INTO {self.TABLE_COMPONENT}
            (rdc_id, sub_system,
             business_flow,
             source_system, aim_system,
             change_type, change_describe)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            business_flow = VALUES(business_flow),
            source_system = VALUES(source_system),
            aim_system = VALUES(aim_system),
            change_type = VALUES(change_type),
            change_describe = VALUES(change_describe)
        """
        n = self.connector.execute_many(sql, rows)
        log.info("组件表回写 {} 行", n)

    def _upsert_modules(self, bundles: List[SysDomainChangeBundle]):
        rows = []
        for b in bundles:
            for m in b.modules:
                rows.append((
                    m.rdc_id, m.sub_system,
                    m.sender, m.receiver, m.business_flow,
                    m.output_strategy, m.change_type, m.remarks,
                ))
        if not rows:
            return
        sql = f"""
        INSERT INTO {self.TABLE_MODULE}
            (rdc_id, sub_system, sender, receiver, business_flow,
             output_strategy, change_type, remarks)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            business_flow = VALUES(business_flow),
            output_strategy = VALUES(output_strategy),
            change_type = VALUES(change_type),
            remarks = VALUES(remarks)
        """
        n = self.connector.execute_many(sql, rows)
        log.info("模块表回写 {} 行", n)
