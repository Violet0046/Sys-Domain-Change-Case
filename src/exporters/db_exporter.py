"""DB 导出器（单表 UPSERT）。"""
import time
from typing import List

from src.db.connector import MySQLConnector
from src.db.queries import DDL_TARGET_TABLE
from src.models.sys_domain_change_usecase import SysDomainChangeUsecase
from src.utils.logger import get_logger

log = get_logger(__name__)


class DBExporter:
    TABLE = "sys_domain_change_usecase"

    def __init__(self, connector: MySQLConnector):
        self.connector = connector

    def ensure_tables(self):
        self.connector.execute(DDL_TARGET_TABLE)
        self._migrate_text_to_mediumtext()
        log.info("目标表已就绪: {}", self.TABLE)

    def _migrate_text_to_mediumtext(self):
        """升级所有 TEXT → MEDIUMTEXT，兼容 64KB+ 数据。"""
        target_cols = ["title", "feature_change_analysis", "description",
                       "algorithm", "implementation", "sub_systems",
                       "affected_components", "affected_modules", "change_points"]
        for col in target_cols:
            rows = self.connector.fetch_all(
                "SELECT DATA_TYPE FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() "
                "AND TABLE_NAME = %s AND COLUMN_NAME = %s",
                (self.TABLE, col),
            )
            if rows and rows[0].get("DATA_TYPE", "").lower() == "text":
                self.connector.execute(
                    f"ALTER TABLE {self.TABLE} MODIFY COLUMN {col} MEDIUMTEXT"
                )
                log.info("升级 {} 列 TEXT → MEDIUMTEXT", col)

    def _batched_upsert(self, rows: list, batch_size: int = 2000):
        """单表 UPSERT（rdc_number 是 PK）。"""
        if not rows:
            return 0
        total = len(rows)
        log_step = max(1, total // 10)
        done = 0
        start = time.time()
        sql = f"""
        INSERT INTO {self.TABLE}
            (rdc_number, title, feature_change_analysis,
             description, algorithm, implementation,
             sub_systems, affected_components, affected_modules,
             change_points)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            title = VALUES(title),
            feature_change_analysis = VALUES(feature_change_analysis),
            description = VALUES(description),
            algorithm = VALUES(algorithm),
            implementation = VALUES(implementation),
            sub_systems = VALUES(sub_systems),
            affected_components = VALUES(affected_components),
            affected_modules = VALUES(affected_modules),
            change_points = VALUES(change_points)
        """
        log.info("DB 开始回写 {}: {} 行", self.TABLE, total)
        for i in range(0, total, batch_size):
            chunk = rows[i:i + batch_size]
            try:
                self.connector.execute_many(sql, chunk)
                done += len(chunk)
                if done % log_step == 0 or done == total:
                    elapsed = time.time() - start
                    rate = done / elapsed if elapsed > 0 else 0
                    eta = (total - done) / rate if rate > 0 else 0
                    log.info(
                        "DB [{:<6}] {:>6}/{:<6} ({:>4.0%}) | 速率 {:>5.0f} 行/s | 剩余 {:>4.1f}s",
                        self.TABLE, done, total, done / total, rate, eta,
                    )
            except Exception as e:
                log.error("DB [{:<6}] 第 {} 批失败: {}", self.TABLE, i // batch_size, e)
                raise
        log.info("DB [{}] 完成: {} 行 | {}s", self.TABLE, done, int(time.time() - start))
        return done

    def upsert_all(self, records: List[SysDomainChangeUsecase]):
        rows = []
        for r in records:
            rows.append((
                r.rdc_number,
                r.title or "",
                r.feature_change_analysis or "",
                r.description or "",
                r.algorithm or "",
                r.implementation or "",
                r.sub_systems or "",
                r.affected_components or "",
                r.affected_modules or "",
                r.change_points or "",
            ))
        return self._batched_upsert(rows)
