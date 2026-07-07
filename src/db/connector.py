"""MySQL 连接管理：基于 DBUtils 的连接池。"""
from contextlib import contextmanager
from typing import Any, Iterable, List, Optional

import pymysql
from dbutils.pooled_db import PooledDB

from config.db_config import DBConfig
from src.utils.logger import get_logger

log = get_logger(__name__)


class MySQLConnector:
    """MySQL 连接池封装。"""

    def __init__(self, config: DBConfig, mincached: int = 2, maxcached: int = 5):
        self.config = config
        self._pool = PooledDB(
            creator=pymysql,
            mincached=mincached,
            maxcached=maxcached,
            maxconnections=10,
            blocking=True,
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            database=config.database,
            charset=config.charset,
            cursorclass=pymysql.cursors.DictCursor,
        )

    @contextmanager
    def _conn(self):
        connection = self._pool.connection()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def fetch_all(self, sql: str, params: Optional[Iterable[Any]] = None) -> List[dict]:
        with self._conn() as c, c.cursor() as cur:
            if params:
                cur.execute(sql, tuple(params))
            else:
                cur.execute(sql)
            return list(cur.fetchall())

    def fetch_one(self, sql: str, params: Optional[Iterable[Any]] = None) -> Optional[dict]:
        with self._conn() as c, c.cursor() as cur:
            if params:
                cur.execute(sql, tuple(params))
            else:
                cur.execute(sql)
            return cur.fetchone()

    def execute(self, sql: str, params: Optional[Iterable[Any]] = None) -> int:
        """执行单条写 SQL，返回受影响行数。"""
        with self._conn() as c, c.cursor() as cur:
            if params:
                return cur.execute(sql, tuple(params))
            return cur.execute(sql)

    def execute_many(self, sql: str, params_list: List[Iterable[Any]]) -> int:
        """批量执行，返回总受影响行数。"""
        if not params_list:
            return 0
        with self._conn() as c, c.cursor() as cur:
            return cur.executemany(sql, [tuple(p) for p in params_list])

    def test_connection(self) -> bool:
        try:
            self.fetch_one("SELECT 1 AS ok")
            log.info("DB 连接正常: {}@{}:{}/{}", self.config.user, self.config.host,
                     self.config.port, self.config.database)
            return True
        except Exception as e:
            log.error("DB 连接失败: {}", e)
            return False