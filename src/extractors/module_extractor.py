"""波及模块抽取器（无去重，按源表原样保留）。

按 (rdc_id, sub_system) 遍历 bundle.subsystems，
从 root_component_main 逐行写入 bundle.modules。

主键由 DBExporter / DDL_MODULE_TABLE 定义为 (rdc_id, sub_system, business_flow)，
所以业务流不同的行会被自然区分保留（不再合并）。
"""
from typing import List

from src.db.connector import MySQLConnector
from src.db.queries import SQL_MODULE_BY_RDC_SUBSYSTEM
from src.extractors.base import BaseExtractor
from src.models.sys_domain_change_usecase import ModuleRecord, SysDomainChangeBundle
from src.utils.logger import get_logger

log = get_logger(__name__)


class ModuleExtractor(BaseExtractor):
    def extract(self, bundle: SysDomainChangeBundle, connector: MySQLConnector) -> SysDomainChangeBundle:
        for sub_rec in bundle.subsystems:
            sub = sub_rec.sub_system
            if not sub:
                continue
            rows = connector.fetch_all(SQL_MODULE_BY_RDC_SUBSYSTEM, (bundle.rdc_id, sub))
            for r in rows:
                bundle.modules.append(ModuleRecord(
                    rdc_id=bundle.rdc_id,
                    sub_system=sub,
                    sender=(r.get("sender") or "").strip(),
                    receiver=(r.get("receiver") or "").strip(),
                    business_flow=(r.get("business_flow") or "").strip(),
                    output_strategy=(r.get("output_strategy") or "").strip(),
                    change_type=(r.get("change_type") or "").strip(),
                    remarks=(r.get("remarks") or "").strip(),
                ))
        log.debug("ModuleExtractor: {} 收集 {} 条", bundle.rdc_id, len(bundle.modules))
        return bundle
