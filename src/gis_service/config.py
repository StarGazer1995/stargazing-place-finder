# -*- coding: utf-8 -*-
"""
GIS 服务统一配置模块
"""

import json
import logging
import os
from typing import Dict, Optional

from config import _import_tomllib

logger = logging.getLogger(__name__)

_DB_CONFIG_ENV = "STARGAZING_DB_CONFIG"
_OLD_DB_CONFIG_ENV = "DB_CONFIG_PATH"


def _resolve_db_config_path(path: Optional[str] = None) -> Optional[str]:
    """
    解析数据库配置文件路径。

    优先级:
    1. 显式传入的 path 参数
    2. STARGAZING_DB_CONFIG 环境变量
    3. DB_CONFIG_PATH 环境变量（已废弃，向后兼容）

    Args:
        path: 显式传入的配置路径

    Returns:
        配置文件路径，无可返回 None
    """
    if path:
        return path

    cfg = os.environ.get(_DB_CONFIG_ENV)
    if cfg:
        return cfg

    cfg = os.environ.get(_OLD_DB_CONFIG_ENV)
    if cfg:
        logger.warning("Environment variable DB_CONFIG_PATH is deprecated. Please use STARGAZING_DB_CONFIG instead.")
        return cfg

    return None


def load_db_config(path: Optional[str] = None) -> Optional[Dict[str, object]]:
    """
    从文件路径（JSON 或 TOML）加载数据库配置。

    Args:
        path: 配置文件路径。为 None 时依次尝试 STARGAZING_DB_CONFIG
              和 DB_CONFIG_PATH（已废弃）环境变量。

    Returns:
        配置字典，如无可返回 None。
    """
    cfg_path = _resolve_db_config_path(path)
    if not cfg_path or not os.path.exists(cfg_path):
        return None

    ext = os.path.splitext(cfg_path)[1].lower()
    if ext in (".json", ""):
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f)
    elif ext == ".toml":
        try:
            tomllib = _import_tomllib()

            with open(cfg_path, "rb") as f:
                return tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise RuntimeError(f"Failed to parse TOML config: {e}") from e
    else:
        raise ValueError(f"Unsupported config format: {ext}")
