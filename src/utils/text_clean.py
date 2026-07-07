"""文本清洗工具。"""
import re


def clean_solution_title(title: str) -> str:
    """去除 feature_sub_system_gaia.title 末尾的 '-盖亚创建'。

    示例：
        '[RAN-6911556][【阿联酋】SSB 功率boosting基站侧配置（无信令影响）]-盖亚创建'
        → '[RAN-6911556][【阿联酋】SSB 功率boosting基站侧配置（无信令影响）]'
    """
    if not title:
        return ""
    return re.sub(r"-盖亚创建\s*$", "", title).strip()


# 找出哪些字符是 ASCII 0-31 范围里的（非\t\n\r），做个 frozenset 快速查
_ILLEGAL_CHAR_SET = frozenset(chr(i) for i in range(32) if i not in (9, 10, 13))


def sanitize_for_excel(value) -> str:
    """清除 Excel 不允许的控制字符，保留 \\t \\n \\r。

    99% 字符串走快速路径（set 查找），无控制字符时直接返回原值。
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    if not any(c in _ILLEGAL_CHAR_SET for c in value):
        return value
    return "".join(c for c in value if c not in _ILLEGAL_CHAR_SET)
