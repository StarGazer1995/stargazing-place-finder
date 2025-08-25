#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光污染地图可视化示例

这个脚本演示了如何使用LightPollutionMap类在真实地图上可视化光污染数据。
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from light_pollution_map import LightPollutionMap


def main():
    """
    主函数：演示光污染地图的各种功能
    """
    # KML文件路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    kml_file = os.path.join(project_root, 'world_atlas', 'doc.kml')
    
    try:
        print("=== 光污染地图可视化器演示 ===")
        print("正在初始化地图可视化器...")
        
        # 初始化地图可视化器
        visualizer = LightPollutionMap(kml_file)
        
        # 获取并打印统计信息
        stats = visualizer.get_statistics()
        print("\n📊 数据统计:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # 设置输出目录
        output_dir = os.path.join(project_root, 'map_output')
        
        print("\n🗺️ 可用的地图类型:")
        print("  1. 热力图 (heatmap) - 显示光污染强度分布")
        print("  2. 标记点地图 (markers) - 显示具体观测点位置")
        print("  3. 聚类地图 (cluster) - 聚合显示密集区域")
        print("  4. 综合地图 (comprehensive) - 生成所有类型的地图")
        print("  5. 样式化地图 (styled) - 基于HTML风格的现代化地图")
        
        # 生成综合地图分析报告（以北京为中心）
        print("\n🚀 正在生成综合地图分析报告...")
        results = visualizer.create_comprehensive_map(
            center_lat=39.9042,
            center_lon=116.4074,
            radius_km=100.0,
            location_name="北京",
            output_dir=output_dir
        )
        
        # 同时生成样式化地图
        print("\n🎨 正在生成样式化地图...")
        from styled_map_generator import StyledMapGenerator
        styled_generator = StyledMapGenerator(kml_file)
        styled_output_dir = os.path.join(project_root, 'styled_map_output')
        styled_results = styled_generator.generate_comprehensive_styled_maps(styled_output_dir)
        
        print("\n✅ 所有地图生成完成!")
        print("\n📋 传统地图文件:")
        for map_type, path in results.items():
            print(f"  {map_type}: {path}")
        
        print("\n🎨 样式化地图文件:")
        for map_type, path in styled_results.items():
            print(f"  {map_type}: {path}")
        
        print("\n🌐 使用方法:")
        print(f"  传统地图: {results.get('index', '索引页面')}")
        print(f"  样式化地图: {styled_results.get('main_map', '主页面')}")
        
        
    except Exception as e:
        print(f"❌ 生成地图时发生错误: {e}")
        import traceback
        traceback.print_exc()
        



def create_index_page(output_dir: str, index_path: str):
    """
    创建索引页面，列出所有生成的地图文件
    
    Args:
        output_dir: 输出目录
        index_path: 索引页面路径
    """
    html_files = [f for f in os.listdir(output_dir) if f.endswith('.html') and f != 'index.html']
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>光污染地图可视化 - 索引页面</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            h1 { color: #333; }
            .map-list { list-style-type: none; padding: 0; }
            .map-item { 
                margin: 10px 0; 
                padding: 15px; 
                border: 1px solid #ddd; 
                border-radius: 5px;
                background-color: #f9f9f9;
            }
            .map-item a { 
                text-decoration: none; 
                color: #0066cc; 
                font-weight: bold;
            }
            .map-item a:hover { text-decoration: underline; }
            .map-type { 
                color: #666; 
                font-size: 0.9em; 
                margin-top: 5px;
            }
        </style>
    </head>
    <body>
        <h1>🌟 光污染地图可视化结果</h1>
        <p>点击下面的链接查看不同类型的光污染地图可视化结果：</p>
        
        <ul class="map-list">
    """
    
    # 按类型分组
    map_types = {
        'heatmap': '🔥 热力图',
        'markers': '📍 标记点地图', 
        'cluster': '🗂️ 聚类地图'
    }
    
    for html_file in sorted(html_files):
        file_type = 'unknown'
        type_icon = '🗺️'
        
        for map_type, icon in map_types.items():
            if map_type in html_file:
                file_type = map_type
                type_icon = icon
                break
        
        # 提取地点名称
        location = html_file.split('_')[0] if '_' in html_file else html_file.replace('.html', '')
        
        html_content += f"""
            <li class="map-item">
                <a href="{html_file}" target="_blank">{location} - {type_icon}</a>
                <div class="map-type">文件: {html_file}</div>
            </li>
        """
    
    html_content += """
        </ul>
        
        <h2>📖 使用说明</h2>
        <ul>
            <li><strong>热力图 🔥</strong>: 显示连续的光污染强度分布，颜色越深表示光污染越严重</li>
            <li><strong>标记点地图 📍</strong>: 显示具体采样点的详细光污染信息，点击标记查看详情</li>
            <li><strong>聚类地图 🗂️</strong>: 自动聚合相近的标记点，适合查看大量数据</li>
        </ul>
        
        <h2>🎨 颜色说明</h2>
        <ul>
            <li><span style="color: #001f3f;">■</span> 深蓝色: 最佳观星条件 (等级 1-2)</li>
            <li><span style="color: #2ECC40;">■</span> 绿色: 良好观星条件 (等级 3-4)</li>
            <li><span style="color: #FF851B;">■</span> 橙色: 一般观星条件 (等级 5-6)</li>
            <li><span style="color: #FF4136;">■</span> 红色: 较差观星条件 (等级 7+)</li>
        </ul>
        
        <p><em>生成时间: """ + str(os.path.getctime(output_dir)) + """</em></p>
    </body>
    </html>
    """
    
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html_content)


if __name__ == "__main__":
    main()