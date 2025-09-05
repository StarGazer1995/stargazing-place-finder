#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存配置演示脚本
展示如何使用统一的缓存配置管理项目中的所有缓存
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from cache_config import (
    get_cache_info, 
    clear_cache, 
    setup_osmnx_cache,
    get_cache_dir,
    get_temp_file
)

def main():
    """
    缓存配置演示主函数
    """
    print("🗂️  Star Gazing Location Finder - Cache Configuration Demo")
    print("=" * 60)
    
    # 1. 显示当前缓存配置信息
    print("\n📊 Current cache configuration info:")
    print("-" * 40)
    cache_info = get_cache_info()
    print(f"Cache root directory: {cache_info['cache_root']}")
    print(f"Total size: {cache_info['total_size']}")
    
    print("\n📁 Cache subdirectories:")
    for cache_type, details in cache_info['subdirs'].items():
        status = "✅" if details['exists'] else "❌"
        print(f"  {status} {cache_type.ljust(15)}: {details['path']} ({details['size']})")
    
    # 2. 设置OSMnx缓存
    print("\n🗺️  Setting up OSMnx cache:")
    print("-" * 40)
    setup_osmnx_cache()
    
    # 3. 演示获取不同类型的缓存目录
    print("\n📂 Cache directory retrieval demo:")
    print("-" * 40)
    cache_types = ['images', 'road_networks', 'osmnx', 'temp', 'default']
    for cache_type in cache_types:
        cache_dir = get_cache_dir(cache_type)
        print(f"  {cache_type.ljust(15)}: {cache_dir}")
    
    # 4. 演示临时文件创建
    print("\n📄 Temporary file creation demo:")
    print("-" * 40)
    temp_files = [
        get_temp_file(suffix='.json', prefix='demo_data_'),
        get_temp_file(suffix='.txt', prefix='demo_log_'),
        get_temp_file(suffix='.pkl', prefix='demo_cache_')
    ]
    
    for i, temp_file in enumerate(temp_files, 1):
        print(f"  Temporary file {i}: {temp_file}")
        # 创建一些示例内容
        with open(temp_file, 'w') as f:
            f.write(f"This is the content of demo temporary file {i}\n")
    
    # 5. 再次显示缓存信息（应该有变化）
    print("\n📊 Cache info after creating temporary files:")
    print("-" * 40)
    updated_cache_info = get_cache_info()
    print(f"Total size: {updated_cache_info['total_size']}")
    temp_info = updated_cache_info['subdirs']['temp']
    print(f"Temporary file cache: {temp_info['size']}")
    
    # 6. 缓存清理演示
    print("\n🧹 Cache cleanup demo:")
    print("-" * 40)
    
    # 询问用户是否要清理缓存
    user_input = input("Do you want to clear temporary cache? (y/N): ").strip().lower()
    if user_input in ['y', 'yes']:
        clear_cache('temp')
        
        # 显示清理后的信息
        final_cache_info = get_cache_info()
        temp_info_after = final_cache_info['subdirs']['temp']
        print(f"Temporary file cache after cleanup: {temp_info_after['size']}")
    else:
        print("Skipping cache cleanup")
    
    print("\n✨ Cache configuration demo completed!")
    print("\n💡 Usage tips:")
    print("  - All cache files are now stored in the 'cache' folder in the project root directory")
    print("  - OSMnx map data is cached in the 'cache/osmnx' directory")
    print("  - Image cache is stored in the 'cache/images' directory")
    print("  - Road network cache is stored in the 'cache/road_networks' directory")
    print("  - Temporary files are stored in the 'cache/temp' directory")
    print("  - You can use the clear_cache() function to clean specific types of cache")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Demo cancelled")
    except Exception as e:
        print(f"\n❌ Error occurred during demo: {e}")
        import traceback
        traceback.print_exc()