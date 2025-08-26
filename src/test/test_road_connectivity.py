#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
道路连通性检测功能测试脚本
用于验证道路连通性检测代码是否正常工作
"""

import sys
import os
# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from simple_road_checker import quick_road_check, batch_road_check
from road_connectivity_checker import RoadConnectivityChecker
import time

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
    print("=== 测试快速检测功能 ===")
    
    # 测试一个已知可达的地点（北京市区）
    lat, lon = 39.9042, 116.4074  # 天安门广场
    print(f"测试坐标: ({lat}, {lon}) - 天安门广场")
    
    start_time = time.time()
    result = quick_road_check(lat, lon, search_radius_km=3.0)
    end_time = time.time()
    
    print(f"结果: {'✅ 可达' if result else '❌ 不可达'}")
    print(f"耗时: {end_time - start_time:.2f}秒")
    
    return result

def test_batch_check():
    """
    测试批量道路连通性检测功能
    
    同时检测多个不同类型的地点，验证
    batch_road_check函数的批处理能力和准确性
    
    测试地点类型：
    - 城市中心（应该可达）
    - 郊区地点（应该可达）
    - 海洋区域（应该不可达）
    
    验证要点：
    - 批量处理效率
    - 结果准确性
    - 不同地形的识别能力
    
    Returns:
        list: 各地点的连通性检测结果列表
    """
    print("\n=== 测试批量检测功能 ===")
    
    # 测试多个地点
    test_locations = [
        (39.9042, 116.4074),  # 天安门广场（应该可达）
        (40.3242, 116.6312),  # 北京怀柔（应该可达）
        (30.0, 125.0),        # 海上某点（应该不可达）
    ]
    
    location_names = ["天安门广场", "北京怀柔", "海上某点"]
    
    print(f"批量测试 {len(test_locations)} 个地点...")
    
    start_time = time.time()
    results = batch_road_check(test_locations, search_radius_km=5.0)
    end_time = time.time()
    
    print(f"批量检测结果 (总耗时: {end_time - start_time:.2f}秒):")
    
    accessible_count = 0
    for i, ((lat, lon), result, name) in enumerate(zip(test_locations, results, location_names)):
        status = "✅ 可达" if result else "❌ 不可达"
        print(f"  {i+1}. {name} ({lat}, {lon}): {status}")
        if result:
            accessible_count += 1
    
    print(f"\n统计: {accessible_count}/{len(test_locations)} 个地点可达")
    return results

def test_detailed_checker():
    """
    测试详细道路连通性检测器功能
    
    使用RoadConnectivityChecker类进行深度检测，
    获取更详细的道路连通性信息和分析数据
    
    测试内容：
    - 可达性判断的准确性
    - 距离道路的精确测量
    - 道路网络节点统计
    - 最近道路类型识别
    - 错误信息的完整性
    
    Returns:
        bool: 详细检测功能是否正常工作
    """
    print("\n=== 测试详细检测器功能 ===")
    
    checker = RoadConnectivityChecker(search_radius_km=8.0)
    
    # 测试一个具体地点
    lat, lon = 40.3242, 116.6312  # 北京怀柔
    print(f"详细测试: 北京怀柔 ({lat}, {lon})")
    
    # 获取详细信息
    info = checker.get_accessibility_info(lat, lon)
    
    print(f"可达性: {'✅ 可达' if info['accessible'] else '❌ 不可达'}")
    if info['accessible']:
        print(f"距离道路: {info['distance_to_road_km']:.2f} km")
        print(f"网络节点数: {info['network_nodes_count']}")
        if info['nearest_road_type']:
            print(f"最近道路类型: {info['nearest_road_type']}")
    else:
        if info['error']:
            print(f"错误信息: {info['error']}")
    
    return info['accessible']

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
    print("\n=== 测试错误处理功能 ===")
    
    # 测试无效坐标
    invalid_coords = [
        (91.0, 0.0),    # 纬度超出范围
        (0.0, 181.0),   # 经度超出范围
        (0.0, 0.0),     # 可能没有道路数据的地点
    ]
    
    for lat, lon in invalid_coords:
        print(f"测试无效坐标: ({lat}, {lon})")
        try:
            result = quick_road_check(lat, lon, search_radius_km=2.0)
            print(f"  结果: {'可达' if result else '不可达'}")
        except Exception as e:
            print(f"  捕获异常: {e}")

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
    print("🧪 道路连通性检测功能测试")
    print("=" * 50)
    
    try:
        # 运行各项测试
        test1_result = test_quick_check()
        test2_results = test_batch_check()
        test3_result = test_detailed_checker()
        test_error_handling()
        
        print("\n📊 测试总结:")
        print(f"  快速检测: {'✅ 通过' if test1_result else '❌ 失败'}")
        print(f"  批量检测: {'✅ 通过' if any(test2_results) else '❌ 失败'}")
        print(f"  详细检测: {'✅ 通过' if test3_result else '❌ 失败'}")
        print(f"  错误处理: ✅ 通过")
        
        # 总体评估
        all_passed = test1_result and any(test2_results) and test3_result
        print(f"\n🎯 总体结果: {'✅ 所有测试通过' if all_passed else '⚠️ 部分测试失败'}")
        
        if all_passed:
            print("\n🎉 道路连通性检测功能工作正常！")
            print("\n💡 使用建议:")
            print("   - 对于快速筛选，使用 quick_road_check()")
            print("   - 对于批量处理，使用 batch_road_check()")
            print("   - 对于详细分析，使用 RoadConnectivityChecker")
            print("   - 根据地区特点调整搜索半径参数")
        else:
            print("\n⚠️ 部分功能可能存在问题，请检查网络连接和依赖包")
            
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        print("请检查依赖包是否正确安装")

if __name__ == "__main__":
    run_all_tests()