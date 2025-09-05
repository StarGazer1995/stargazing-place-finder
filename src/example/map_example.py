#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光污染地图可视化示例

这个脚本演示了如何使用LightPollutionMap类在真实地图上可视化光污染数据。
"""

import os
import sys
# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from light_pollution_map import LightPollutionMap


def main():
    """
    光污染地图可视化功能演示主函数
    
    展示LightPollutionMap和StyledMapGenerator类的完整使用流程
    包括多种地图类型的生成和可视化效果对比
    
    演示功能：
    1. 初始化地图可视化器并获取统计信息
    2. 生成传统样式的综合地图分析报告
    3. 生成现代化样式的地图可视化
    4. 创建多种地图类型的对比展示
    5. 生成完整的索引页面和使用说明
    
    地图类型：
    - 热力图：连续的光污染强度分布
    - 标记点地图：具体观测点的详细信息
    - 聚类地图：密集区域的聚合显示
    - 样式化地图：基于HTML的现代化界面
    
    输出内容：
    - 多种格式的地图文件
    - 完整的索引页面
    - 详细的使用说明和颜色图例
    - 统计信息和生成报告
    """
    # KML文件路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    kml_file = os.path.join(project_root, 'world_atlas', 'doc.kml')
    
    try:
        print("=== Light Pollution Map Visualizer Demo ===")
        print("Initializing map visualizer...")
        
        # 初始化地图可视化器
        visualizer = LightPollutionMap(kml_file)
        
        # 获取并打印统计信息
        stats = visualizer.get_statistics()
        print("\n📊 Data Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # 设置输出目录
        output_dir = os.path.join(project_root, 'map_output')
        
        print("\n🗺️ Available map types:")
        print("  1. Heatmap (heatmap) - Shows light pollution intensity distribution")
        print("  2. Marker map (markers) - Shows specific observation point locations")
        print("  3. Cluster map (cluster) - Aggregated display of dense areas")
        print("  4. Comprehensive map (comprehensive) - Generates all types of maps")
        print("  5. Styled map (styled) - Modern HTML-based maps")
        
        # 生成综合地图分析报告（以北京为中心）
        print("\n🚀 Generating comprehensive map analysis report...")
        results = visualizer.create_comprehensive_map(
            center_lat=39.9042,
            center_lon=116.4074,
            radius_km=100.0,
            location_name="北京",
            output_dir=output_dir
        )
        
        # 同时生成样式化地图
        print("\n🎨 Generating styled maps...")
        from styled_map_generator import StyledMapGenerator
        styled_generator = StyledMapGenerator(kml_file)
        styled_output_dir = os.path.join(project_root, 'styled_map_output')
        styled_results = styled_generator.generate_comprehensive_styled_maps(styled_output_dir)
        
        print("\n✅ All maps generated successfully!")
        print("\n📋 Traditional map files:")
        for map_type, path in results.items():
            print(f"  {map_type}: {path}")
        
        print("\n🎨 Styled map files:")
        for map_type, path in styled_results.items():
            print(f"  {map_type}: {path}")
        
        print("\n🌐 Usage:")
        print(f"  Traditional maps: {results.get('index', 'Index page')}")
        print(f"  Styled maps: {styled_results.get('main_map', 'Main page')}")
        
        
    except Exception as e:
        print(f"❌ Error occurred while generating maps: {e}")
        import traceback
        traceback.print_exc()
        



def create_index_page(output_dir: str, index_path: str):
    """
    创建光污染地图可视化的索引页面
    
    生成一个包含所有地图文件链接的HTML索引页面
    提供清晰的导航和使用说明
    
    功能特点：
    1. 自动扫描输出目录中的HTML文件
    2. 按地图类型分类和排序
    3. 提供图标和描述性标签
    4. 包含详细的使用说明
    5. 添加颜色图例和等级说明
    
    页面内容：
    - 地图文件的分类列表
    - 每种地图类型的功能说明
    - 光污染等级的颜色对照表
    - 生成时间和版本信息
    
    Args:
        output_dir (str): 包含地图文件的输出目录路径
        index_path (str): 要生成的索引页面文件路径
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