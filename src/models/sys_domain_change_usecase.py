"""输出数据模型。

新结构（方案 B）：
  SysDomainChangeBundle —— 一个 rdc_id 下的全部数据
    ├── main: SysDomainChangeUsecase              # 主表：1 个 rdc_id 只产生 1 行
    │     └── 子系统列（joined string）记录所有涉及的 sub_system
    ├── subsystems: List[SubsystemRecord]         # 子系表：(rdc_id, sub_system) 列表
    │     └── 每个 sub_system 含 change_points
    ├── components: List[ComponentRecord]        # 组件子表
    └── modules:    List[ModuleRecord]           # 模块子表
"""
from dataclasses import dataclass, field
from typing import List


# ---------- 主表 ----------
@dataclass
class SysDomainChangeUsecase:
    """主表的 1 行（与 rdc_id 一一对应）。

    rdc_number 不再单独存储：它等价于 rdc_id 去括号，可由 rdc_id 派生。
    """
    rdc_id: str
    sub_system: str = ""            # 所有涉及子系，`\n` 分隔
    solution: str = ""
    feature_change_analysis: str = ""
    requirement: str = ""
    algorithm: str = ""
    implementation: str = ""


# ---------- 子系表 ----------
@dataclass
class SubsystemRecord:
    """(rdc_id, sub_system) 子表的一行。"""
    rdc_id: str
    sub_system: str
    change_points: List[str] = field(default_factory=list)


# ---------- 子表：组件 ----------
@dataclass
class ComponentRecord:
    rdc_id: str
    sub_system: str
    business_flow: str = ""
    source_system: str = ""
    aim_system: str = ""
    change_type: str = ""
    change_describe: str = ""


# ---------- 子表：模块 ----------
@dataclass
class ModuleRecord:
    rdc_id: str
    sub_system: str
    sender: str = ""
    receiver: str = ""
    business_flow: str = ""
    output_strategy: str = ""
    change_type: str = ""
    remarks: str = ""


# ---------- 聚合根 ----------
@dataclass
class SysDomainChangeBundle:
    """一个 rdc_id 对应的全部输出数据。"""
    rdc_id: str
    main: SysDomainChangeUsecase = None  # type: ignore[assignment]
    subsystems: List[SubsystemRecord] = field(default_factory=list)
    components: List[ComponentRecord] = field(default_factory=list)
    modules: List[ModuleRecord] = field(default_factory=list)
