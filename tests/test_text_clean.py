"""单元测试：工具与抽取器（mock DB）。"""
import pytest

from src.extractors.gaia_base_extractor import GaiaBaseExtractor
from src.extractors.module_extractor import ModuleExtractor
from src.extractors.subsystem_change_extractor import SubsystemChangeExtractor
from src.models.sys_domain_change_usecase import (
    SysDomainChangeBundle, SysDomainChangeUsecase,
)
from src.utils.text_clean import clean_solution_title, sanitize_for_excel


# ---------- text_clean ----------
class TestCleanSolutionTitle:
    def test_remove_gaia_suffix(self):
        s = "[RAN-6911556][【阿联酋】SSB 功率boosting基站侧配置（无信令影响）]-盖亚创建"
        assert clean_solution_title(s) == "[RAN-6911556][【阿联酋】SSB 功率boosting基站侧配置（无信令影响）]"

    def test_no_suffix(self):
        s = "[RAN-6911556]foo"
        assert clean_solution_title(s) == "[RAN-6911556]foo"

    def test_with_trailing_whitespace(self):
        s = "标题-盖亚创建  "
        assert clean_solution_title(s) == "标题"

    def test_empty(self):
        assert clean_solution_title("") == ""
        assert clean_solution_title(None) == ""  # type: ignore[arg-type]


# ---------- sanitize_for_excel ----------
class TestSanitizeForExcel:
    def test_none_becomes_empty(self):
        assert sanitize_for_excel(None) == ""

    def test_normal_text_unchanged(self):
        assert sanitize_for_excel("正常文本 ABC 123") == "正常文本 ABC 123"

    def test_strip_null_bytes(self):
        assert sanitize_for_excel("a\x00b") == "ab"

    def test_strip_other_control_chars(self):
        bad = "".join(chr(i) for i in range(32))
        cleaned = sanitize_for_excel(bad)
        assert cleaned == "\t\n\r"

    def test_keeps_newline_and_tab(self):
        assert sanitize_for_excel("a\nb\tc") == "a\nb\tc"

    def test_non_string_converted(self):
        assert sanitize_for_excel(123) == "123"
        assert sanitize_for_excel(True) == "True"

    def test_real_world_can_bus_content(self):
        s = "B28~24\n\x00控制域\nSUM=(T+W0)%256"
        cleaned = sanitize_for_excel(s)
        assert "\x00" not in cleaned
        assert "\n" in cleaned
        assert "%" in cleaned


# ---------- SubsystemChangeExtractor ----------
def _empty_bundle():
    return SysDomainChangeBundle(
        rdc_id="X",
        main=SysDomainChangeUsecase(rdc_id="X"),
    )


class TestSubsystemChangeExtractor:
    def test_no_rows_sets_empty_sub_system(self, mocker):
        connector = mocker.Mock()
        connector.fetch_all.return_value = []
        b = _empty_bundle()
        b = SubsystemChangeExtractor().extract(b, connector)
        assert len(b.subsystems) == 0
        assert b.main.sub_system == ""

    def test_two_subsystems_split(self, mocker):
        fake_rows = [
            {"sub_system_name": "SPA", "system_change_describe": "变更点A"},
            {"sub_system_name": "SPA", "system_change_describe": "变更点B"},
            {"sub_system_name": "MAC", "system_change_describe": "变更点C"},
        ]
        connector = mocker.Mock()
        connector.fetch_all.return_value = fake_rows

        b = _empty_bundle()
        b = SubsystemChangeExtractor().extract(b, connector)

        assert len(b.subsystems) == 2
        assert b.main.sub_system == "SPA\nMAC"
        spa = next(s for s in b.subsystems if s.sub_system == "SPA")
        mac = next(s for s in b.subsystems if s.sub_system == "MAC")
        assert spa.change_points == ["变更点A", "变更点B"]
        assert mac.change_points == ["变更点C"]


# ---------- ModuleExtractor 不去重（数据原样保留）----------
class TestModuleExtractorNoDedup:
    def test_extract_appends_all_rows_verbatim(self, mocker):
        """源表 3 行 → 输出 3 行，每个 business_flow 单独保留。"""
        connector = mocker.Mock()
        connector.fetch_all.return_value = [
            {"sub_system": "SPA", "sender": "RAC", "receiver": "MCC_L1模块",
             "business_flow": "reserved379", "output_strategy": "RAC_L1模块",
             "change_type": "修改", "remarks": ""},
            {"sub_system": "SPA", "sender": "RAC", "receiver": "MCC_L1模块",
             "business_flow": "reserved966", "output_strategy": "RAC_L1模块",
             "change_type": "修改", "remarks": ""},
            {"sub_system": "SPA", "sender": "PHY", "receiver": "RAC",
             "business_flow": "bf3", "output_strategy": "os3",
             "change_type": "ct3", "remarks": "rm3"},
        ]
        # 用真实流水线的一环：bundle 含一个 subsystem=SPA
        b = SysDomainChangeBundle(
            rdc_id="X",
            main=SysDomainChangeUsecase(rdc_id="X"),
        )
        from src.models.sys_domain_change_usecase import SubsystemRecord
        b.subsystems.append(SubsystemRecord(rdc_id="X", sub_system="SPA"))

        b = ModuleExtractor().extract(b, connector)
        assert len(b.modules) == 3
        flows = [m.business_flow for m in b.modules]
        assert flows == ["reserved379", "reserved966", "bf3"]


# ---------- GaiaBaseExtractor ----------
class TestGaiaBaseExtractor:
    def test_fills_main(self, mocker):
        connector = mocker.Mock()
        connector.fetch_one.return_value = {
            "rdc_id": "X",  # SELECT 现在已不含 rdc_id
            "rdc_number": "RAN-1",
            "title": "[RAN-1]示例-盖亚创建",
            "description": "需求",
            "algorithm": "算法",
            "implementation": "实现",
        }
        b = _empty_bundle()
        b = GaiaBaseExtractor().extract(b, connector)
        assert b.main.solution == "[RAN-1]示例"
        assert b.main.requirement == "需求"
        assert b.main.algorithm == "算法"

    def test_missing_row_does_not_modify(self, mocker):
        connector = mocker.Mock()
        connector.fetch_one.return_value = None
        b = _empty_bundle()
        b = GaiaBaseExtractor().extract(b, connector)
        assert b.main.solution == ""
