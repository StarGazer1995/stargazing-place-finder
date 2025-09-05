#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cache Configuration Module
Unified management of all cache storage locations in the project
"""

import os
import tempfile
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# Cache root directory - set to cache folder under project root
CACHE_ROOT = PROJECT_ROOT / "cache"

# Ensure cache directory exists
CACHE_ROOT.mkdir(exist_ok=True)

# Various cache subdirectories
IMAGE_CACHE_DIR = CACHE_ROOT / "images"
ROAD_NETWORK_CACHE_DIR = CACHE_ROOT / "road_networks"
OSMNX_CACHE_DIR = CACHE_ROOT / "osmnx"
TEMP_CACHE_DIR = CACHE_ROOT / "temp"

# Create all cache subdirectories
for cache_dir in [IMAGE_CACHE_DIR, ROAD_NETWORK_CACHE_DIR, OSMNX_CACHE_DIR, TEMP_CACHE_DIR]:
    cache_dir.mkdir(exist_ok=True)

def get_cache_dir(cache_type: str = "default") -> Path:
    """
    Get cache directory for specified type
    
    Args:
        cache_type: Cache type ('images', 'road_networks', 'osmnx', 'temp', 'default')
        
    Returns:
        Path: Cache directory path
    """
    cache_dirs = {
        'images': IMAGE_CACHE_DIR,
        'road_networks': ROAD_NETWORK_CACHE_DIR,
        'osmnx': OSMNX_CACHE_DIR,
        'temp': TEMP_CACHE_DIR,
        'default': CACHE_ROOT
    }
    
    return cache_dirs.get(cache_type, CACHE_ROOT)

def setup_osmnx_cache():
    """
    Configure OSMnx to use project cache directory
    """
    try:
        import osmnx as ox
        # Set OSMnx cache directory
        ox.settings.cache_folder = str(OSMNX_CACHE_DIR)
        ox.settings.use_cache = True
        print(f"✅ OSMnx cache directory set to: {OSMNX_CACHE_DIR}")
    except ImportError:
        print("⚠️  OSMnx not installed, skipping cache configuration")

def get_temp_file(suffix: str = ".tmp", prefix: str = "stargazing_") -> str:
    """
    Create temporary file in project cache directory
    
    Args:
        suffix: File suffix
        prefix: File prefix
        
    Returns:
        str: Temporary file path
    """
    temp_file = tempfile.NamedTemporaryFile(
        suffix=suffix,
        prefix=prefix,
        dir=str(TEMP_CACHE_DIR),
        delete=False
    )
    temp_file.close()
    return temp_file.name

def clear_cache(cache_type: str = "all"):
    """
    Clear cache of specified type
    
    Args:
        cache_type: Cache type to clear ('images', 'road_networks', 'osmnx', 'temp', 'all')
    """
    import shutil
    
    if cache_type == "all":
        # Clear all cache
        if CACHE_ROOT.exists():
            shutil.rmtree(CACHE_ROOT)
            CACHE_ROOT.mkdir(exist_ok=True)
            # Recreate subdirectories
            for cache_dir in [IMAGE_CACHE_DIR, ROAD_NETWORK_CACHE_DIR, OSMNX_CACHE_DIR, TEMP_CACHE_DIR]:
                cache_dir.mkdir(exist_ok=True)
            print(f"✅ All cache cleared: {CACHE_ROOT}")
    else:
        # Clear specified type cache
        cache_dir = get_cache_dir(cache_type)
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            cache_dir.mkdir(exist_ok=True)
            print(f"✅ {cache_type} cache cleared: {cache_dir}")

def get_cache_info() -> dict:
    """
    Get cache information
    
    Returns:
        dict: Cache information dictionary
    """
    def get_dir_size(path: Path) -> int:
        """Calculate directory size (bytes)"""
        total_size = 0
        if path.exists():
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        return total_size
    
    def format_size(size_bytes: int) -> str:
        """Format file size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    cache_info = {
        'cache_root': str(CACHE_ROOT),
        'total_size': format_size(get_dir_size(CACHE_ROOT)),
        'subdirs': {}
    }
    
    for cache_type, cache_dir in [
        ('images', IMAGE_CACHE_DIR),
        ('road_networks', ROAD_NETWORK_CACHE_DIR),
        ('osmnx', OSMNX_CACHE_DIR),
        ('temp', TEMP_CACHE_DIR)
    ]:
        cache_info['subdirs'][cache_type] = {
            'path': str(cache_dir),
            'size': format_size(get_dir_size(cache_dir)),
            'exists': cache_dir.exists()
        }
    
    return cache_info

if __name__ == "__main__":
    # Initialize cache configuration
    setup_osmnx_cache()
    
    # Display cache information
    print("\n📁 Cache Configuration Information:")
    print("=" * 50)
    info = get_cache_info()
    print(f"Cache root directory: {info['cache_root']}")
    print(f"Total size: {info['total_size']}")
    print("\nSubdirectories:")
    for cache_type, details in info['subdirs'].items():
        status = "✅" if details['exists'] else "❌"
        print(f"  {status} {cache_type}: {details['path']} ({details['size']})")