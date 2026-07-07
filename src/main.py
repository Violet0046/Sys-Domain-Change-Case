"""主程序入口。

流水线：
  1. 建/校验目标表（含迁移）
  2. 从 root_system_change_analysis_sub 拉所有 distinct rdc_id（驱动表）
  3. 对每个 rdc_id 创建空 bundle，依次跑 extractor 流水线
  4. 导出 Excel：主表 / 子系表 / 组件表 / 模块表
  5. 回写 DB
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.db_config import DEFAULT_CONFIG
from src.db.connector import MySQLConnector
from src.db.queries import SQL_DRIVER_BASE
from src.exporters.db_exporter import DBExporter
from src.exporters.excel_exporter import ExcelExporter
from src.extractors.component_extractor import ComponentExtractor
from src.extractors.feature_change_extractor import FeatureChangeExtractor
# GaiaBaseExtractor 已废除：bundle 创建时直接从 gaia 行预填，不再回查
from src.extractors.module_extractor import ModuleExtractor
from src.extractors.subsystem_change_extractor import SubsystemChangeExtractor
from src.models.sys_domain_change_usecase import (
    SysDomainChangeBundle, SysDomainChangeUsecase,
)
from src.utils.logger import get_logger
from src.utils.text_clean import clean_solution_title

log = get_logger(__name__)


def build_pipeline(connector: MySQLConnector) -> list:
    """构造抽取器流水线。顺序很重要。

    注意：不再需要 GaiaBaseExtractor，因为 bundle 创建时直接从 gaia 行预填
    方案级字段（solution/requirement/algorithm/implementation）。
    """
    return [
        SubsystemChangeExtractor(),  # 必须最先：决定 subsystems 列表 + main.sub_system 拼接串
        FeatureChangeExtractor(),    # 填 main.feature_change_analysis
        ComponentExtractor(),        # 遍历 subsystems，收集组件
        ModuleExtractor(),           # 遍历 subsystems，收集模块
    ]


def process_one(connector: MySQLConnector, gaia_row: dict, pipeline: list) -> SysDomainChangeBundle:
    """从 gaia 一行驱动：构造 rdc_id，预填方案级字段，跑其他抽取器。"""
    rdc_number = (gaia_row.get("rdc_number") or "").strip()
    rdc_id = f"[{rdc_number}]"
    main = SysDomainChangeUsecase(
        rdc_id=rdc_id,
        solution=clean_solution_title(gaia_row.get("title") or ""),
        requirement=(gaia_row.get("description") or ""),
        algorithm=(gaia_row.get("algorithm") or ""),
        implementation=(gaia_row.get("implementation") or ""),
    )
    bundle = SysDomainChangeBundle(rdc_id=rdc_id, main=main)
    for extractor in pipeline:
        bundle = extractor.extract(bundle, connector)
    return bundle


def run():
    log.info("=== 系统域变更分析场景用例 生成任务启动 ===")
    connector = MySQLConnector(DEFAULT_CONFIG)
    if not connector.test_connection():
        log.error("DB 连接失败，终止")
        return

    db_exporter = DBExporter(connector)
    db_exporter.ensure_tables()

    # 驱动：root_system_change_analysis_sub
    driver_rows = connector.fetch_all(SQL_DRIVER_BASE)
    log.info("驱动 feature_sub_system_gaia 共有 {} 条 rdc_number", len(driver_rows))

    pipeline = build_pipeline(connector)
    bundles = []
    total_sub = total_comp = total_mod = 0
    failed = []
    start = time.time()
    log_step = max(1, len(driver_rows) // 20)

    for idx, gaia_row in enumerate(driver_rows, 1):
        rdc_number = (gaia_row.get("rdc_number") or "").strip()
        rdc_id = f"[{rdc_number}]"
        try:
            bundle = process_one(connector, gaia_row, pipeline)
            bundles.append(bundle)
            total_sub += len(bundle.subsystems)
            total_comp += len(bundle.components)
            total_mod += len(bundle.modules)
        except Exception as e:
            log.warning("rdc_id={} 处理失败: {}", rdc_id, e)
            failed.append(rdc_id)

        # 批量进度日志（约每 5% 一行）
        if idx % log_step == 0 or idx == len(driver_rows):
            elapsed = time.time() - start
            rate = idx / elapsed if elapsed > 0 else 0
            eta = (len(driver_rows) - idx) / rate if rate > 0 else 0
            log.info(
                "进度 [{:>5}/{:<5}] {:.0%} | 速率 {:.1f} rdc/s | 已用 {:>4}s | 预计剩余 {:>4}s | 失败 {}",
                idx, len(driver_rows), idx / len(driver_rows), rate, int(elapsed), int(eta), len(failed),
            )

    extract_secs = time.time() - start
    log.info(
        "抽取完成: {} bundles | 子系 {} 行 / 组件 {} 条 / 模块 {} 条 | 失败 {} | 用时 {}s",
        len(bundles), total_sub, total_comp, total_mod, len(failed), int(extract_secs),
    )
    if failed:
        log.warning("失败 rdc_id 列表（前 10）: {}", failed[:10])

    excel_start = time.time()
    excel_path = ExcelExporter().export(bundles)
    log.info("Excel 写入完成: {} | {}s", excel_path, int(time.time() - excel_start))

    db_start = time.time()
    db_exporter.upsert_all(bundles)
    log.info("DB 回写完成 | {}s", int(time.time() - db_start))

    log.info("=== 任务结束 | 总用时 {}s ===", int(time.time() - start))


if __name__ == "__main__":
    run()
