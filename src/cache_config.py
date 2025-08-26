#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存配置模块
统一管理项目中所有缓存的存储位置
"""

import os
import tempfile
from pathlib import Path

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# 缓存根目录 - 设置为项目根目录下的cache文件夹
CACHE_ROOT = PROJECT_ROOT / "cache"

# 确保缓存目录存在
CACHE_ROOT.mkdir(exist_ok=True)

# 各种缓存子目录
IMAGE_CACHE_DIR = CACHE_ROOT / "images"
ROAD_NETWORK_CACHE_DIR = CACHE_ROOT / "road_networks"
OSMNX_CACHE_DIR = CACHE_ROOT / "osmnx"
TEMP_CACHE_DIR = CACHE_ROOT / "temp"

# 创建所有缓存子目录
for cache_dir in [IMAGE_CACHE_DIR, ROAD_NETWORK_CACHE_DIR, OSMNX_CACHE_DIR, TEMP_CACHE_DIR]:
    cache_dir.mkdir(exist_ok=True)

def get_cache_dir(cache_type: str = "default") -> Path:
    """
    获取指定类型的缓存目录
    
    Args:
        cache_type: 缓存类型 ('images', 'road_networks', 'osmnx', 'temp', 'default')
        
    Returns:
        Path: 缓存目录路径
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
    配置OSMnx使用项目缓存目录
    """
    try:
        import osmnx as ox
        # 设置OSMnx缓存目录
        ox.settings.cache_folder = str(OSMNX_CACHE_DIR)
        ox.settings.use_cache = True
        print(f"✅ OSMnx缓存目录已设置为: {OSMNX_CACHE_DIR}")
    except ImportError:
        print("⚠️  OSMnx未安装，跳过缓存配置")

def get_temp_file(suffix: str = ".tmp", prefix: str = "stargazing_") -> str:
    """
    在项目缓存目录中创建临时文件
    
    Args:
        suffix: 文件后缀
        prefix: 文件前缀
        
    Returns:
        str: 临时文件路径
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
    清除指定类型的缓存
    
    Args:
        cache_type: 要清除的缓存类型 ('images', 'road_networks', 'osmnx', 'temp', 'all')
    """
    import shutil
    
    if cache_type == "all":
        # 清除所有缓存
        if CACHE_ROOT.exists():
            shutil.rmtree(CACHE_ROOT)
            CACHE_ROOT.mkdir(exist_ok=True)
            # 重新创建子目录
            for cache_dir in [IMAGE_CACHE_DIR, ROAD_NETWORK_CACHE_DIR, OSMNX_CACHE_DIR, TEMP_CACHE_DIR]:
                cache_dir.mkdir(exist_ok=True)
            print(f"✅ 已清除所有缓存: {CACHE_ROOT}")
    else:
        # 清除指定类型的缓存
        cache_dir = get_cache_dir(cache_type)
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            cache_dir.mkdir(exist_ok=True)
            print(f"✅ 已清除{cache_type}缓存: {cache_dir}")

def get_cache_info() -> dict:
    """
    获取缓存信息
    
    Returns:
        dict: 缓存信息字典
    """
    def get_dir_size(path: Path) -> int:
        """计算目录大小（字节）"""
        total_size = 0
        if path.exists():
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        return total_size
    
    def format_size(size_bytes: int) -> str:
        """格式化文件大小"""
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
    # 初始化缓存配置
    setup_osmnx_cache()
    
    # 显示缓存信息
    print("\n📁 缓存配置信息:")
    print("=" * 50)
    info = get_cache_info()
    print(f"缓存根目录: {info['cache_root']}")
    print(f"总大小: {info['total_size']}")
    print("\n子目录:")
    for cache_type, details in info['subdirs'].items():
        status = "✅" if details['exists'] else "❌"
        print(f"  {status} {cache_type}: {details['path']} ({details['size']})")