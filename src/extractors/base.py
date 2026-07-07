"""抽取器抽象基类。"""
from abc import ABC, abstractmethod

from src.db.connector import MySQLConnector
from src.models.sys_domain_change_usecase import SysDomainChangeBundle


class BaseExtractor(ABC):
    """所有 extractor 的父类。

    子类实现 extract()，接收一个 bundle 和 connector，返回填充后的 bundle。
    抽取器不负责记录之间的聚合，只负责把数据塞进 bundle。
    """

    @abstractmethod
    def extract(self, bundle: SysDomainChangeBundle, connector: MySQLConnector) -> SysDomainChangeBundle:
        ...