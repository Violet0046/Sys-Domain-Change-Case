"""子系统驱动 + 变更点抽取器。

作用：
1. 收集所有 (rdc_id, sub_system)，写入 bundle.subsystems（每个含 change_points）
2. 设置 bundle.main.sub_system（所有 sub_system `\n` 拼接）
"""
from src.db.connector import MySQLConnector
from src.db.queries import SQL_SYSTEM_CHANGE_BY_RDC
from src.extractors.base import BaseExtractor
from src.models.sys_domain_change_usecase import (
    SubsystemRecord, SysDomainChangeBundle,
)
from src.utils.logger import get_logger

log = get_logger(__name__)


class SubsystemChangeExtractor(BaseExtractor):
    """从 root_system_change_analysis_sub 取子系列表与变更点。"""

    def extract(self, bundle: SysDomainChangeBundle, connector: MySQLConnector) -> SysDomainChangeBundle:
        rows = connector.fetch_all(SQL_SYSTEM_CHANGE_BY_RDC, (bundle.rdc_id,))
        # 按 sub_system_name 分组收集变更点
        grouped: dict = {}
        order: list = []
        for r in rows:
            ss = (r.get("sub_system_name") or "").strip()
            if ss not in grouped:
                grouped[ss] = []
                order.append(ss)
            desc = (r.get("system_change_describe") or "").strip()
            if desc:
                grouped[ss].append(desc)

        # 写入 subsystems
        bundle.subsystems = []
        for ss in order:
            bundle.subsystems.append(SubsystemRecord(
                rdc_id=bundle.rdc_id,
                sub_system=ss,
                change_points=grouped[ss],
            ))

        # 设置 main.sub_system（joined string）
        if bundle.main:
            bundle.main.sub_system = "\n".join(order)

        log.debug("SubsystemChangeExtractor: {} 子系 {} 个", bundle.rdc_id, len(bundle.subsystems))
        return bundle
