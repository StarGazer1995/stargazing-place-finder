# -*- coding: utf-8 -*-
"""
GIS 服务统一配置模块
"""

import json
import os
from typing import Any, Dict, Optional


def load_db_config(path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    从文件路径（JSON 或 TOML）加载数据库配置。

    Args:
        path: 配置文件路径。为 None 时尝试从 DB_CONFIG_PATH 环境变量读取。

    Returns:
        配置字典，如无可返回 None。
    """
    cfg_path = path or os.environ.get('DB_CONFIG_PATH')
    if not cfg_path or not os.path.exists(cfg_path):
        return None

    ext = os.path.splitext(cfg_path)[1].lower()
    if ext in ('.json', ''):
        with open(cfg_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    elif ext == '.toml':
        try:
            import tomllib  # Python 3.11+
            with open(cfg_path, 'rb') as f:
                return tomllib.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to parse TOML config: {e}")
    else:
        raise ValueError(f"Unsupported config format: {ext}")
