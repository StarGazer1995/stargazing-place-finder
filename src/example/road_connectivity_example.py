#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
道路连通性检测示例
展示如何在观星地点查找中使用道路连通性检测
"""

import os
import sys
# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from road_connectivity_checker import RoadConnectivityChecker, simple_road_check
import json
import time

def demo_simple_check():
    """
    简单道路连通性检测演示
    
    使用便捷函数simple_road_check进行快速的道路可达性检测
    适用于需要快速筛选大量候选地点的场景
    
    测试地点：
    - 北京怀柔：典型的郊区观星地点
    - 上海崇明岛：岛屿地区的可达性
    - 西藏纳木错：高海拔偏远地区
    - 新疆喀纳斯：边境地区的道路状况
    - 海上某点：明确不可达的测试点
    
    演示内容：
    1. 使用便捷函数进行快速检测
    2. 测量检测耗时和性能
    3. 展示不同地理环境的检测结果
    4. 验证函数的准确性和可靠性
    
    输出信息：
    - 每个地点的可达性状态
    - 检测耗时统计
    - 结果的可视化展示
    """
    print("=== 简单道路连通性检测示例 ===")
    
    # 一些测试坐标（观星地点候选）
    test_locations = [
        {"name": "北京怀柔", "lat": 40.3242, "lon": 116.6312},
        {"name": "上海崇明岛", "lat": 31.6270, "lon": 121.3975},
        {"name": "西藏纳木错", "lat": 30.7188, "lon": 90.9960},
        {"name": "新疆喀纳斯", "lat": 48.7070, "lon": 87.0400},
        {"name": "海上某点（不可达）", "lat": 30.0, "lon": 125.0},
    ]
    
    for location in test_locations:
        print(f"\n检测 {location['name']} ({location['lat']}, {location['lon']}):")
        
        start_time = time.time()
        accessible = simple_road_check(location['lat'], location['lon'])
        end_time = time.time()
        
        status = "✅ 可达" if accessible else "❌ 不可达"
        print(f"结果: {status} (耗时: {end_time - start_time:.2f}秒)")

def demo_detailed_check():
    """
    详细道路连通性检测演示
    
    使用RoadConnectivityChecker类进行深入的道路可达性分析
    提供多种交通方式的详细检测信息
    
    检测参数：
    - 搜索半径：15公里
    - 测试地点：密云水库观星点
    - 交通方式：驾车、步行、骑行
    
    演示内容：
    1. 创建详细检测器实例
    2. 测试多种交通方式的可达性
    3. 获取距离最近道路的详细信息
    4. 分析道路网络的节点密度
    5. 展示错误处理和异常情况
    
    输出信息：
    - 各交通方式的可达性状态
    - 距离最近道路的精确距离
    - 最近道路的类型信息
    - 网络节点数量统计
    - 详细的错误信息（如有）
    """
    print("\n=== 详细道路连通性检测示例 ===")
    
    checker = RoadConnectivityChecker(search_radius_km=15.0)
    
    # 测试一个具体的观星地点
    stargazing_spot = {
        "name": "密云水库观星点", 
        "lat": 40.4769, 
        "lon": 117.1230
    }
    
    print(f"\n详细检测 {stargazing_spot['name']}:")
    
    # 检测不同交通方式的可达性
    transport_modes = [
        ('drive', '驾车'),
        ('walk', '步行'),
        ('bike', '骑行')
    ]
    
    for mode, mode_name in transport_modes:
        print(f"\n{mode_name}可达性:")
        info = checker.get_accessibility_info(
            stargazing_spot['lat'], 
            stargazing_spot['lon'], 
            network_type=mode
        )
        
        if info['accessible']:
            print(f"  ✅ {mode_name}可达")
            print(f"  📍 距离最近道路: {info['distance_to_road_km']:.2f} km")
            if info['nearest_road_type']:
                print(f"  🛣️  最近道路类型: {info['nearest_road_type']}")
        else:
            print(f"  ❌ {mode_name}不可达")
            if info['error']:
                print(f"  ⚠️  错误: {info['error']}")
        
        print(f"  📊 网络节点数: {info['network_nodes_count']}")

def demo_batch_check():
    """
    批量道路连通性检测演示
    
    演示如何高效地批量检测多个候选观星地点的道路可达性
    适用于大规模观星地点筛选的实际应用场景
    
    检测参数：
    - 搜索半径：10公里
    - 候选地点：5个北京周边位置
    - 检测方式：批量并行处理
    
    测试地点：
    - 北京怀柔、密云水库、房山、延庆、大兴等地
    
    演示内容：
    1. 模拟从光污染分析中获得的候选地点
    2. 使用批量检测功能提高效率
    3. 统计检测耗时和性能指标
    4. 计算可达率和筛选效果
    5. 生成详细的统计报告
    
    输出信息：
    - 每个地点的检测结果
    - 批量检测的总耗时
    - 可达地点的统计数量
    - 整体可达率百分比
    
    Returns:
        list: 可达的地点坐标列表
    """
    print("\n=== 批量道路连通性检测示例 ===")
    
    # 模拟从光污染分析中筛选出的候选观星地点
    candidate_locations = [
        (40.3242, 116.6312),  # 北京怀柔
        (40.4769, 117.1230),  # 密云水库
        (40.2539, 116.2340),  # 房山某地
        (40.5678, 116.8901),  # 延庆某地
        (40.1234, 116.5678),  # 大兴某地
    ]
    
    checker = RoadConnectivityChecker(search_radius_km=10.0)
    
    print(f"批量检测 {len(candidate_locations)} 个候选观星地点...")
    
    start_time = time.time()
    results = checker.batch_check_accessibility(candidate_locations)
    end_time = time.time()
    
    print(f"\n批量检测结果 (总耗时: {end_time - start_time:.2f}秒):")
    
    accessible_locations = []
    for i, ((lat, lon), accessible) in enumerate(zip(candidate_locations, results)):
        status = "✅ 可达" if accessible else "❌ 不可达"
        print(f"  地点 {i+1} ({lat}, {lon}): {status}")
        
        if accessible:
            accessible_locations.append((lat, lon))
    
    print(f"\n📊 统计结果:")
    print(f"  总候选地点: {len(candidate_locations)}")
    print(f"  可达地点: {len(accessible_locations)}")
    print(f"  可达率: {len(accessible_locations)/len(candidate_locations)*100:.1f}%")
    
    return accessible_locations

def integrate_with_stargazing_finder():
    """
    观星地点查找流程集成演示
    
    演示道路连通性检测在完整观星地点查找流程中的应用
    展示多重筛选条件的综合评估方法
    
    集成流程：
    1. 光污染数据筛选：获取低光污染候选地点
    2. 道路可达性检测：验证地点的交通便利性
    3. 综合评估排序：结合多个因素进行最终推荐
    
    筛选条件：
    - 光污染指数：< 0.3（较低水平）
    - 道路可达性：必须可达
    - 搜索半径：12公里
    
    演示内容：
    1. 模拟光污染分析的筛选结果
    2. 对候选地点进行道路可达性验证
    3. 综合评估和排序推荐
    4. 处理无符合条件地点的情况
    5. 提供优化建议和替代方案
    
    输出信息：
    - 各阶段的筛选结果
    - 最终推荐的观星地点列表
    - 每个地点的详细评估信息
    - 优化建议和使用指导
    """
    print("\n=== 集成到观星地点查找流程 ===")
    
    # 模拟观星地点查找的完整流程
    print("1. 🌃 根据光污染数据筛选候选地点...")
    
    # 假设这些是光污染较低的候选地点
    low_pollution_candidates = [
        {"lat": 40.3242, "lon": 116.6312, "light_pollution": 0.2},
        {"lat": 40.4769, "lon": 117.1230, "light_pollution": 0.15},
        {"lat": 40.8000, "lon": 117.5000, "light_pollution": 0.1},  # 可能不可达
        {"lat": 40.2539, "lon": 116.2340, "light_pollution": 0.25},
    ]
    
    print(f"   找到 {len(low_pollution_candidates)} 个低光污染候选地点")
    
    print("\n2. 🛣️  检测道路可达性...")
    
    checker = RoadConnectivityChecker(search_radius_km=12.0)
    accessible_candidates = []
    
    for candidate in low_pollution_candidates:
        accessible = checker.is_road_accessible(
            candidate['lat'], 
            candidate['lon']
        )
        
        if accessible:
            candidate['road_accessible'] = True
            accessible_candidates.append(candidate)
            print(f"   ✅ ({candidate['lat']}, {candidate['lon']}) 可达")
        else:
            print(f"   ❌ ({candidate['lat']}, {candidate['lon']}) 不可达")
    
    print(f"\n3. 📊 最终推荐结果:")
    
    if accessible_candidates:
        # 按光污染程度排序
        accessible_candidates.sort(key=lambda x: x['light_pollution'])
        
        print(f"   找到 {len(accessible_candidates)} 个可达的优质观星地点:")
        
        for i, spot in enumerate(accessible_candidates, 1):
            print(f"   {i}. 坐标: ({spot['lat']}, {spot['lon']})")
            print(f"      光污染指数: {spot['light_pollution']}")
            print(f"      道路可达: ✅")
            print()
    else:
        print("   ⚠️  没有找到既低光污染又可达的观星地点")
        print("   建议扩大搜索范围或降低筛选标准")

def save_results_to_json():
    """
    检测结果JSON格式保存演示
    
    演示如何将道路连通性检测结果保存为结构化的JSON文件
    便于后续数据分析和系统集成
    
    保存内容：
    1. 检测时间戳和参数配置
    2. 详细的检测结果数据
    3. 地点信息和可达性状态
    4. 距离道路的精确测量
    
    数据结构：
    - 元数据：检测时间、参数设置
    - 结果数组：每个地点的完整信息
    - 统计信息：汇总数据和指标
    
    演示内容：
    1. 构建标准化的结果数据结构
    2. 使用UTF-8编码保存中文信息
    3. 格式化JSON输出提高可读性
    4. 异常处理和错误恢复
    5. 文件保存状态的反馈
    
    输出文件：
    - road_accessibility_results.json：检测结果数据
    
    应用场景：
    - 数据持久化存储
    - 结果分享和交换
    - 后续分析和可视化
    - 系统集成和API对接
    """
    print("\n=== 保存检测结果 ===")
    
    # 示例数据
    results = {
        "检测时间": time.strftime("%Y-%m-%d %H:%M:%S"),
        "检测参数": {
            "搜索半径": "10km",
            "交通方式": "驾车"
        },
        "检测结果": [
            {
                "坐标": [40.3242, 116.6312],
                "地点名称": "北京怀柔",
                "可达性": True,
                "距离道路": 0.5
            },
            {
                "坐标": [40.4769, 117.1230],
                "地点名称": "密云水库",
                "可达性": True,
                "距离道路": 1.2
            }
        ]
    }
    
    output_file = "road_accessibility_results.json"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"✅ 结果已保存到 {output_file}")
    except Exception as e:
        print(f"❌ 保存失败: {e}")

if __name__ == "__main__":
    print("🌟 观星地点道路连通性检测演示")
    print("=" * 50)
    
    # 运行各种演示
    demo_simple_check()
    demo_detailed_check()
    demo_batch_check()
    integrate_with_stargazing_finder()
    save_results_to_json()
    
    print("\n🎉 演示完成！")
    print("\n💡 使用提示:")
    print("   - 使用 simple_road_check(lat, lon) 进行快速检测")
    print("   - 使用 RoadConnectivityChecker 类进行详细分析")
    print("   - 可以调整 search_radius_km 参数来平衡精度和性能")
    print("   - 支持 'drive', 'walk', 'bike' 等不同交通方式")