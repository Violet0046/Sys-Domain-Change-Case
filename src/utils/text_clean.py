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


def is_blank(value) -> bool:
    """判断值是否为空/全空白。"""
    return value is None or (isinstance(value, str) and not value.strip())


# openpyxl / Excel 不允许的控制字符（ASCII 0x00-0x08、0x0B、0x0C、0x0E-0x1F）
# 允许：\t (0x09), \n (0x0A), \r (0x0D)
_ILLEGAL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def sanitize_for_excel(value) -> str:
    """清除 Excel 不允许的控制字符，保留 \\t \\n \\r。

    - None → ""
    - 非字符串 → str(value)
    - 字符串 → 去除非法控制字符
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return _ILLEGAL_CHARS_RE.sub("", value)