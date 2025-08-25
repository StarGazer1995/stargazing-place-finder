#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光污染可视化示例

这个脚本演示了如何使用LightPollutionVisualizer类来可视化指定地点周围的光污染情况。
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from light_pollution_visualizer import LightPollutionVisualizer


def main():
    """
    主函数：演示光污染可视化功能
    """
    # KML文件路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    kml_file = os.path.join(project_root, 'world_atlas', 'doc.kml')
    
    try:
        print("=== 光污染可视化示例 ===")
        print("正在初始化可视化器...")
        
        # 初始化可视化器
        visualizer = LightPollutionVisualizer(kml_file)
        
        # 显示统计信息
        stats = visualizer.get_statistics()
        print(f"\n=== 可视化器统计信息 ===")
        print(f"分析器统计: {stats['analyzer_stats']}")
        print(f"可用颜色等级: {stats['available_colors']}")
        
        # 测试地点列表
        test_locations = [
            (39.9042, 116.4074, "北京"),
            (31.2304, 121.4737, "上海"),
            (40.7128, -74.0060, "纽约"),
            (51.5074, -0.1278, "伦敦"),
            (35.6762, 139.6503, "东京")
        ]
        
        print("\n=== 可视化选项 ===")
        print("1. 生成单个地点的热力图")
        print("2. 生成单个地点的等高线图")
        print("3. 生成单个地点的散点图")
        print("4. 生成综合分析报告")
        print("5. 批量生成多个地点的可视化")
        
        # 选择测试模式
        print("\n请选择测试模式 (1-5):")
        print("由于这是自动化示例，将执行模式4：生成综合分析报告")
        
        # 选择测试地点
        test_location = test_locations[0]  # 使用北京作为示例
        lat, lon, name = test_location
        
        print(f"\n=== 为 {name} 生成综合分析报告 ===")
        print(f"坐标: ({lat}°, {lon}°)")
        print(f"分析半径: 10km")
        
        # 创建输出目录
        output_dir = os.path.join(project_root, 'visualization_output')
        
        # 生成综合报告
        results = visualizer.create_comprehensive_report(
            center_lat=lat,
            center_lon=lon,
            radius_km=10.0,
            location_name=name,
            output_dir=output_dir
        )
        
        print("\n=== 生成结果 ===")
        for chart_type, result in results.items():
            print(f"{chart_type}: {result}")
        
        # 演示单独的可视化功能
        print("\n=== 演示单独功能 ===")
        
        # 1. 热力图示例
        print("\n1. 生成热力图...")
        heatmap_result = visualizer.create_heatmap(
            center_lat=lat,
            center_lon=lon,
            radius_km=5.0,  # 使用较小半径以加快处理
            grid_size=30,   # 使用较小网格以加快处理
            save_path=os.path.join(output_dir, f"{name}_demo_heatmap.png"),
            show_plot=False
        )
        print(f"热力图结果: {heatmap_result}")
        
        # 2. 等高线图示例
        print("\n2. 生成等高线图...")
        contour_result = visualizer.create_contour_map(
            center_lat=lat,
            center_lon=lon,
            radius_km=5.0,
            grid_size=30,
            save_path=os.path.join(output_dir, f"{name}_demo_contour.png"),
            show_plot=False
        )
        print(f"等高线图结果: {contour_result}")
        
        # 3. 散点图示例
        print("\n3. 生成散点图...")
        scatter_result = visualizer.create_scatter_plot(
            center_lat=lat,
            center_lon=lon,
            radius_km=5.0,
            sample_points=100,  # 使用较少采样点以加快处理
            save_path=os.path.join(output_dir, f"{name}_demo_scatter.png"),
            show_plot=False
        )
        print(f"散点图结果: {scatter_result}")
        
        # 演示不同半径的比较
        print("\n=== 不同半径比较 ===")
        
        radii = [5, 10, 15]  # 不同半径
        for radius in radii:
            print(f"\n生成半径 {radius}km 的热力图...")
            result = visualizer.create_heatmap(
                center_lat=lat,
                center_lon=lon,
                radius_km=radius,
                grid_size=25,  # 使用较小网格
                save_path=os.path.join(output_dir, f"{name}_radius_{radius}km_heatmap.png"),
                show_plot=False
            )
            print(f"半径 {radius}km 结果: {result}")
        
        # 演示多地点快速比较
        print("\n=== 多地点快速比较 ===")
        
        for i, (test_lat, test_lon, test_name) in enumerate(test_locations[:3]):  # 只测试前3个地点
            print(f"\n{i+1}/3 处理 {test_name}...")
            
            try:
                result = visualizer.create_heatmap(
                    center_lat=test_lat,
                    center_lon=test_lon,
                    radius_km=8.0,
                    grid_size=20,  # 使用更小网格以加快处理
                    save_path=os.path.join(output_dir, f"{test_name}_quick_heatmap.png"),
                    show_plot=False
                )
                print(f"{test_name} 处理完成: {result}")
                
            except Exception as e:
                print(f"{test_name} 处理失败: {e}")
        
        # 生成使用说明
        print("\n=== 使用说明 ===")
        print("1. 热力图: 显示连续的光污染强度分布")
        print("2. 等高线图: 显示光污染强度的等值线")
        print("3. 散点图: 显示采样点的光污染数据")
        print("4. 综合报告: 包含所有类型的可视化图表")
        print("\n颜色说明:")
        print("- 深蓝色: 最佳观星条件 (Class 1-2)")
        print("- 绿色/黄色: 一般观星条件 (Class 3-5)")
        print("- 橙色/红色: 较差到极差观星条件 (Class 6-7+)")
        
        print(f"\n=== 可视化完成 ===")
        print(f"所有图表已保存到: {output_dir}")
        print("\n建议:")
        print("1. 查看热力图了解整体光污染分布")
        print("2. 查看等高线图了解污染强度梯度")
        print("3. 查看散点图了解具体采样点数据")
        print("4. 比较不同半径的结果选择最佳观星位置")
        
    except FileNotFoundError:
        print(f"错误: 找不到KML文件 {kml_file}")
        print("请确保文件路径正确")
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()