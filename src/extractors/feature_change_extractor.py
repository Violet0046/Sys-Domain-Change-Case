"""特性域变更分析抽取器。

5 字段: feature_name, feature_change_type, usecase_name, usecase_change_type, change_point
按 id 排序后格式化为多行结构化文本，填入 bundle.main.feature_change_analysis。
"""
from src.db.connector import MySQLConnector
from src.db.queries import SQL_FEATURE_CHANGE_BY_RDC
from src.extractors.base import BaseExtractor
from src.models.sys_domain_change_usecase import SysDomainChangeBundle
from src.utils.logger import get_logger

log = get_logger(__name__)


class FeatureChangeExtractor(BaseExtractor):
    @staticmethod
    def _format(rows):
        if not rows:
            return ""
        lines = []
        for r in rows:
            cells = [
                str(r.get("feature_name") or ""),
                str(r.get("feature_change_type") or ""),
                str(r.get("usecase_name") or ""),
                str(r.get("usecase_change_type") or ""),
                str(r.get("change_point") or ""),
            ]
            lines.append(" | ".join(cells))
        return "\n".join(lines)

    def extract(self, bundle: SysDomainChangeBundle, connector: MySQLConnector) -> SysDomainChangeBundle:
        rows = connector.fetch_all(SQL_FEATURE_CHANGE_BY_RDC, (bundle.rdc_id,))
        text = self._format(rows)
        if bundle.main:
            bundle.main.feature_change_analysis = text
        log.debug("FeatureChangeExtractor: {} 记录 {} 条", bundle.rdc_id, len(rows))
        return bundle
