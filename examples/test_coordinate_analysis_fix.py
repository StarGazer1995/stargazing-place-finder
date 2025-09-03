#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试坐标分析API修复

这个脚本用于验证地图点击事件是否正确调用了后端的coordinate_analysis API。

作者: Assistant
日期: 2024
"""

import requests
import json
from typing import Dict, Any

def test_coordinate_analysis_api(lat: float, lng: float) -> Dict[str, Any]:
    """
    测试坐标分析API
    
    Args:
        lat: 纬度
        lng: 经度
        
    Returns:
        API响应结果
    """
    api_url = f"http://127.0.0.1:5001/api/coordinate_analysis?lat={lat}&lng={lng}"
    
    try:
        print(f"🔍 测试坐标点: ({lat}, {lng})")
        print(f"📡 API URL: {api_url}")
        
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ API调用成功")
            print(f"📊 响应数据: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return result
        else:
            print(f"❌ API调用失败: HTTP {response.status_code}")
            print(f"错误信息: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求失败: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {e}")
        return None

def main():
    """
    主测试函数
    """
    print("🧪 开始测试坐标分析API修复")
    print("=" * 50)
    
    # 测试几个不同的坐标点
    test_coordinates = [
        (40.6515, 116.2848),  # 北京附近
        (31.2304, 121.4737),  # 上海附近
        (39.9042, 116.4074),  # 北京天安门
        (22.3193, 114.1694),  # 香港
    ]
    
    success_count = 0
    total_count = len(test_coordinates)
    
    for i, (lat, lng) in enumerate(test_coordinates, 1):
        print(f"\n📍 测试 {i}/{total_count}:")
        result = test_coordinate_analysis_api(lat, lng)
        
        if result and result.get('success'):
            success_count += 1
            data = result.get('data', {})
            light_pollution = data.get('light_pollution', {})
            
            print(f"🌃 波特尔等级: {light_pollution.get('bortle_class')}")
            print(f"✨ SQM值: {light_pollution.get('sqm_value')}")
            print(f"💡 光污染强度: {light_pollution.get('intensity', 0) * 100:.1f}%")
            print(f"📝 描述: {light_pollution.get('description')}")
        else:
            print(f"❌ 测试失败")
        
        print("-" * 30)
    
    print(f"\n📈 测试总结:")
    print(f"✅ 成功: {success_count}/{total_count}")
    print(f"❌ 失败: {total_count - success_count}/{total_count}")
    
    if success_count == total_count:
        print("🎉 所有测试通过！坐标分析API修复成功！")
    else:
        print("⚠️ 部分测试失败，请检查API服务器状态")

if __name__ == "__main__":
    main()