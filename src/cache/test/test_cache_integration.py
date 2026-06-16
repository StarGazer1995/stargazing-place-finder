#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存集成测试脚本
验证所有模块的缓存配置是否正常工作
"""

import os
import sys
import warnings

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from src.cache.cache_config import clear_cache, get_cache_info
from src.light_pollution.light_pollution_analyzer import LightPollutionAnalyzer
from src.road_connectivity.road_connectivity_checker import RoadConnectivityChecker
from src.road_connectivity.simple_road_checker import SimpleRoadChecker

# 抑制已弃用功能的 DeprecationWarning（向后兼容测试）
warnings.simplefilter("ignore", DeprecationWarning)


def test_cache_directories():
    """
    测试缓存目录是否正确创建
    """
    print("🧪 Testing cache directory creation...")

    cache_info = get_cache_info()
    required_dirs = ["images", "road_networks", "osmnx", "temp"]

    for dir_name in required_dirs:
        assert dir_name in cache_info["subdirs"], f"{dir_name} directory not found in cache info"
        assert cache_info["subdirs"][dir_name]["exists"], f"{dir_name} directory does not exist"
        print(f"  ✅ {dir_name} directory exists")

    return True


def test_light_pollution_analyzer_cache():
    """
    测试光污染分析器的初始化（GeoTIFF 后端）
    """
    print("\n🧪 Testing light pollution analyzer initialization...")

    try:
        # 不传 geotiff_path，测试空初始化（允许后续 init() 加载）
        analyzer = LightPollutionAnalyzer(geotiff_path=None)

        # 检查 GEOTIFF 分析器核心属性
        assert analyzer._geotiff_path is None, "GeoTIFF path should be None when not provided"
        assert analyzer._src is None, "Dataset should be None when not initialized"
        print("  ✅ Analyzer created with geotiff_path=None (lazy init supported)")

        # 测试 close() 在未加载数据集时不会出错
        analyzer.close()
        print("  ✅ close() works normally on uninitialized analyzer")

        return True

    except Exception as e:
        print(f"  ❌ Light pollution analyzer test failed: {e}")
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
        assert hasattr(checker, "_road_cache_dir"), "Road cache directory not configured"
        print(f"  ✅ Road cache directory configured: {checker._road_cache_dir}")

        # 检查缓存目录是否存在
        assert os.path.exists(checker._road_cache_dir), "Road cache directory does not exist"
        print("  ✅ Road cache directory exists")

        return True

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
        SimpleRoadChecker()
        print("  ✅ Simple road checker created successfully")

        # 检查OSMnx缓存是否已设置
        import osmnx as ox

        cache_folder = ox.settings.cache_folder
        assert cache_folder is not None, "OSMnx cache directory not set"
        print(f"  ✅ OSMnx cache directory set: {cache_folder}")

        return True

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
        clear_cache("temp")
        print("  ✅ Temporary cache cleanup successful")

        # 获取清理后的缓存信息
        cache_info = get_cache_info()
        assert "temp" in cache_info["subdirs"], "Temp cache directory not found"
        temp_size = cache_info["subdirs"]["temp"]["size"]
        print(f"  ✅ Temporary cache size: {temp_size}")

        return True

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
        test_cache_cleanup,
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
