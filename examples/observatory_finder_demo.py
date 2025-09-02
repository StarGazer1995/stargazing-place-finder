#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
天文台查找功能演示脚本

该脚本演示如何使用MountainPeakFinder类中的天文台查找功能，
在指定区域内搜索天文台并显示详细信息。
"""

import sys
import os

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from mountain_peak_finder import MountainPeakFinder, Location

def main():
    """
    主函数：演示天文台查找功能
    """
    print("=== 天文台查找功能演示 ===")
    print()
    
    # 创建天文台查找器实例
    finder = MountainPeakFinder()
    
    # 定义搜索区域（以北京周边为例）
    # 边界框格式：(south, west, north, east)
    beijing_area = (39.5, 115.5, 40.5, 117.5)
    
    print(f"搜索区域：北京周边 {beijing_area}")
    print("开始搜索天文台...")
    print()
    
    try:
        # 查找天文台
        observatories = finder.find_observatories_in_area(
            bbox=beijing_area,
            max_observatories=20
        )
        
        if not observatories:
            print("未找到任何天文台")
            return
        
        print("\n=== 搜索结果 ===")
        print(f"找到 {len(observatories)} 个天文台：")
        print()
        
        # 显示天文台详细信息
        for i, obs in enumerate(observatories, 1):
            # 验证这是天文台类型的Location对象
            assert obs.is_observatory(), f"期望天文台类型，但得到：{obs.location_type}"
            
            print(f"{i}. {obs.name}")
            print(f"   位置类型：{obs.location_type}")
            print(f"   天文台类型：{obs.observatory_type}")
            print(f"   位置：({obs.latitude:.4f}, {obs.longitude:.4f})")
            print(f"   海拔：{obs.elevation:.1f} 米")
            print(f"   最近城镇：{obs.nearest_town_name} ({obs.distance_to_nearest_town:.1f} 公里)")
            if obs.description:
                print(f"   描述：{obs.description}")
            print()
        
        # 统计信息
        print("=== 统计信息 ===")
        
        # 验证所有结果都是天文台类型
        observatory_count = sum(1 for obs in observatories if obs.is_observatory())
        print(f"天文台总数：{observatory_count} 个")
        
        type_counts = {}
        for obs in observatories:
            if obs.is_observatory():
                obs_type = obs.observatory_type or "未知类型"
                type_counts[obs_type] = type_counts.get(obs_type, 0) + 1
        
        print("天文台类型分布：")
        for obs_type, count in type_counts.items():
            print(f"  {obs_type}: {count} 个")
        
        avg_elevation = sum(obs.elevation for obs in observatories) / len(observatories)
        print(f"平均海拔：{avg_elevation:.1f} 米")
        
        max_elevation_obs = max(observatories, key=lambda x: x.elevation)
        print(f"最高海拔天文台：{max_elevation_obs.name} ({max_elevation_obs.elevation:.1f} 米)")
        
    except Exception as e:
        print(f"搜索过程中发生错误：{e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()