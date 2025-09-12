#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一Location类演示脚本
展示如何使用统一后的Location类来处理山峰、天文台和观景台
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.stargazing_analyzer.stargazing_place_finder import Location, Peak, Observatory, Viewpoint

def demonstrate_unified_location_class():
    """演示统一的Location类功能"""
    print("=== 统一Location类演示 ===")
    print()
    
    # 创建不同类型的地点
    locations = [
        # 使用Location类直接创建山峰
        Location(
            name="珠穆朗玛峰",
            latitude=27.9881,
            longitude=86.9250,
            elevation=8848.86,
            distance_to_nearest_town=50.0,
            nearest_town_name="定日县",
            location_type="mountain_peak",
            prominence=8848.86,
            height_difference=8000.0,
            description="世界最高峰"
        ),
        
        # 使用Location类直接创建天文台
        Location(
            name="帕洛马天文台",
            latitude=33.3563,
            longitude=-116.8650,
            elevation=1712.0,
            distance_to_nearest_town=25.0,
            nearest_town_name="埃斯孔迪多",
            location_type="observatory",
            observatory_type="光学天文台",
            description="著名的光学天文台，拥有5米海尔望远镜",
            light_pollution_level="低"
        ),
        
        # 使用Location类直接创建观景台
        Location(
            name="大峡谷南缘观景台",
            latitude=36.0544,
            longitude=-112.1401,
            elevation=2134.0,
            distance_to_nearest_town=15.0,
            nearest_town_name="大峡谷村",
            location_type="viewpoint",
            viewpoint_type="峡谷观景台",
            description="俯瞰科罗拉多大峡谷的绝佳位置",
            scenic_value="优秀"
        ),
        
        # 使用别名创建（向后兼容）
        Peak(
            name="泰山",
            latitude=36.2532,
            longitude=117.1013,
            elevation=1532.7,
            distance_to_nearest_town=8.0,
            nearest_town_name="泰安市",
            location_type="mountain_peak",
            prominence=1391.0,
            height_difference=1400.0,
            description="五岳之首"
        ),
        
        Observatory(
            name="北京天文馆",
            latitude=39.9425,
            longitude=116.3374,
            elevation=50.0,
            distance_to_nearest_town=0.5,
            nearest_town_name="北京市",
            location_type="observatory",
            observatory_type="天象馆",
            description="中国第一座大型天象馆",
            light_pollution_level="高"
        ),
        
        Viewpoint(
            name="黄山迎客松观景台",
            latitude=30.1394,
            longitude=118.1558,
            elevation=1670.0,
            distance_to_nearest_town=12.0,
            nearest_town_name="汤口镇",
            location_type="viewpoint",
            viewpoint_type="山顶观景台",
            description="观赏著名迎客松的最佳位置",
            scenic_value="优秀"
        )
    ]
    
    # 展示所有地点的信息
    for i, location in enumerate(locations, 1):
        print(f"{i}. {location.name}")
        print(f"   类型: {location.location_type}")
        print(f"   坐标: ({location.latitude:.4f}, {location.longitude:.4f})")
        print(f"   海拔: {location.elevation:.1f}m")
        print(f"   最近城镇: {location.nearest_town_name} ({location.distance_to_nearest_town:.1f}km)")
        
        # 根据类型显示特定信息
        if location.is_mountain_peak():
            print(f"   🏔️  山峰特征:")
            if location.prominence:
                print(f"      相对高度: {location.prominence:.1f}m")
            if location.height_difference:
                print(f"      高度差: {location.height_difference:.1f}m")
                
        elif location.is_observatory():
            print(f"   🔭 天文台特征:")
            if location.observatory_type:
                print(f"      类型: {location.observatory_type}")
            if location.light_pollution_level:
                print(f"      光污染等级: {location.light_pollution_level}")
                
        elif location.is_viewpoint():
            print(f"   🌄 观景台特征:")
            if location.viewpoint_type:
                print(f"      类型: {location.viewpoint_type}")
            if location.scenic_value:
                print(f"      景观价值: {location.scenic_value}")
        
        if location.description:
            print(f"   📝 描述: {location.description}")
        
        print()

def demonstrate_type_filtering():
    """演示类型过滤功能"""
    print("=== 类型过滤演示 ===")
    print()
    
    # 创建混合类型的地点列表
    mixed_locations = [
        Location("华山", 34.4749, 110.0870, 2154.9, 15.0, "华阴市", "mountain_peak", prominence=1665.0),
        Location("紫金山天文台", 32.0603, 118.8197, 267.0, 8.0, "南京市", "observatory", observatory_type="光学天文台"),
        Location("天门山观景台", 29.0519, 110.4792, 1518.6, 20.0, "张家界市", "viewpoint", scenic_value="优秀"),
        Location("峨眉山", 29.5446, 103.3340, 3099.0, 25.0, "峨眉山市", "mountain_peak", prominence=2540.0),
        Location("上海天文馆", 31.1129, 121.6424, 5.0, 2.0, "上海市", "observatory", observatory_type="科普天文馆")
    ]
    
    # 按类型分组
    peaks = [loc for loc in mixed_locations if loc.is_mountain_peak()]
    observatories = [loc for loc in mixed_locations if loc.is_observatory()]
    viewpoints = [loc for loc in mixed_locations if loc.is_viewpoint()]
    
    print(f"🏔️  山峰 ({len(peaks)}个):")
    for peak in peaks:
        print(f"   - {peak.name} (海拔: {peak.elevation:.1f}m)")
    print()
    
    print(f"🔭 天文台 ({len(observatories)}个):")
    for obs in observatories:
        print(f"   - {obs.name} (类型: {obs.observatory_type or '未知'})")
    print()
    
    print(f"🌄 观景台 ({len(viewpoints)}个):")
    for vp in viewpoints:
        print(f"   - {vp.name} (景观价值: {vp.scenic_value or '未评估'})")
    print()

def demonstrate_backward_compatibility():
    """演示向后兼容性"""
    print("=== 向后兼容性演示 ===")
    print()
    
    # 使用原有的类名创建对象
    peak = Peak("测试山峰", 40.0, 116.0, 1500.0, 10.0, "测试城镇", "mountain_peak")
    observatory = Observatory("测试天文台", 39.0, 115.0, 1200.0, 15.0, "测试城镇", "observatory")
    viewpoint = Viewpoint("测试观景台", 38.0, 114.0, 800.0, 5.0, "测试城镇", "viewpoint")
    
    print("使用别名创建的对象:")
    print(f"Peak: {peak.name} -> 类型: {type(peak).__name__}, 是Location实例: {isinstance(peak, Location)}")
    print(f"Observatory: {observatory.name} -> 类型: {type(observatory).__name__}, 是Location实例: {isinstance(observatory, Location)}")
    print(f"Viewpoint: {viewpoint.name} -> 类型: {type(viewpoint).__name__}, 是Location实例: {isinstance(viewpoint, Location)}")
    print()
    
    # 验证类型检查方法
    print("类型检查方法验证:")
    for name, obj in [("Peak", peak), ("Observatory", observatory), ("Viewpoint", viewpoint)]:
        print(f"{name}: 山峰={obj.is_mountain_peak()}, 天文台={obj.is_observatory()}, 观景台={obj.is_viewpoint()}")
    print()

if __name__ == "__main__":
    print("🌟 统一Location类功能演示")
    print("=" * 50)
    print()
    
    demonstrate_unified_location_class()
    print("=" * 50)
    print()
    
    demonstrate_type_filtering()
    print("=" * 50)
    print()
    
    demonstrate_backward_compatibility()
    print("=" * 50)
    print()
    
    print("✅ 演示完成！")
    print()
    print("📋 总结:")
    print("1. 成功将Peak、Observatory、Viewpoint统一为Location类")
    print("2. 保持了向后兼容性，原有代码无需修改")
    print("3. 通过location_type字段区分不同类型的地点")
    print("4. 提供了便捷的类型检查方法")
    print("5. 支持类型特定的可选字段")