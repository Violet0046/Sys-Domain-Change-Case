"""单元测试：清洗 + 抽取器（mock DB）。"""
import json

import pytest

from src.extractors.usecase_extractor import (
    _format_features, _format_change_points,
    _format_affected_components, _format_affected_modules,
)
from src.utils.text_clean import clean_solution_title, sanitize_for_excel


# ---------- text_clean ----------
class TestCleanSolutionTitle:
    def test_remove_gaia_suffix(self):
        s = "[RAN-6911556][【阿联酋】SSB 功率boosting基站侧配置（无信令影响）]-盖亚创建"
        assert clean_solution_title(s) == "[RAN-6911556][【阿联酋】SSB 功率boosting基站侧配置（无信令影响）]"

    def test_strips_brackets_keeps_body(self):
        # 注意：清理只去 -盖亚创建，方括号保留（这是新设计）
        assert "[RAN-X]" in clean_solution_title("[RAN-X]标题-盖亚创建")

    def test_empty(self):
        assert clean_solution_title("") == ""
        assert clean_solution_title(None) == ""


# ---------- sanitize_for_excel ----------
class TestSanitizeForExcel:
    def test_none(self):
        assert sanitize_for_excel(None) == ""

    def test_strip_null(self):
        assert sanitize_for_excel("a\x00b") == "ab"

    def test_keeps_newlines(self):
        assert sanitize_for_excel("a\nb") == "a\nb"


# ---------- 4 个格式化函数 ----------
class TestFormatFeatures:
    def test_empty(self):
        assert json.loads(_format_features([])) == []

    def test_one_row(self):
        rows = [{
            "feature_name": "F1", "feature_change_type": "新增",
            "usecase_name": "U1", "usecase_change_type": "修改",
            "change_point": "P1",
        }]
        result = json.loads(_format_features(rows))
        assert result == [{
            "feature_name": "F1", "feature_change_type": "新增",
            "usecase_name": "U1", "usecase_change_type": "修改",
            "change_point": "P1",
        }]


class TestFormatChangePoints:
    def test_empty(self):
        assert json.loads(_format_change_points([])) == []

    def test_grouped_by_sub(self):
        rows = [
            {"sub_system_name": "SPA", "system_change_describe": "d1"},
            {"sub_system_name": "SPA", "system_change_describe": "d2"},
            {"sub_system_name": "PHY", "system_change_describe": "d3"},
        ]
        result = json.loads(_format_change_points(rows))
        assert len(result) == 3
        assert sum(1 for x in result if x["sub_system"] == "SPA") == 2


class TestFormatAffectedComponents:
    def test_empty(self):
        assert json.loads(_format_affected_components([])) == []

    def test_grouped_by_subsystem(self):
        rows = [
            {"sub_system": "SPA", "business_number": "1", "source_system": "HUC",
             "business_flow": "F1", "aim_system": "MCC",
             "change_type": "新增", "change_describe": "D1"},
            {"sub_system": "SPA", "business_number": "2", "source_system": "MCC",
             "business_flow": "F2", "aim_system": "UPA",
             "change_type": "修改", "change_describe": "D2"},
            {"sub_system": "PHY", "business_number": "1", "source_system": "PHY",
             "business_flow": "F3", "aim_system": "UE",
             "change_type": "继承", "change_describe": "D3"},
        ]
        result = json.loads(_format_affected_components(rows))
        assert len(result) == 2  # SPA + PHY
        spa = next(x for x in result if x["subSystem"] == "SPA")
        assert len(spa["波及组件"]) == 2
        assert spa["波及组件"][0]["source_system"] == "HUC"


class TestFormatAffectedModules:
    def test_empty_returns_empty_json_array(self):
        import json
        assert json.loads(_format_affected_modules([])) == []

    def test_two_rows_produce_json_list(self):
        import json
        rows = [
            {"sender": "S1", "receiver": "R1", "business_flow": "BF1",
             "output_strategy": "OS1", "change_type": "CT1", "remarks": "RM1"},
            {"sender": "S2", "receiver": "R2", "business_flow": "BF2",
             "output_strategy": "OS2", "change_type": "CT2", "remarks": "RM2"},
        ]
        items = json.loads(_format_affected_modules(rows))
        assert len(items) == 2
        assert items[0] == {
            "sender": "S1", "receiver": "R1", "business_flow": "BF1",
            "output_strategy": "OS1", "change_type": "CT1", "remarks": "RM1",
        }


# ---------- SQL_DRIVER_BASE 不返回空 rdc_number ----------
def test_driver_query_filters_empty():
    from src.db.queries import SQL_DRIVER_BASE
    assert "rdc_number != ''" in SQL_DRIVER_BASE or '""' in SQL_DRIVER_BASE
