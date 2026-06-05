"""Cache management module."""
from .cache_config import (
    CACHE_ROOT,
    IMAGE_CACHE_DIR,
    ROAD_NETWORK_CACHE_DIR,
    OSMNX_CACHE_DIR,
    TEMP_CACHE_DIR,
    get_cache_dir,
    setup_osmnx_cache,
    get_temp_file,
    clear_cache,
    get_cache_info,
)