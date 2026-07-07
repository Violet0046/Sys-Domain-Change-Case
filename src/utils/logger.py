"""统一日志配置。"""
import sys
from loguru import logger


def get_logger(name: str):
    """为每个模块返回带模块名的 logger，并保证只配置一次。"""
    if not getattr(logger, "_sys_domain_configured", False):
        logger.remove()
        logger.add(
            sys.stderr,
            level="INFO",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level:<7}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                   "<level>{message}</level>",
        )
        logger.add(
            "output/run.log",
            level="DEBUG",
            rotation="10 MB",
            retention="7 days",
            encoding="utf-8",
        )
        logger._sys_domain_configured = True  # type: ignore[attr-defined]
    return logger.bind(module=name)