"""输出数据模型（单表架构）。

一行 = 一个 rdc_number。
所有列表型/子表型内容用 JSON 或 \n|\n 分隔字符串存于一个 TEXT 列。
"""
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class SysDomainChangeUsecase:
    """单行记录 = 一个方案的所有字段。"""
    rdc_number: str
    title: str = ""                          # 方案（清洗后）
    feature_change_analysis: str = ""        # 子表 JSON（特性域变更分析）
    description: str = ""                    # 需求描述
    algorithm: str = ""                      # 算法描述
    implementation: str = ""                 # 实现思路
    sub_systems: str = ""                    # 波及子系统（JSON 数组 ["a","b"]）
    affected_components: str = ""            # 波及组件（大 JSON 对象）
    affected_modules: str = ""               # 波及模块（\n|\n 多行多列文本）
    change_points: str = ""                  # 波及的变更点（JSON 子表格式）
