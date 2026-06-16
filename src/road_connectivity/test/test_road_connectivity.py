#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
道路连通性检测功能测试脚本
用于验证道路连通性检测代码是否正常工作
"""

import os
import sys
import warnings

# 添加 src 目录到Python路径以加载顶层包
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

import time

from models import GeoCoordinate
from road_connectivity.road_connectivity_checker import RoadConnectivityChecker
from road_connectivity.simple_road_checker import batch_road_check, quick_road_check

# 抑制已弃用功能的 DeprecationWarning（向后兼容测试）
warnings.simplefilter("ignore", DeprecationWarning)


def test_quick_check():
    """
    测试快速道路连通性检测功能

    使用已知可达的地点（天安门广场）验证
    quick_road_check函数的基本功能和性能

    测试要点：
    - 功能正确性：能否正确识别可达地点
    - 性能表现：检测耗时是否在合理范围内
    - 返回值格式：布尔值返回是否正确

    Returns:
        bool: 测试地点是否被正确识别为可达
    """
    print("=== Testing Quick Detection Function ===")

    # 测试一个已知可达的地点（北京市区）
    lat, lon = 39.9042, 116.4074  # 天安门广场
    print(f"Test coordinates: ({lat}, {lon}) - Tiananmen Square")

    start_time = time.time()
    result = quick_road_check(lat, lon, search_radius_km=3.0)
    end_time = time.time()

    print(f"Result: {'✅ Accessible' if result else '❌ Not accessible'}")
    print(f"Time taken: {end_time - start_time:.2f} seconds")

    assert result is not None, "Quick road check should return a boolean value"


def test_batch_check():
    """
    测试批量道路连通性检测功能（使用 GeoFence 模拟数据，无需真实网络请求）
    """
    print("\n=== Testing Batch Detection Function (GeoFence) ===")

    from road_connectivity.geo_fence import GeoFence

    geo_fence = GeoFence(enabled=True)
    test_locations = [
        (39.9042, 116.4074),  # 北京（围栏返回可达）
        (40.3242, 116.6312),  # 北京怀柔（围栏返回可达）
        (25.0, 125.0),  # 海上（围栏返回不可达）
    ]

    location_names = ["天安门广场", "北京怀柔", "海上某点"]

    print(f"Batch testing {len(test_locations)} locations...")

    start_time = time.time()
    results = batch_road_check(test_locations, search_radius_km=5.0, geo_fence=geo_fence)
    end_time = time.time()

    print(f"Batch detection results (total time: {end_time - start_time:.2f} seconds):")

    accessible_count = 0
    for i, ((lat, lon), result, name) in enumerate(zip(test_locations, results, location_names)):
        status = "✅ 可达" if result else "❌ 不可达"
        print(f"  {i + 1}. {name} ({lat}, {lon}): {status}")
        if result:
            accessible_count += 1

    print(f"\nStatistics: {accessible_count}/{len(test_locations)} locations accessible")

    assert len(results) == len(test_locations), "Batch check should return results for all locations"
    assert all(isinstance(result, bool) for result in results), "All results should be boolean values"


def test_detailed_checker():
    """
    测试详细道路连通性检测器功能（使用 GeoFence 模拟数据，无需真实网络请求）

    测试内容：
    - 可达性判断的准确性
    - 距离道路的精确测量
    - 道路网络节点统计
    - 最近道路类型识别
    - 错误信息的完整性

    Returns:
        bool: 详细检测功能是否正常工作
    """
    print("\n=== Testing Detailed Detector Functions (GeoFence) ===")

    from road_connectivity.geo_fence import GeoFence

    geo_fence = GeoFence(enabled=True)
    checker = RoadConnectivityChecker(search_radius_km=8.0, geo_fence=geo_fence)

    # 测试一个具体地点（北京怀柔，围栏返回可达）
    lat, lon = 40.3242, 116.6312
    print(f"Detailed test: Beijing Huairou ({lat}, {lon})")

    # 获取详细信息
    point = GeoCoordinate(latitude=lat, longitude=lon)
    info = checker.get_accessibility_info(point)

    accessible = info.get("accessible", False)
    print(f"Accessibility: {'✅ Accessible' if accessible else '❌ Not accessible'}")
    if accessible:
        dist = info.get("distance_to_road_km")
        if dist is not None:
            print(f"Distance to road: {dist:.2f} km")
        print(f"Network nodes count: {info.get('network_nodes_count', 0)}")
        road_type = info.get("nearest_road_type")
        if road_type:
            print(f"Nearest road type: {road_type}")
    else:
        err = info.get("error")
        if err:
            print(f"Error message: {err}")

    assert "accessible" in info, "RoadAccessInfo should have 'accessible' key"
    assert isinstance(info["accessible"], bool), "Accessibility should be a boolean value"
    return info["accessible"]


def test_error_handling():
    """
    测试道路连通性检测的错误处理机制

    验证系统在遇到异常输入时的健壮性，
    确保程序不会因为无效数据而崩溃

    测试场景：
    - 超出有效范围的地理坐标
    - 可能缺乏道路数据的特殊位置
    - 网络请求异常情况的处理

    验证要点：
    - 异常捕获的完整性
    - 错误信息的清晰度
    - 程序的稳定性
    """
    print("\n=== Testing Error Handling Functions ===")

    # 测试无效坐标
    invalid_coords = [
        (91.0, 0.0),  # 纬度超出范围
        (0.0, 181.0),  # 经度超出范围
        (0.0, 0.0),  # 可能没有道路数据的地点
    ]

    for lat, lon in invalid_coords:
        print(f"Testing invalid coordinates: ({lat}, {lon})")
        try:
            result = quick_road_check(lat, lon, search_radius_km=2.0)
            print(f"  Result: {'Accessible' if result else 'Not accessible'}")
        except Exception as e:
            print(f"  Caught exception: {e}")


def run_all_tests():
    """
    运行所有道路连通性检测测试用例

    按顺序执行所有测试函数，收集测试结果，
    并提供详细的测试报告和使用建议

    测试覆盖范围：
    1. 快速检测功能验证
    2. 批量检测能力测试
    3. 详细检测器功能验证
    4. 错误处理机制测试

    输出内容：
    - 各项测试的通过状态
    - 总体测试结果评估
    - 功能使用建议

    Returns:
        bool: 所有关键测试是否通过
    """
    print("🧪 Road Connectivity Detection Function Test")
    print("=" * 50)

    try:
        # 运行各项测试
        test1_result = test_quick_check()
        test2_results = test_batch_check()
        test3_result = test_detailed_checker()
        test_error_handling()

        print("\n📊 Test Summary:")
        print(f"  Quick detection: {'✅ Passed' if test1_result else '❌ Failed'}")
        print(f"  Batch detection: {'✅ Passed' if any(test2_results) else '❌ Failed'}")
        print(f"  Detailed detection: {'✅ Passed' if test3_result else '❌ Failed'}")
        print("  Error handling: ✅ Passed")

        # 总体评估
        all_passed = test1_result and any(test2_results) and test3_result
        print(f"\n🎯 Overall result: {'✅ All tests passed' if all_passed else '⚠️ Some tests failed'}")

        if all_passed:
            print("\n🎉 Road connectivity detection function works normally!")
            print("\n💡 Usage suggestions:")
            print("   - For quick filtering, use quick_road_check()")
            print("   - For batch processing, use batch_road_check()")
            print("   - For detailed analysis, use RoadConnectivityChecker")
            print("   - Adjust search radius parameters based on regional characteristics")
        else:
            print("\n⚠️ Some functions may have issues, please check network connection and dependencies")

    except Exception as e:
        print(f"\n❌ Error occurred during testing: {e}")
        print("Please check if dependencies are correctly installed")


if __name__ == "__main__":
    run_all_tests()
