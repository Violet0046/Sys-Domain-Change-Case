"""主表方案级字段抽取器。

从 feature_sub_system_gaia 取：rdc_number, title→solution, description, algorithm, implementation
填到 bundle.main 这唯一一行。
"""
from src.db.connector import MySQLConnector
from src.db.queries import SQL_GAIA_BY_RDC
from src.extractors.base import BaseExtractor
from src.models.sys_domain_change_usecase import SysDomainChangeBundle
from src.utils.logger import get_logger
from src.utils.text_clean import clean_solution_title

log = get_logger(__name__)


class GaiaBaseExtractor(BaseExtractor):
    def extract(self, bundle: SysDomainChangeBundle, connector: MySQLConnector) -> SysDomainChangeBundle:
        row = connector.fetch_one(SQL_GAIA_BY_RDC, (bundle.rdc_id,))
        if not row:
            log.warning("feature_sub_system_gaia 未找到 rdc_id={}", bundle.rdc_id)
            return bundle

        if bundle.main is None:
            return bundle

        bundle.main.solution = clean_solution_title(row.get("title") or "")
        bundle.main.requirement = row.get("description") or ""
        bundle.main.algorithm = row.get("algorithm") or ""
        bundle.main.implementation = row.get("implementation") or ""

        log.debug("GaiaBaseExtractor 完成: {}", bundle.rdc_id)
        return bundle
