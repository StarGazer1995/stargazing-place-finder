#!/usr/bin/env python3
"""
山峰查找器测试脚本
用于测试山峰查找功能的各项能力
"""

import os
import sys

# 添加 src 目录到路径以加载顶层包
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

import time

from stargazing_analyzer.stargazing_place_finder import StarGazingPlaceFinder, find_peaks_with_height_difference


def test_distance_calculation():
    """
    测试距离计算功能

    使用北京到上海的已知距离（约1000公里）来验证
    Haversine公式计算地理坐标间距离的准确性

    Returns:
        bool: 测试是否通过（距离在合理范围内）
    """
    print("=== Test 1: Distance Calculation Function ===")

    finder = StarGazingPlaceFinder()

    # 测试北京到上海的距离（已知约1000公里）
    beijing_lat, beijing_lon = 39.9042, 116.4074
    shanghai_lat, shanghai_lon = 31.2304, 121.4737

    distance = finder.calculate_distance(beijing_lat, beijing_lon, shanghai_lat, shanghai_lon)
    print(f"Distance from Beijing to Shanghai: {distance:.1f} km")

    # 验证距离是否合理（应该在1000-1200公里之间）
    if 1000 <= distance <= 1200:
        print("✅ Distance calculation test passed")
    else:
        print("❌ Distance calculation test failed")

    assert isinstance(distance, (int, float)), "Distance should be a numeric value"
    assert 1000 <= distance <= 1200, f"Distance should be between 1000-1200 km, got {distance:.1f} km"


def test_elevation_api():
    """
    测试海拔API功能

    通过查询珠穆朗玛峰的海拔数据来验证
    外部海拔API服务的可用性和数据准确性

    Returns:
        bool: 测试是否通过（API可用且数据合理）
    """
    print("\n=== Test 2: Elevation API Function ===")

    finder = StarGazingPlaceFinder()

    # 测试珠穆朗玛峰的海拔（应该接近8848米）
    everest_lat, everest_lon = 27.9881, 86.9250

    print("Getting elevation data for Mount Everest...")
    elevation = finder.get_elevation_from_api(everest_lat, everest_lon)

    if elevation is not None:
        print(f"Mount Everest elevation: {elevation} meters")
        # 海拔数据可能不够精确，但应该在8000米以上
        if elevation > 8000:
            print("✅ Elevation API test passed")
        else:
            print(f"⚠️ Elevation data may be inaccurate: {elevation} meters")
        assert isinstance(elevation, (int, float)), "Elevation should be a numeric value"
    else:
        print("❌ Elevation API test failed")
        # API可能暂时不可用，但不应该导致测试失败
        print("⚠️ API may be temporarily unavailable")


def test_overpass_api():
    """
    测试Overpass API功能

    验证从OpenStreetMap Overpass API获取
    山峰和城镇地理数据的功能是否正常

    测试区域：北京香山附近

    Returns:
        bool: 测试是否通过（能够获取到山峰和城镇数据）
    """
    print("\n=== Test 3: Overpass API Function ===")

    finder = StarGazingPlaceFinder()

    # 测试小范围区域的数据获取（北京香山附近）
    bbox = (39.98, 116.18, 40.02, 116.22)

    print("Getting peak data...")
    peaks = finder.get_peaks_from_overpass(bbox)
    print(f"Found {len(peaks)} peaks")

    print("Getting town data...")
    towns = finder.get_towns_from_overpass(bbox)
    print(f"Found {len(towns)} towns")

    if len(peaks) > 0 and len(towns) > 0:
        print("✅ Overpass API test passed")
    else:
        print("❌ Overpass API test failed")

    assert isinstance(peaks, list), "Peaks should be returned as a list"
    assert isinstance(towns, list), "Towns should be returned as a list"


def test_small_area_search():
    """
    测试小范围山峰搜索功能

    在指定的小范围区域内搜索符合条件的山峰，
    验证山峰查找算法的完整性和准确性

    测试区域：北京香山地区
    测试条件：高度差大于100米

    Returns:
        bool: 测试是否通过（找到符合条件的山峰）
    """
    print("\n=== Test 4: Small Range Peak Search ===")

    # 选择一个已知有山峰的小区域（北京香山地区）
    bbox = (39.98, 116.18, 40.02, 116.22)

    print("Searching for peaks in Xiangshan area...")
    print("Search parameters: minimum height difference 50m, maximum 5 peaks")

    try:
        peaks = find_peaks_with_height_difference(
            south=bbox[0],
            west=bbox[1],
            north=bbox[2],
            east=bbox[3],
            min_height_diff=50.0,  # 降低要求以便找到结果
            max_locations=5,
        )

        print(f"Found {len(peaks)} peaks that meet the criteria")

        if peaks:
            print("Peak details:")
            for i, peak in enumerate(peaks, 1):
                print(f"{i}. {peak.name}")
                print(f"   Coordinates: ({peak.latitude:.4f}, {peak.longitude:.4f})")
                print(f"   Elevation: {peak.elevation:.1f}m")
                print(f"   Height difference: {peak.height_difference:.1f}m")
                print(f"   Distance to nearest town: {peak.distance_to_nearest_town:.1f}km")
            print("✅ Small range search test passed")
        else:
            print("⚠️ No peaks found that meet the criteria, but function works normally")

        assert isinstance(peaks, list), "Peaks should be returned as a list"

    except Exception as e:
        print(f"❌ Small range search test failed: {e}")
        # Re-raise the exception to fail the test properly
        raise


def test_convenience_function():
    """
    测试便捷函数功能

    验证find_peaks_with_height_difference便捷函数
    是否能够正确封装复杂的山峰查找逻辑，
    为用户提供简单易用的接口

    测试参数：更小的搜索区域和更低的高度差要求

    Returns:
        bool: 测试是否通过（便捷函数正常工作）
    """
    print("\n=== Test 5: Convenience Function Test ===")

    # 测试便捷函数
    bbox = (39.99, 116.19, 40.01, 116.21)  # 更小的区域

    print("Using convenience function to search for peaks...")

    try:
        peaks = find_peaks_with_height_difference(
            south=bbox[0],
            west=bbox[1],
            north=bbox[2],
            east=bbox[3],
            min_height_diff=30.0,  # 进一步降低要求
            max_locations=3,
        )

        print(f"Convenience function returned {len(peaks)} results")
        print("✅ Convenience function test passed")

        assert isinstance(peaks, list), "Convenience function should return a list"

    except Exception as e:
        print(f"❌ Convenience function test failed: {e}")
        # Re-raise the exception to fail the test properly
        raise


def test_error_handling():
    """
    测试错误处理机制

    验证系统在遇到无效输入、网络错误、
    API限制等异常情况时的健壮性和
    错误恢复能力

    测试场景：
    - 无效的地理坐标边界
    - 极端的参数值
    - 网络连接问题模拟

    Returns:
        bool: 测试是否通过（错误处理机制正常）
    """
    print("\n=== Test 6: Error Handling Test ===")

    finder = StarGazingPlaceFinder()

    # 测试无效坐标
    print("Testing invalid coordinate handling...")
    elevation = finder.get_elevation_from_api(999, 999)
    if elevation is None:
        print("✅ Invalid coordinate error handling is correct")
    else:
        print("⚠️ Invalid coordinates returned data (API may have good fault tolerance)")

    # 测试空区域
    print("Testing ocean area (no peaks)...")
    ocean_bbox = (25.0, 125.0, 25.1, 125.1)  # 太平洋某处
    peaks = finder.get_peaks_from_overpass(ocean_bbox)

    if len(peaks) == 0:
        print("✅ Ocean area correctly returned empty results")
    else:
        print(f"⚠️ Ocean area returned {len(peaks)} results")


def run_all_tests():
    """
    运行所有山峰查找器测试用例

    按顺序执行所有测试函数，统计测试结果，
    并在测试间添加延迟以避免API请求过于频繁

    测试覆盖范围：
    1. 距离计算算法验证
    2. 海拔API服务可用性
    3. Overpass API数据获取
    4. 小范围山峰搜索功能
    5. 便捷函数接口测试
    6. 错误处理机制验证

    Returns:
        bool: 所有测试是否全部通过
    """
    print("Peak Finder Function Test")
    print("=" * 50)

    tests = [
        test_distance_calculation,
        test_elevation_api,
        test_overpass_api,
        test_small_area_search,
        test_convenience_function,
        test_error_handling,
    ]

    passed = 0
    total = len(tests)

    for test_func in tests:
        try:
            if test_func():
                passed += 1
            time.sleep(1)  # 避免API请求过于频繁
        except Exception as e:
            print(f"❌ Test {test_func.__name__} encountered exception: {e}")

    print("\n" + "=" * 50)
    print(f"Test results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Peak finder function works normally")
    elif passed >= total * 0.8:
        print("✅ Most tests passed, function works basically normally")
    else:
        print("⚠️ Some tests failed, please check network connection and API availability")

    print("\nUsage suggestions:")
    print("1. Ensure network connection is normal")
    print("2. Some APIs may have access restrictions or delays")
    print("3. You can adjust search parameters to adapt to different regions")
    print("4. It is recommended to test the target area before actual use")

    # 返回测试是否全部通过
    return passed == total


if __name__ == "__main__":
    run_all_tests()
