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
    print("🗂️  观星地点查找器 - 缓存配置演示")
    print("=" * 60)
    
    # 1. 显示当前缓存配置信息
    print("\n📊 当前缓存配置信息:")
    print("-" * 40)
    cache_info = get_cache_info()
    print(f"缓存根目录: {cache_info['cache_root']}")
    print(f"总大小: {cache_info['total_size']}")
    
    print("\n📁 缓存子目录:")
    for cache_type, details in cache_info['subdirs'].items():
        status = "✅" if details['exists'] else "❌"
        print(f"  {status} {cache_type.ljust(15)}: {details['path']} ({details['size']})")
    
    # 2. 设置OSMnx缓存
    print("\n🗺️  设置OSMnx缓存:")
    print("-" * 40)
    setup_osmnx_cache()
    
    # 3. 演示获取不同类型的缓存目录
    print("\n📂 缓存目录获取演示:")
    print("-" * 40)
    cache_types = ['images', 'road_networks', 'osmnx', 'temp', 'default']
    for cache_type in cache_types:
        cache_dir = get_cache_dir(cache_type)
        print(f"  {cache_type.ljust(15)}: {cache_dir}")
    
    # 4. 演示临时文件创建
    print("\n📄 临时文件创建演示:")
    print("-" * 40)
    temp_files = [
        get_temp_file(suffix='.json', prefix='demo_data_'),
        get_temp_file(suffix='.txt', prefix='demo_log_'),
        get_temp_file(suffix='.pkl', prefix='demo_cache_')
    ]
    
    for i, temp_file in enumerate(temp_files, 1):
        print(f"  临时文件 {i}: {temp_file}")
        # 创建一些示例内容
        with open(temp_file, 'w') as f:
            f.write(f"这是演示临时文件 {i} 的内容\n")
    
    # 5. 再次显示缓存信息（应该有变化）
    print("\n📊 创建临时文件后的缓存信息:")
    print("-" * 40)
    updated_cache_info = get_cache_info()
    print(f"总大小: {updated_cache_info['total_size']}")
    temp_info = updated_cache_info['subdirs']['temp']
    print(f"临时文件缓存: {temp_info['size']}")
    
    # 6. 缓存清理演示
    print("\n🧹 缓存清理演示:")
    print("-" * 40)
    
    # 询问用户是否要清理缓存
    user_input = input("是否要清理临时缓存？(y/N): ").strip().lower()
    if user_input in ['y', 'yes']:
        clear_cache('temp')
        
        # 显示清理后的信息
        final_cache_info = get_cache_info()
        temp_info_after = final_cache_info['subdirs']['temp']
        print(f"清理后临时文件缓存: {temp_info_after['size']}")
    else:
        print("跳过缓存清理")
    
    print("\n✨ 缓存配置演示完成！")
    print("\n💡 使用提示:")
    print("  - 所有缓存文件现在都存储在项目根目录的 'cache' 文件夹中")
    print("  - OSMnx 的地图数据缓存在 'cache/osmnx' 目录")
    print("  - 图像缓存存储在 'cache/images' 目录")
    print("  - 道路网络缓存存储在 'cache/road_networks' 目录")
    print("  - 临时文件存储在 'cache/temp' 目录")
    print("  - 可以使用 clear_cache() 函数清理特定类型的缓存")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 演示已取消")
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()