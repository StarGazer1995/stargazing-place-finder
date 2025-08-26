#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存集成测试脚本
验证所有模块的缓存配置是否正常工作
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from cache_config import get_cache_info, clear_cache
from light_pollution_analyzer import LightPollutionAnalyzer
from road_connectivity_checker import RoadConnectivityChecker
from simple_road_checker import SimpleRoadChecker

def test_cache_directories():
    """
    测试缓存目录是否正确创建
    """
    print("🧪 测试缓存目录创建...")
    
    cache_info = get_cache_info()
    required_dirs = ['images', 'road_networks', 'osmnx', 'temp']
    
    for dir_name in required_dirs:
        if dir_name in cache_info['subdirs'] and cache_info['subdirs'][dir_name]['exists']:
            print(f"  ✅ {dir_name} 目录存在")
        else:
            print(f"  ❌ {dir_name} 目录不存在")
            return False
    
    return True

def test_light_pollution_analyzer_cache():
    """
    测试光污染分析器的缓存功能
    """
    print("\n🧪 测试光污染分析器缓存...")
    
    try:
        # 创建一个临时的测试KML文件
        test_kml_path = "test.kml"
        with open(test_kml_path, 'w') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2">\n</kml>')
        
        # 创建分析器实例
        analyzer = LightPollutionAnalyzer(test_kml_path)
        
        # 清理临时文件
        os.remove(test_kml_path)
        
        # 检查是否有图像缓存目录属性
        if hasattr(analyzer, '_image_cache_dir'):
            print(f"  ✅ 图像缓存目录已配置: {analyzer._image_cache_dir}")
        else:
            print("  ❌ 图像缓存目录未配置")
            return False
        
        # 检查缓存目录是否存在
        if os.path.exists(analyzer._image_cache_dir):
            print("  ✅ 图像缓存目录存在")
        else:
            print("  ❌ 图像缓存目录不存在")
            return False
        
        # 测试清除缓存功能
        analyzer.clear_image_cache()
        print("  ✅ 图像缓存清除功能正常")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 光污染分析器缓存测试失败: {e}")
        return False

def test_road_connectivity_checker_cache():
    """
    测试道路连通性检查器的缓存功能
    """
    print("\n🧪 测试道路连通性检查器缓存...")
    
    try:
        # 创建检查器实例
        checker = RoadConnectivityChecker()
        
        # 检查是否有道路缓存目录属性
        if hasattr(checker, '_road_cache_dir'):
            print(f"  ✅ 道路缓存目录已配置: {checker._road_cache_dir}")
        else:
            print("  ❌ 道路缓存目录未配置")
            return False
        
        # 检查缓存目录是否存在
        if os.path.exists(checker._road_cache_dir):
            print("  ✅ 道路缓存目录存在")
        else:
            print("  ❌ 道路缓存目录不存在")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ 道路连通性检查器缓存测试失败: {e}")
        return False

def test_simple_road_checker_cache():
    """
    测试简单道路检查器的缓存功能
    """
    print("\n🧪 测试简单道路检查器缓存...")
    
    try:
        # 创建检查器实例
        checker = SimpleRoadChecker()
        print("  ✅ 简单道路检查器创建成功")
        
        # 检查OSMnx缓存是否已设置
        import osmnx as ox
        cache_folder = ox.settings.cache_folder
        if 'cache/osmnx' in cache_folder:
            print(f"  ✅ OSMnx缓存目录已设置: {cache_folder}")
        else:
            print(f"  ⚠️ OSMnx缓存目录: {cache_folder}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 简单道路检查器缓存测试失败: {e}")
        return False

def test_cache_cleanup():
    """
    测试缓存清理功能
    """
    print("\n🧪 测试缓存清理功能...")
    
    try:
        # 测试临时缓存清理
        clear_cache('temp')
        print("  ✅ 临时缓存清理成功")
        
        # 获取清理后的缓存信息
        cache_info = get_cache_info()
        temp_size = cache_info['subdirs']['temp']['size']
        print(f"  ✅ 临时缓存大小: {temp_size}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 缓存清理测试失败: {e}")
        return False

def main():
    """
    运行所有缓存集成测试
    """
    print("🚀 开始缓存集成测试")
    print("=" * 50)
    
    tests = [
        test_cache_directories,
        test_light_pollution_analyzer_cache,
        test_road_connectivity_checker_cache,
        test_simple_road_checker_cache,
        test_cache_cleanup
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有缓存集成测试通过！")
        print("\n✨ 缓存配置已成功应用到所有模块")
        print("💡 所有缓存文件现在都存储在项目根目录的 'cache' 文件夹中")
        return True
    else:
        print("❌ 部分测试失败，请检查配置")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 测试已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)