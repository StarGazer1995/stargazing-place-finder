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
    print("🧪 Testing cache directory creation...")
    
    cache_info = get_cache_info()
    required_dirs = ['images', 'road_networks', 'osmnx', 'temp']
    
    for dir_name in required_dirs:
        assert dir_name in cache_info['subdirs'], f"{dir_name} directory not found in cache info"
        assert cache_info['subdirs'][dir_name]['exists'], f"{dir_name} directory does not exist"
        print(f"  ✅ {dir_name} directory exists")

def test_light_pollution_analyzer_cache():
    """
    测试光污染分析器的缓存功能
    """
    print("\n🧪 Testing light pollution analyzer cache...")
    
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
        assert hasattr(analyzer, '_image_cache_dir'), "Image cache directory not configured"
        print(f"  ✅ Image cache directory configured: {analyzer._image_cache_dir}")
        
        # 检查缓存目录是否存在
        assert os.path.exists(analyzer._image_cache_dir), "Image cache directory does not exist"
        print("  ✅ Image cache directory exists")
        
        # 测试清除缓存功能
        analyzer.clear_image_cache()
        print("  ✅ Image cache clearing function works normally")
        
    except Exception as e:
        print(f"  ❌ Light pollution analyzer cache test failed: {e}")
        raise

def test_road_connectivity_checker_cache():
    """
    测试道路连通性检查器的缓存功能
    """
    print("\n🧪 Testing road connectivity checker cache...")
    
    try:
        # 创建检查器实例
        checker = RoadConnectivityChecker()
        
        # 检查是否有道路缓存目录属性
        assert hasattr(checker, '_road_cache_dir'), "Road cache directory not configured"
        print(f"  ✅ Road cache directory configured: {checker._road_cache_dir}")
        
        # 检查缓存目录是否存在
        assert os.path.exists(checker._road_cache_dir), "Road cache directory does not exist"
        print("  ✅ Road cache directory exists")
        
    except Exception as e:
        print(f"  ❌ Road connectivity checker cache test failed: {e}")
        raise

def test_simple_road_checker_cache():
    """
    测试简单道路检查器的缓存功能
    """
    print("\n🧪 Testing simple road checker cache...")
    
    try:
        # 创建检查器实例
        checker = SimpleRoadChecker()
        print("  ✅ Simple road checker created successfully")
        
        # 检查OSMnx缓存是否已设置
        import osmnx as ox
        cache_folder = ox.settings.cache_folder
        assert cache_folder is not None, "OSMnx cache directory not set"
        print(f"  ✅ OSMnx cache directory set: {cache_folder}")
        
    except Exception as e:
        print(f"  ❌ Simple road checker cache test failed: {e}")
        raise

def test_cache_cleanup():
    """
    测试缓存清理功能
    """
    print("\n🧪 Testing cache cleanup function...")
    
    try:
        # 测试临时缓存清理
        clear_cache('temp')
        print("  ✅ Temporary cache cleanup successful")
        
        # 获取清理后的缓存信息
        cache_info = get_cache_info()
        assert 'temp' in cache_info['subdirs'], "Temp cache directory not found"
        temp_size = cache_info['subdirs']['temp']['size']
        print(f"  ✅ Temporary cache size: {temp_size}")
        
    except Exception as e:
        print(f"  ❌ Cache cleanup test failed: {e}")
        raise

def main():
    """
    运行所有缓存集成测试
    """
    print("🚀 Starting cache integration test")
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
    print(f"📊 Test results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All cache integration tests passed!")
        print("\n✨ Cache configuration successfully applied to all modules")
        print("💡 All cache files are now stored in the 'cache' folder in the project root directory")
        return True
    else:
        print("❌ Some tests failed, please check configuration")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Test cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error occurred during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)