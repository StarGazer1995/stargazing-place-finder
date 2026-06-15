"""GIS查询服务：统一的地理空间数据查询入口。"""

from .config import load_db_config
from .query_service import GisQueryService

__all__ = [
    "load_db_config",
    "GisQueryService",
]
