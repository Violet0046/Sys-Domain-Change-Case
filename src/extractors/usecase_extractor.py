"""方案抽取器（合并所有字段于一处）。

输入：feature_sub_system_gaia 一行（rdc_number, title, description, algorithm, implementation, sub_system）
输出：SysDomainChangeUsecase（10 个字段全填）
"""
import json
from typing import List

from src.db.connector import MySQLConnector
from src.db.queries import (
    SQL_CHANGE_POINTS_BY_RDC, SQL_COMPONENT_BY_RDC,
    SQL_FEATURE_CHANGE_BY_RDC, SQL_MODULE_BY_RDC,
    build_sub_systems_json,
)
from src.models.sys_domain_change_usecase import SysDomainChangeUsecase
from src.utils.logger import get_logger
from src.utils.text_clean import clean_solution_title

log = get_logger(__name__)


def _format_features(rows) -> str:
    """特性域变更分析结果：JSON 字符串，每条是 5 字段 dict。"""
    if not rows:
        return json.dumps([], ensure_ascii=False)
    items = []
    for r in rows:
        items.append({
            "feature_name": (r.get("feature_name") or "").strip(),
            "feature_change_type": (r.get("feature_change_type") or "").strip(),
            "usecase_name": (r.get("usecase_name") or "").strip(),
            "usecase_change_type": (r.get("usecase_change_type") or "").strip(),
            "change_point": (r.get("change_point") or "").strip(),
        })
    return json.dumps(items, ensure_ascii=False)


def _format_change_points(rows) -> str:
    """波及的变更点：JSON 字符串。"""
    if not rows:
        return json.dumps([], ensure_ascii=False)
    items = []
    for r in rows:
        items.append({
            "sub_system": (r.get("sub_system_name") or "").strip(),
            "system_change_describe": (r.get("system_change_describe") or "").strip(),
        })
    return json.dumps(items, ensure_ascii=False)


def _format_affected_components(rows) -> str:
    """波及组件：大 JSON 对象，按 sub_system 分组。"""
    if not rows:
        return json.dumps([], ensure_ascii=False)
    groups = {}
    order = []
    for r in rows:
        ss = (r.get("sub_system") or "").strip()
        if ss not in groups:
            groups[ss] = []
            order.append(ss)
        groups[ss].append({
            "business_number": str(r.get("business_number") or ""),
            "source_system": (r.get("source_system") or "").strip(),
            "business_flow": (r.get("business_flow") or "").strip(),
            "aim_system": (r.get("aim_system") or "").strip(),
            "change_type": (r.get("change_type") or "").strip(),
            "change_describe": (r.get("change_describe") or "").strip(),
        })
    return json.dumps(
        [{"subSystem": ss, "波及组件": groups[ss]} for ss in order],
        ensure_ascii=False,
    )


def _format_affected_modules(rows) -> str:
    """波及模块：JSON 数组，每条 6 字段 dict。

    输出形如:
      [{"sender":"X","receiver":"Y","business_flow":"Z","output_strategy":"A",
        "change_type":"B","remarks":"C"}, ...]
    """
    if not rows:
        return json.dumps([], ensure_ascii=False)
    items = []
    for r in rows:
        items.append({
            "sender": (r.get("sender") or "").strip(),
            "receiver": (r.get("receiver") or "").strip(),
            "business_flow": (r.get("business_flow") or "").strip(),
            "output_strategy": (r.get("output_strategy") or "").strip(),
            "change_type": (r.get("change_type") or "").strip(),
            "remarks": (r.get("remarks") or "").strip(),
        })
    return json.dumps(items, ensure_ascii=False)


class UsecaseExtractor:
    """单个抽取器，搞定全部 10 个字段。"""

    def __init__(self, connector: MySQLConnector):
        self.connector = connector

    def extract(self, gaia_row: dict) -> SysDomainChangeUsecase:
        rdc_number = (gaia_row.get("rdc_number") or "").strip()
        rdc_id = f"[{rdc_number}]"

        rec = SysDomainChangeUsecase(
            rdc_number=rdc_number,
            title=clean_solution_title(gaia_row.get("title") or ""),
            description=(gaia_row.get("description") or ""),
            algorithm=(gaia_row.get("algorithm") or ""),
            implementation=(gaia_row.get("implementation") or ""),
            sub_systems=build_sub_systems_json(gaia_row.get("sub_system") or ""),
        )

        rec.feature_change_analysis = _format_features(
            self.connector.fetch_all(SQL_FEATURE_CHANGE_BY_RDC, (rdc_id,))
        )
        rec.affected_components = _format_affected_components(
            self.connector.fetch_all(SQL_COMPONENT_BY_RDC, (rdc_id,))
        )
        rec.affected_modules = _format_affected_modules(
            self.connector.fetch_all(SQL_MODULE_BY_RDC, (rdc_id,))
        )
        rec.change_points = _format_change_points(
            self.connector.fetch_all(SQL_CHANGE_POINTS_BY_RDC, (rdc_id,))
        )

        log.debug("UsecaseExtractor 完成 {}", rdc_number)
        return rec
