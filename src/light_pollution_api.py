#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光污染数据API服务器

这个模块提供了一个Flask API服务器，用于根据地图视窗范围动态获取光污染图像数据。
"""

import os
import sys
import json
import math
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import Dict, List, Tuple, Any, Optional

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from .light_pollution_analyzer import LightPollutionAnalyzer
    from .stargazing_location_analyzer import analyze_stargazing_area
except ImportError:
    from light_pollution_analyzer import LightPollutionAnalyzer
    from stargazing_location_analyzer import analyze_stargazing_area

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 全局光污染分析器实例
analyzer = None

def init_analyzer():
    """
    初始化光污染分析器
    """
    global analyzer
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        kml_file = os.path.join(project_root, 'world_atlas', 'doc.kml')
        
        print(f"正在初始化光污染分析器...")
        print(f"KML文件路径: {kml_file}")
        
        analyzer = LightPollutionAnalyzer(kml_file)
        print(f"✅ 光污染分析器初始化完成")
        
        # 显示统计信息
        stats = analyzer.get_statistics()
        print(f"覆盖层数量: {stats['count']}")
        print(f"图像基础路径: {stats['images_base_path']}")
        print(f"图像目录是否存在: {stats['images_directory_exists']}")
        
    except Exception as e:
        print(f"❌ 光污染分析器初始化失败: {e}")
        analyzer = None

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    计算两个地理坐标之间的距离（公里）
    
    Args:
        lat1, lon1: 第一个点的纬度和经度
        lat2, lon2: 第二个点的纬度和经度
        
    Returns:
        距离（公里）
    """
    # 使用Haversine公式计算距离
    R = 6371  # 地球半径（公里）
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def get_pollution_level_description(bortle: int) -> str:
    """
    根据波特尔等级获取描述
    
    Args:
        bortle: 波特尔等级 (1-9)
        
    Returns:
        等级描述
    """
    descriptions = {
        1: "优秀暗空",
        2: "典型暗空", 
        3: "乡村天空",
        4: "乡村/郊区过渡",
        5: "郊区天空",
        6: "明亮郊区",
        7: "郊区/城市过渡",
        8: "城市天空",
        9: "内城天空"
    }
    return descriptions.get(bortle, "未知等级")

def brightness_to_bortle(brightness: int) -> int:
    """
    将亮度值转换为波特尔等级
    
    Args:
        brightness: 亮度值 (0-255)
        
    Returns:
        波特尔等级 (1-9)
    """
    # 将0-255的亮度值映射到1-9的波特尔等级
    # 亮度越高，光污染越严重，波特尔等级越高
    if brightness <= 28:  # 0-28
        return 1
    elif brightness <= 56:  # 29-56
        return 2
    elif brightness <= 84:  # 57-84
        return 3
    elif brightness <= 112:  # 85-112
        return 4
    elif brightness <= 140:  # 113-140
        return 5
    elif brightness <= 168:  # 141-168
        return 6
    elif brightness <= 196:  # 169-196
        return 7
    elif brightness <= 224:  # 197-224
        return 8
    else:  # 225-255
        return 9

def bortle_to_sqm(bortle: int) -> float:
    """
    将波特尔等级转换为SQM值（每平方角秒星等）
    根据标准的波特尔-SQM对应关系
    
    Args:
        bortle: 波特尔等级 (1-9)
        
    Returns:
        SQM值
    """
    # 波特尔等级与SQM值的标准对应关系
    sqm_values = {
        1: 21.9,  # 优秀暗空 (21.7-22.0)
        2: 21.6,  # 典型暗空 (21.5-21.6)
        3: 21.3,  # 乡村天空 (21.3-21.4)
        4: 20.4,  # 乡村/郊区过渡 (20.4-21.2)
        5: 19.5,  # 郊区天空 (19.1-20.3)
        6: 18.5,  # 明亮郊区 (18.0-19.0)
        7: 17.5,  # 郊区/城市过渡 (17.0-18.0)
        8: 16.5,  # 城市天空 (16.0-17.0)
        9: 15.5   # 内城天空 (<16.0)
    }
    return sqm_values.get(bortle, 20.0)

@app.route('/api/light_pollution', methods=['GET'])
def get_light_pollution_data():
    """
    获取指定边界范围内的光污染数据
    
    查询参数:
        north: 北边界纬度
        south: 南边界纬度
        east: 东边界经度
        west: 西边界经度
        zoom: 地图缩放级别（可选，默认为10）
    
    Returns:
        JSON格式的光污染数据数组
    """
    if analyzer is None:
        return jsonify({
            'error': '光污染分析器未初始化',
            'data': []
        }), 500
    
    try:
        # 获取查询参数
        north = float(request.args.get('north', 0))
        south = float(request.args.get('south', 0))
        east = float(request.args.get('east', 0))
        west = float(request.args.get('west', 0))
        zoom = int(request.args.get('zoom', 10))
        
        print(f"🌍 获取光污染数据: 边界=({south}, {west}) 到 ({north}, {east}), 缩放={zoom}")
        
        # 根据缩放级别确定网格分辨率
        if zoom <= 8:
            grid_resolution = 0.1  # 低缩放级别，粗网格
        elif zoom <= 12:
            grid_resolution = 0.05  # 中等缩放级别
        elif zoom <= 16:
            grid_resolution = 0.02  # 高缩放级别
        else:
            grid_resolution = 0.01  # 非常高缩放级别，细网格
        
        # 计算网格范围
        lat_range = north - south
        lng_range = east - west
        grid_rows = max(1, int(lat_range / grid_resolution))
        grid_cols = max(1, int(lng_range / grid_resolution))
        
        # 限制最大网格数量以避免性能问题
        max_points = 2000
        total_points = grid_rows * grid_cols
        
        if total_points > max_points:
            # 调整网格分辨率
            scale_factor = math.sqrt(max_points / total_points)
            grid_rows = max(1, int(grid_rows * scale_factor))
            grid_cols = max(1, int(grid_cols * scale_factor))
            print(f"⚠️ 网格点数过多，已调整为 {grid_rows}x{grid_cols} = {grid_rows * grid_cols}个点")
        
        print(f"🔢 生成网格: {grid_rows}x{grid_cols} = {grid_rows * grid_cols}个点")
        
        data = []
        point_index = 0
        
        # 生成网格点并获取光污染数据
        for row in range(grid_rows):
            for col in range(grid_cols):
                # 计算网格点坐标
                lat = south + (row + 0.5) * (lat_range / grid_rows)
                lng = west + (col + 0.5) * (lng_range / grid_cols)
                
                try:
                    # 从光污染分析器获取真实数据
                    pollution_info = analyzer.get_light_pollution_color(lat, lng)
                    
                    if pollution_info:
                        # 从真实数据中提取信息
                        brightness = pollution_info['brightness']
                        bortle = brightness_to_bortle(brightness)
                        sqm = bortle_to_sqm(bortle)
                        intensity = brightness / 255.0
                        
                        data.append({
                            'name': f'数据点 {point_index + 1}',
                            'lat': lat,
                            'lng': lng,
                            'bortle': bortle,
                            'sqm': f'{sqm:.1f}',
                            'intensity': intensity,
                            'brightness': brightness,
                            'rgb': pollution_info['rgb'],
                            'hex': pollution_info['hex'],
                            'overlay_name': pollution_info['overlay_name']
                        })
                    else:
                        # 如果没有找到数据，使用默认值
                        data.append({
                            'name': f'数据点 {point_index + 1}',
                            'lat': lat,
                            'lng': lng,
                            'bortle': 5,  # 默认中等光污染
                            'sqm': '20.0',
                            'intensity': 0.5,
                            'brightness': 128,
                            'rgb': [128, 128, 128],
                            'hex': '#808080',
                            'overlay_name': '默认数据'
                        })
                        
                except Exception as e:
                    print(f"⚠️ 获取坐标 ({lat:.4f}, {lng:.4f}) 的数据时出错: {e}")
                    # 使用默认值
                    data.append({
                        'name': f'数据点 {point_index + 1}',
                        'lat': lat,
                        'lng': lng,
                        'bortle': 5,
                        'sqm': '20.0',
                        'intensity': 0.5,
                        'brightness': 128,
                        'rgb': [128, 128, 128],
                        'hex': '#808080',
                        'overlay_name': '默认数据'
                    })
                
                point_index += 1
        
        print(f"✅ 成功获取 {len(data)} 个光污染数据点")
        
        return jsonify({
            'success': True,
            'data': data,
            'metadata': {
                'bounds': {
                    'north': north,
                    'south': south,
                    'east': east,
                    'west': west
                },
                'zoom': zoom,
                'grid_resolution': grid_resolution,
                'total_points': len(data)
            }
        })
        
    except Exception as e:
        print(f"❌ 获取光污染数据时出错: {e}")
        return jsonify({
            'error': str(e),
            'data': []
        }), 500

@app.route('/api/light_pollution_images', methods=['GET'])
def get_light_pollution_images():
    """
    获取指定地理边界内的光污染图片数据
    
    查询参数:
    - north: 北边界纬度
    - south: 南边界纬度
    - east: 东边界经度
    - west: 西边界经度
    
    返回:
    - 包含图片信息的JSON数组
    """
    global analyzer
    
    if analyzer is None:
        return jsonify({'error': '光污染分析器未初始化'}), 500
    
    try:
        # 获取查询参数
        north = request.args.get('north', type=float)
        south = request.args.get('south', type=float)
        east = request.args.get('east', type=float)
        west = request.args.get('west', type=float)
        
        # 验证参数
        if any(param is None for param in [north, south, east, west]):
            return jsonify({
                'error': '缺少必需的参数: north, south, east, west'
            }), 400
        
        # 验证坐标范围
        if not (-90 <= north <= 90) or not (-90 <= south <= 90):
            return jsonify({'error': '纬度必须在-90到90之间'}), 400
        
        if not (-180 <= east <= 180) or not (-180 <= west <= 180):
            return jsonify({'error': '经度必须在-180到180之间'}), 400
        
        if north <= south:
            return jsonify({'error': '北边界必须大于南边界'}), 400
        
        print(f"获取光污染图片数据: 北{north}° 南{south}° 东{east}° 西{west}°")
        
        # 获取指定区域内的光污染图片数据
        images_data = analyzer.get_light_pollution_images_in_bounds(north, south, east, west)
        
        # 处理返回数据，移除不能序列化的对象
        processed_data = []
        for item in images_data:
            processed_item = {
                'name': item['name'],
                'image_path': item['image_path'],
                'image_data': item['image_data'],
                'bounds': item['bounds'],
                'exists': item['exists']
            }
            processed_data.append(processed_item)
        
        print(f"✅ 成功获取 {len(processed_data)} 个光污染图片")
        
        return jsonify({
            'success': True,
            'count': len(processed_data),
            'images': processed_data,
            'query_bounds': {
                'north': north,
                'south': south,
                'east': east,
                'west': west
            }
        })
        
    except Exception as e:
        print(f"❌ 获取光污染图片数据时出错: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'服务器内部错误: {str(e)}'}), 500

@app.route('/api/coordinate_analysis', methods=['GET'])
def analyze_coordinate():
    """
    分析单个坐标点的光污染数据
    
    查询参数:
        lat: 纬度
        lng: 经度
    
    Returns:
        JSON格式的光污染分析结果
    """
    if analyzer is None:
        return jsonify({
            'error': '光污染分析器未初始化',
            'success': False
        }), 500
    
    try:
        # 获取查询参数
        lat = float(request.args.get('lat', 0))
        lng = float(request.args.get('lng', 0))
        
        print(f"🎯 分析坐标点: ({lat}, {lng})")
        
        # 使用光污染分析器获取真实数据
        pollution_info = analyzer.get_light_pollution_color(lat, lng)
        
        if pollution_info:
            # 从真实数据中提取信息
            brightness = pollution_info['brightness']
            bortle = brightness_to_bortle(brightness)
            sqm = bortle_to_sqm(bortle)
            intensity = brightness / 255.0
            description = get_pollution_level_description(bortle)
            
            result = {
                'success': True,
                'data': {
                    'coordinates': {
                        'lat': lat,
                        'lng': lng
                    },
                    'light_pollution': {
                        'bortle_class': bortle,
                        'sqm_value': round(sqm, 1),
                        'intensity': round(intensity, 3),
                        'brightness': brightness,
                        'description': description
                    },
                    'color_info': {
                        'rgb': pollution_info['rgb'],
                        'hex': pollution_info['hex']
                    },
                    'source': {
                        'overlay_name': pollution_info['overlay_name'],
                        'data_type': 'real_data'
                    }
                }
            }
            
            print(f"✅ 成功分析坐标点: 波特尔等级={bortle}, SQM={sqm:.1f}")
            return jsonify(result)
        else:
            # 如果没有找到数据，返回默认值
            result = {
                'success': True,
                'data': {
                    'coordinates': {
                        'lat': lat,
                        'lng': lng
                    },
                    'light_pollution': {
                        'bortle_class': 5,
                        'sqm_value': 20.0,
                        'intensity': 0.5,
                        'brightness': 128,
                        'description': get_pollution_level_description(5)
                    },
                    'color_info': {
                        'rgb': [128, 128, 128],
                        'hex': '#808080'
                    },
                    'source': {
                        'overlay_name': '默认数据',
                        'data_type': 'default_data'
                    }
                },
                'warning': '该坐标点没有找到光污染数据，使用默认值'
            }
            
            print(f"⚠️ 坐标点 ({lat}, {lng}) 没有找到数据，使用默认值")
            return jsonify(result)
            
    except ValueError as e:
        return jsonify({
            'error': '无效的坐标参数',
            'success': False,
            'details': str(e)
        }), 400
        
    except Exception as e:
        print(f"❌ 分析坐标点时出错: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@app.route('/api/analyze_stargazing_area', methods=['GET', 'POST', 'OPTIONS'])
def analyze_stargazing_area_endpoint():
    """
    分析指定区域的观星地点
    
    参数:
        south: 南边界纬度
        west: 西边界经度  
        north: 北边界纬度
        east: 东边界经度
        max_peaks: 最大山峰数量（可选，默认30）
        min_height_diff: 最小高度差（可选，默认100.0）
        road_radius_km: 道路搜索半径（可选，默认10.0）
    """
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        # 根据请求方法获取参数
        if request.method == 'POST':
            # POST请求从JSON body获取参数
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'Missing JSON data',
                    'message': '缺少JSON数据'
                }), 400
            
            bbox = data.get('bbox', {})
            south = float(bbox.get('south', 0))
            west = float(bbox.get('west', 0))
            north = float(bbox.get('north', 0))
            east = float(bbox.get('east', 0))
            max_peaks = int(data.get('max_peaks', 30))
            min_height_diff = float(data.get('min_height_diff', 100.0))
            road_radius_km = float(data.get('road_radius_km', 10.0))
            network_type = data.get('network_type', 'drive')
            include_light_pollution = data.get('include_light_pollution', True)
            include_road_connectivity = data.get('include_road_connectivity', True)
        else:
            # GET请求从URL参数获取
            south = float(request.args.get('south', 0))
            west = float(request.args.get('west', 0))
            north = float(request.args.get('north', 0))
            east = float(request.args.get('east', 0))
            max_peaks = int(request.args.get('max_peaks', 30))
            min_height_diff = float(request.args.get('min_height_diff', 100.0))
            road_radius_km = float(request.args.get('road_radius_km', 10.0))
            network_type = request.args.get('network_type', 'drive')
            include_light_pollution = request.args.get('include_light_pollution', 'true').lower() == 'true'
            include_road_connectivity = request.args.get('include_road_connectivity', 'true').lower() == 'true'
        
        print(f"分析观星区域: 北{north}° 南{south}° 东{east}° 西{west}°")
        
        # 获取KML文件路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        kml_file = os.path.join(project_root, 'world_atlas', 'doc.kml')
        
        # 调用分析函数
        locations = analyze_stargazing_area(
            south=south,
            west=west, 
            north=north,
            east=east,
            kml_file_path=kml_file if os.path.exists(kml_file) else None,
            max_peaks=max_peaks,
            min_height_diff=min_height_diff,
            road_radius_km=road_radius_km
        )
        
        # 转换为JSON格式
        locations_data = []
        for loc in locations:
            loc_dict = {
                'name': loc.name,
                'latitude': loc.latitude,
                'longitude': loc.longitude,
                'elevation': loc.elevation,
                'prominence': loc.prominence,
                'distance_to_nearest_town': loc.distance_to_nearest_town,
                'nearest_town_name': loc.nearest_town_name,
                'height_difference': loc.height_difference,
                'light_pollution_rgb': loc.light_pollution_rgb,
                'light_pollution_hex': loc.light_pollution_hex,
                'light_pollution_brightness': loc.light_pollution_brightness,
                'light_pollution_level': loc.light_pollution_level,
                'light_pollution_overlay': loc.light_pollution_overlay,
                'road_accessible': loc.road_accessible,
                'distance_to_road_km': loc.distance_to_road_km,
                'road_network_type': loc.road_network_type,
                'road_check_error': loc.road_check_error,
                'stargazing_score': loc.stargazing_score,
                'recommendation_level': loc.recommendation_level,
                'analysis_notes': loc.analysis_notes
            }
            locations_data.append(loc_dict)
        
        print(f"✅ 成功分析 {len(locations_data)} 个观星地点")
        
        return jsonify({
            'success': True,
            'count': len(locations_data),
            'locations': locations_data,
            'bounds': {
                'south': south,
                'west': west,
                'north': north,
                'east': east
            }
        })
        
    except Exception as e:
        print(f"❌ 观星区域分析失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '观星区域分析失败'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    健康检查端点
    """
    return jsonify({
        'status': 'healthy',
        'analyzer_initialized': analyzer is not None
    })

if __name__ == '__main__':
    # 初始化分析器
    init_analyzer()
    
    # 启动Flask服务器
    print("🚀 启动光污染数据API服务器...")
    print("📡 API端点:")
    print("  - GET /api/light_pollution - 获取光污染数据")
    print("  - GET /api/light_pollution_images - 获取光污染图片数据")
    print("  - GET /api/coordinate_analysis - 分析单个坐标点")
    print("  - GET/POST /api/analyze_stargazing_area - 分析观星区域")
    print("  - GET /api/health - 健康检查")
    print("🌐 服务器地址: http://localhost:5001")
    
    app.run(host='0.0.0.0', port=5001, debug=True)