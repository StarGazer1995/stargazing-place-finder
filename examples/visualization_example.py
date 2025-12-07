#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光污染可视化示例

这个脚本演示了如何使用LightPollutionVisualizer类来可视化指定地点周围的光污染情况。
"""

import os
import sys
# 添加 src 目录到Python路径以加载顶层包
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, '..', 'src'))
from light_pollution.light_pollution_visualizer import LightPollutionVisualizer


def main():
    """
    光污染可视化功能演示主函数
    
    演示如何使用LightPollutionVisualizer类进行光污染数据的可视化分析，
    展示多种图表类型和分析方法的完整功能。
    
    演示功能:
    - 初始化光污染可视化器
    - 显示可视化器统计信息
    - 生成综合分析报告（包含多种图表类型）
    - 演示单独的可视化功能（热力图、等高线图、散点图）
    - 不同半径的光污染分布比较
    - 多地点的快速可视化比较
    - 提供详细的使用说明和颜色解释
    
    可视化类型:
    1. 热力图: 显示连续的光污染强度分布，适合整体趋势分析
    2. 等高线图: 显示光污染强度的等值线，便于识别污染边界
    3. 散点图: 显示采样点的具体光污染数据，适合精确分析
    4. 综合报告: 包含所有类型的可视化图表和统计信息
    
    测试地点:
    - 北京 (39.9042°N, 116.4074°E) - 主要演示地点
    - 上海 (31.2304°N, 121.4737°E) - 多地点比较
    - 纽约 (40.7128°N, -74.0060°W) - 多地点比较
    - 伦敦 (51.5074°N, -0.1278°W) - 多地点比较
    - 东京 (35.6762°N, 139.6503°E) - 多地点比较
    
    输出内容:
    - 控制台显示处理进度和结果统计
    - 可视化器统计信息（分析器状态、可用颜色等级）
    - 综合分析报告（多种图表类型的生成结果）
    - 不同半径比较图表（5km、10km、15km）
    - 多地点快速比较图表
    - 详细的使用说明和颜色解释
    
    生成文件:
    - {地点名}_comprehensive_report/ 目录（包含完整的分析报告）
    - {地点名}_demo_heatmap.png（演示热力图）
    - {地点名}_demo_contour.png（演示等高线图）
    - {地点名}_demo_scatter.png（演示散点图）
    - {地点名}_radius_{半径}km_heatmap.png（不同半径比较图）
    - {地点名}_quick_heatmap.png（多地点快速比较图）
    
    前置条件:
    - 需要存在有效的光污染KML数据文件
    - KML文件路径: ../world_atlas/doc.kml
    
    异常处理:
    - 文件不存在异常（FileNotFoundError）
    - 可视化处理异常（单个地点失败不影响其他地点）
    - 提供详细的错误堆栈信息用于调试
    
    应用场景:
    - 观星地点的光污染环境评估
    - 城市光污染分布研究
    - 天文观测条件的可视化分析
    - 光污染数据的教学和演示
    
    注意事项:
    - 可视化过程可能需要较长时间，特别是大半径和高精度设置
    - 生成的图片文件较大，注意存储空间
    - 建议在有足够内存的环境下运行
    - 颜色映射遵循国际光污染等级标准
    """
    # KML文件路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    kml_file = os.path.join(project_root, 'world_atlas', 'doc.kml')
    
    try:
        print("=== Light Pollution Visualization Example ===")
        print("Initializing visualizer...")
        
        # 初始化可视化器
        visualizer = LightPollutionVisualizer(kml_file)
        
        # 显示统计信息
        stats = visualizer.get_statistics()
        print(f"\n=== Visualizer Statistics ===")
        print(f"Analyzer statistics: {stats['analyzer_stats']}")
        print(f"Available color levels: {stats['available_colors']}")
        
        # 测试地点列表
        test_locations = [
            (39.9042, 116.4074, "北京"),
            (31.2304, 121.4737, "上海"),
            (40.7128, -74.0060, "纽约"),
            (51.5074, -0.1278, "伦敦"),
            (35.6762, 139.6503, "东京")
        ]
        
        print("\n=== Visualization Options ===")
        print("1. Generate heatmap for single location")
        print("2. Generate contour map for single location")
        print("3. Generate scatter plot for single location")
        print("4. Generate comprehensive analysis report")
        print("5. Batch generate visualizations for multiple locations")
        
        # 选择测试模式
        print("\nPlease select test mode (1-5):")
        print("Since this is an automated example, will execute mode 4: Generate comprehensive analysis report")
        
        # 选择测试地点
        test_location = test_locations[0]  # 使用北京作为示例
        lat, lon, name = test_location
        
        print(f"\n=== Generating comprehensive analysis report for {name} ===")
        print(f"Coordinates: ({lat}°, {lon}°)")
        print(f"Analysis radius: 10km")
        
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
        
        print("\n=== Generation Results ===")
        for chart_type, result in results.items():
            print(f"{chart_type}: {result}")
        
        # 演示单独的可视化功能
        print("\n=== Demonstrating Individual Functions ===")
        
        # 1. 热力图示例
        print("\n1. Generating heatmap...")
        heatmap_result = visualizer.create_heatmap(
            center_lat=lat,
            center_lon=lon,
            radius_km=5.0,  # 使用较小半径以加快处理
            grid_size=30,   # 使用较小网格以加快处理
            save_path=os.path.join(output_dir, f"{name}_demo_heatmap.png"),
            show_plot=False
        )
        print(f"Heatmap result: {heatmap_result}")
        
        # 2. 等高线图示例
        print("\n2. Generating contour map...")
        contour_result = visualizer.create_contour_map(
            center_lat=lat,
            center_lon=lon,
            radius_km=5.0,
            grid_size=30,
            save_path=os.path.join(output_dir, f"{name}_demo_contour.png"),
            show_plot=False
        )
        print(f"Contour map result: {contour_result}")
        
        # 3. 散点图示例
        print("\n3. Generating scatter plot...")
        scatter_result = visualizer.create_scatter_plot(
            center_lat=lat,
            center_lon=lon,
            radius_km=5.0,
            sample_points=100,  # 使用较少采样点以加快处理
            save_path=os.path.join(output_dir, f"{name}_demo_scatter.png"),
            show_plot=False
        )
        print(f"Scatter plot result: {scatter_result}")
        
        # 演示不同半径的比较
        print("\n=== Different Radius Comparison ===")
        
        radii = [5, 10, 15]  # 不同半径
        for radius in radii:
            print(f"\nGenerating heatmap for radius {radius}km...")
            result = visualizer.create_heatmap(
                center_lat=lat,
                center_lon=lon,
                radius_km=radius,
                grid_size=25,  # 使用较小网格
                save_path=os.path.join(output_dir, f"{name}_radius_{radius}km_heatmap.png"),
                show_plot=False
            )
            print(f"Radius {radius}km result: {result}")
        
        # 演示多地点快速比较
        print("\n=== Multi-location Quick Comparison ===")
        
        for i, (test_lat, test_lon, test_name) in enumerate(test_locations[:3]):  # 只测试前3个地点
            print(f"\n{i+1}/3 Processing {test_name}...")
            
            try:
                result = visualizer.create_heatmap(
                    center_lat=test_lat,
                    center_lon=test_lon,
                    radius_km=8.0,
                    grid_size=20,  # 使用更小网格以加快处理
                    save_path=os.path.join(output_dir, f"{test_name}_quick_heatmap.png"),
                    show_plot=False
                )
                print(f"{test_name} processing completed: {result}")
                
            except Exception as e:
                print(f"{test_name} processing failed: {e}")
        
        # 生成使用说明
        print("\n=== Usage Instructions ===")
        print("1. Heatmap: Shows continuous light pollution intensity distribution")
        print("2. Contour map: Shows contour lines of light pollution intensity")
        print("3. Scatter plot: Shows light pollution data at sampling points")
        print("4. Comprehensive report: Contains all types of visualization charts")
        print("\nColor explanation:")
        print("- Dark blue: Best stargazing conditions (Class 1-2)")
        print("- Green/Yellow: Average stargazing conditions (Class 3-5)")
        print("- Orange/Red: Poor to extremely poor stargazing conditions (Class 6-7+)")
        
        print(f"\n=== Visualization Completed ===")
        print(f"All charts saved to: {output_dir}")
        print("\nRecommendations:")
        print("1. View heatmap to understand overall light pollution distribution")
        print("2. View contour map to understand pollution intensity gradients")
        print("3. View scatter plot to understand specific sampling point data")
        print("4. Compare results from different radii to select optimal stargazing locations")
        
    except FileNotFoundError:
        print(f"Error: Cannot find KML file {kml_file}")
        print("Please ensure the file path is correct")
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()