#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
健壮的API调用演示

这个脚本演示了改进后的Overpass API调用，包含:
1. 自动重试机制
2. 详细的错误处理
3. 网络超时处理
4. 服务器错误处理
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from stargazing_analyzer.stargazing_place_finder import StarGazingPlaceFinder
import time

def demo_robust_api_calls():
    """
    演示健壮的API调用功能
    """
    print("=== 健壮的API调用演示 ===")
    print("这个演示展示了改进后的Overpass API调用功能:")
    print("✓ 自动重试机制（最多3次）")
    print("✓ 智能错误处理")
    print("✓ 网络超时保护")
    print("✓ 详细的状态反馈")
    print()
    
    # 创建查找器实例
    finder = StarGazingPlaceFinder()
    
    # 测试不同类型的地点查找
    test_areas = [
        {
            "name": "北京市中心",
            "bbox": (39.9, 116.3, 40.0, 116.4),
            "description": "小范围测试 - 应该快速成功"
        },
        {
            "name": "北京更大范围", 
            "bbox": (39.8, 116.2, 40.1, 116.5),
            "description": "中等范围测试 - 可能需要更长时间"
        }
    ]
    
    for i, area in enumerate(test_areas, 1):
        print(f"{i}. 测试区域: {area['name']}")
        print(f"   描述: {area['description']}")
        print(f"   范围: {area['bbox']}")
        print()
        
        start_time = time.time()
        
        # 测试观景台查找
        print("   🔍 查找观景台...")
        try:
            viewpoints = finder.find_viewpoints_in_area(area['bbox'], max_viewpoints=5)
            print(f"   ✅ 成功找到 {len(viewpoints)} 个观景台")
            
            if viewpoints:
                print("   📍 观景台列表:")
                for j, vp in enumerate(viewpoints[:3], 1):
                    print(f"      {j}. {vp.name}")
                    print(f"         坐标: ({vp.latitude:.4f}, {vp.longitude:.4f})")
                    print(f"         海拔: {vp.elevation}m")
                    print(f"         距离最近城镇: {vp.distance_to_nearest_town:.1f}km")
        except Exception as e:
            print(f"   ❌ 观景台查找失败: {e}")
        
        print()
        
        # 测试山峰查找
        print("   🏔️ 查找山峰...")
        try:
            peaks = finder.find_peaks_in_area(area['bbox'], max_locations=3)
            print(f"   ✅ 成功找到 {len(peaks)} 个山峰")
            
            if peaks:
                print("   📍 山峰列表:")
                for j, peak in enumerate(peaks[:2], 1):
                    print(f"      {j}. {peak.name}")
                    print(f"         坐标: ({peak.latitude:.4f}, {peak.longitude:.4f})")
                    print(f"         海拔: {peak.elevation}m")
                    if peak.height_difference:
                        print(f"         高度差: {peak.height_difference:.1f}m")
        except Exception as e:
            print(f"   ❌ 山峰查找失败: {e}")
        
        print()
        
        # 测试天文台查找
        print("   🔭 查找天文台...")
        try:
            observatories = finder.find_observatories_in_area(area['bbox'], max_observatories=3)
            print(f"   ✅ 成功找到 {len(observatories)} 个天文台")
            
            if observatories:
                print("   📍 天文台列表:")
                for j, obs in enumerate(observatories[:2], 1):
                    print(f"      {j}. {obs.name}")
                    print(f"         坐标: ({obs.latitude:.4f}, {obs.longitude:.4f})")
                    print(f"         海拔: {obs.elevation}m")
        except Exception as e:
            print(f"   ❌ 天文台查找失败: {e}")
        
        elapsed_time = time.time() - start_time
        print(f"   ⏱️ 总耗时: {elapsed_time:.1f}秒")
        print("-" * 60)
        print()
    
    print("=== 演示完成 ===")
    print()
    print("🎯 主要改进:")
    print("• 网络超时自动重试（最多3次）")
    print("• 智能延迟策略避免API限制")
    print("• 详细的错误分类和处理")
    print("• 用户友好的状态反馈")
    print("• 504网关超时专门处理")
    print("• 429频率限制智能等待")
    print()
    print("💡 使用建议:")
    print("• 如果遇到超时，程序会自动重试")
    print("• 大范围查询可能需要更长时间")
    print("• 网络不稳定时建议稍后重试")
    print("• 查看详细日志了解API调用状态")

def demo_error_scenarios():
    """
    演示各种错误场景的处理
    """
    print("\n=== 错误处理演示 ===")
    print("演示如何处理各种API错误情况...")
    print()
    
    finder = StarGazingPlaceFinder()
    
    # 测试无效的查询范围
    print("1. 测试无效查询范围...")
    try:
        # 使用无效的坐标范围
        invalid_bbox = (200, 200, 300, 300)  # 超出地球坐标范围
        result = finder.get_viewpoints_from_overpass(invalid_bbox)
        print(f"   结果: {len(result)} 个观景台")
    except Exception as e:
        print(f"   处理了错误: {e}")
    
    print()
    print("2. 测试超大范围查询（可能触发超时）...")
    try:
        # 使用很大的查询范围
        large_bbox = (35, 110, 45, 120)  # 覆盖大部分中国北方
        print("   注意: 这个查询可能会很慢或超时，演示重试机制...")
        result = finder.get_viewpoints_from_overpass(large_bbox)
        print(f"   结果: {len(result)} 个观景台")
    except Exception as e:
        print(f"   处理了错误: {e}")
    
    print("\n错误处理演示完成")

if __name__ == "__main__":
    demo_robust_api_calls()
    
    # 可选：演示错误处理（可能比较慢）
    user_input = input("\n是否要演示错误处理场景？(y/n): ")
    if user_input.lower() == 'y':
        demo_error_scenarios()