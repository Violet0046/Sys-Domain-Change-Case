"""主程序入口。

流水线：
  1. 建表
  2. 从 feature_sub_system_gaia 拉所有 rdc_number（驱动表）
  3. 对每行用 UsecaseExtractor 抽取 10 字段
  4. 导出 Excel（单 Sheet，10 列）
  5. 回写 DB（单表 UPSERT）
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.db_config import DEFAULT_CONFIG
from src.db.connector import MySQLConnector
from src.db.queries import SQL_DRIVER_BASE
from src.exporters.db_exporter import DBExporter
from src.exporters.excel_exporter import ExcelExporter
from src.extractors.usecase_extractor import UsecaseExtractor
from src.utils.logger import get_logger

log = get_logger(__name__)


def run():
    log.info("=== 系统域变更分析场景用例 生成任务启动 ===")
    connector = MySQLConnector(DEFAULT_CONFIG)
    if not connector.test_connection():
        log.error("DB 连接失败，终止")
        return

    db_exporter = DBExporter(connector)
    db_exporter.ensure_tables()

    driver_rows = connector.fetch_all(SQL_DRIVER_BASE)
    total = len(driver_rows)
    log.info("驱动 feature_sub_system_gaia 共有 {} 条 rdc_number", total)

    extractor = UsecaseExtractor(connector)
    records = []
    failed = []
    start = time.time()
    log_step = max(1, total // 20)

    for idx, gaia_row in enumerate(driver_rows, 1):
        rdc_number = (gaia_row.get("rdc_number") or "").strip()
        try:
            rec = extractor.extract(gaia_row)
            records.append(rec)
        except Exception as e:
            log.warning("rdc_number={} 处理失败: {}", rdc_number, e)
            failed.append(rdc_number)

        if idx % log_step == 0 or idx == total:
            elapsed = time.time() - start
            rate = idx / elapsed if elapsed > 0 else 0
            eta = (total - idx) / rate if rate > 0 else 0
            log.info(
                "进度 [{:>5}/{:<5}] {:.0%} | 速率 {:.1f} rdc/s | 已用 {:>4}s | 预计剩余 {:>4}s | 失败 {}",
                idx, total, idx / total, rate, int(elapsed), int(eta), len(failed),
            )

    extract_secs = time.time() - start
    log.info("抽取完成: {} 行 | 失败 {} | 用时 {}s", len(records), len(failed), int(extract_secs))
    if failed:
        log.warning("失败 rdc_number 前 10: {}", failed[:10])

    if not os.getenv("SKIP_EXCEL"):
        excel_start = time.time()
        ExcelExporter().export(records)
        log.info("Excel 阶段用时: {}s", int(time.time() - excel_start))
    else:
        log.info("Excel 写入已跳过（SKIP_EXCEL=1）")

    db_start = time.time()
    db_exporter.upsert_all(records)
    log.info("DB 阶段用时: {}s", int(time.time() - db_start))

    log.info("=== 任务结束 | 总用时 {}s ===", int(time.time() - start))


if __name__ == "__main__":
    run()
