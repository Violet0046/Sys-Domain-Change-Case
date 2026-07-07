"""数据库配置模板。

使用方法：
  1. 复制本文件：cp db_config.example.py db_config.py
  2. 编辑 db_config.py，填入真实的连接参数
     （或通过环境变量设置，本文件已被 .gitignore 屏蔽）
"""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DBConfig:
    host: str
    user: str
    password: str
    database: str
    port: int
    charset: str

    @classmethod
    def from_env(cls) -> "DBConfig":
        return cls(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "solution_knowledge"),
            port=int(os.getenv("DB_PORT", "3306")),
            charset=os.getenv("DB_CHARSET", "utf8mb4"),
        )


DEFAULT_CONFIG = DBConfig.from_env()
