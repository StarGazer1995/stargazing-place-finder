"""Cache management module."""

from .cache_config import (
    CACHE_ROOT,
    IMAGE_CACHE_DIR,
    OSMNX_CACHE_DIR,
    ROAD_NETWORK_CACHE_DIR,
    TEMP_CACHE_DIR,
    clear_cache,
    get_cache_dir,
    get_cache_info,
    get_temp_file,
    setup_osmnx_cache,
)

__all__ = [
    "CACHE_ROOT",
    "IMAGE_CACHE_DIR",
    "OSMNX_CACHE_DIR",
    "ROAD_NETWORK_CACHE_DIR",
    "TEMP_CACHE_DIR",
    "clear_cache",
    "get_cache_dir",
    "get_cache_info",
    "get_temp_file",
    "setup_osmnx_cache",
]
