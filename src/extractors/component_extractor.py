"""波及组件抽取器。

按 (rdc_id, sub_system) 遍历 bundle.subsystems，从 root_in_sub_system_process_sub 取组件。
"""
from src.db.connector import MySQLConnector
from src.db.queries import SQL_COMPONENT_BY_RDC_SUBSYSTEM
from src.extractors.base import BaseExtractor
from src.models.sys_domain_change_usecase import ComponentRecord, SysDomainChangeBundle
from src.utils.logger import get_logger

log = get_logger(__name__)


class ComponentExtractor(BaseExtractor):
    def extract(self, bundle: SysDomainChangeBundle, connector: MySQLConnector) -> SysDomainChangeBundle:
        for sub_rec in bundle.subsystems:
            sub = sub_rec.sub_system
            if not sub:
                continue
            rows = connector.fetch_all(SQL_COMPONENT_BY_RDC_SUBSYSTEM, (bundle.rdc_id, sub))
            for r in rows:
                bundle.components.append(ComponentRecord(
                    rdc_id=bundle.rdc_id,
                    sub_system=sub,
                    business_flow=(r.get("business_flow") or "").strip(),
                    source_system=(r.get("source_system") or "").strip(),
                    aim_system=(r.get("aim_system") or "").strip(),
                    change_type=(r.get("change_type") or "").strip(),
                    change_describe=(r.get("change_describe") or "").strip(),
                ))
        log.debug("ComponentExtractor: {} 收集 {} 条", bundle.rdc_id, len(bundle.components))
        return bundle
