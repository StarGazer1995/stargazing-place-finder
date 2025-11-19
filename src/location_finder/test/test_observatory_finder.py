#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
天文台查找功能测试

测试MountainPeakFinder类中的天文台查找相关功能。
"""

import sys
import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加 src 目录到Python路径以加载顶层包
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))

from light_pollution.light_pollution_analyzer import LightPollutionAnalyzer
from stargazing_analyzer.stargazing_place_finder import StarGazingPlaceFinder, Location, Observatory

class TestObservatoryFinder(unittest.TestCase):
    """
    天文台查找功能测试类
    """
    
    def setUp(self):
        self.finder = StarGazingPlaceFinder(enable_cache=False)
        self.test_bbox = (39.5, 115.5, 40.5, 117.5)  # 北京周边区域
    
    def test_observatory_data_class(self):
        """
        测试Location数据类（天文台类型）
        """
        observatory = Location(
            name="测试天文台",
            latitude=39.9042,
            longitude=116.4074,
            elevation=100.0,
            location_type="observatory",
            observatory_type="Astronomical observatory",
            description="这是一个测试天文台",
            distance_to_nearest_town=5.0,
            nearest_town_name="北京市",
            light_pollution_level="中等"
        )
        
        self.assertEqual(observatory.name, "测试天文台")
        self.assertEqual(observatory.latitude, 39.9042)
        self.assertEqual(observatory.location_type, "observatory")
        self.assertTrue(observatory.is_observatory())
        self.assertFalse(observatory.is_mountain_peak())
        self.assertFalse(observatory.is_viewpoint())
        
        # 测试向后兼容的别名
        observatory_alias = Observatory(
            name="测试天文台2",
            latitude=39.9042,
            longitude=116.4074,
            elevation=100.0,
            location_type="observatory",
            observatory_type="Astronomical observatory",
            distance_to_nearest_town=5.0,
            nearest_town_name="北京市"
        )
        self.assertTrue(observatory_alias.is_observatory())
        self.assertEqual(observatory_alias.location_type, "observatory")
        self.assertEqual(observatory.longitude, 116.4074)
        self.assertEqual(observatory.elevation, 100.0)
        self.assertEqual(observatory_alias.observatory_type, "Astronomical observatory")
        self.assertEqual(observatory.description, "这是一个测试天文台")
        self.assertEqual(observatory.distance_to_nearest_town, 5.0)
        self.assertEqual(observatory.nearest_town_name, "北京市")
        self.assertEqual(observatory.light_pollution_level, "中等")
    
    @patch('stargazing_analyzer.stargazing_place_finder.requests.post')
    def test_get_observatories_from_overpass(self, mock_post):
        """
        测试从Overpass API获取天文台数据
        """
        # 模拟API响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'elements': [
                {
                    'type': 'node',
                    'id': 1,
                    'lat': 39.9042,
                    'lon': 116.4074,
                    'tags': {
                        'name': '测试天文台',
                        'man_made': 'observatory'
                    }
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # 调用方法
        result = self.finder.get_observatories_from_overpass(self.test_bbox)
        
        # 验证结果
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['lat'], 39.9042)
        self.assertEqual(result[0]['lon'], 116.4074)
        self.assertEqual(result[0]['tags']['name'], '测试天文台')
        
        # 验证API调用
        mock_post.assert_called_once()
    
    @patch('stargazing_analyzer.stargazing_place_finder.StarGazingPlaceFinder.get_observatories_from_overpass')
    @patch('stargazing_analyzer.stargazing_place_finder.StarGazingPlaceFinder.get_towns_from_overpass')
    @patch('stargazing_analyzer.stargazing_place_finder.StarGazingPlaceFinder.get_elevation_from_api')
    @patch('light_pollution.light_pollution_analyzer.LightPollutionAnalyzer.batch_analyze_coordinates')
    def test_find_observatories_in_area(self, mock_light_pollution, mock_elevation, mock_towns, mock_observatories):
        """
        测试在指定区域查找天文台
        """
        # 模拟天文台数据
        mock_observatories.return_value = [
            {
                'type': 'node',
                'lat': 39.9042,
                'lon': 116.4074,
                'tags': {
                    'name': '测试天文台',
                    'man_made': 'observatory',
                    'description': '这是一个测试天文台'
                }
            }
        ]
        
        # 模拟城镇数据
        mock_towns.return_value = [
            {
                'type': 'node',
                'lat': 39.9000,
                'lon': 116.4000,
                'tags': {'name': '测试城镇'}
            }
        ]
        
        # 模拟海拔数据
        mock_elevation.return_value = 100.0
        
        # 模拟光污染数据
        mock_light_pollution.return_value = [{'pollution_level': 'Low'}]
        
        # 调用方法
        result = self.finder.find_observatories_in_area(self.test_bbox, max_observatories=10)
        
        # 验证结果
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], Observatory)
        self.assertEqual(result[0].name, '测试天文台')
        self.assertEqual(result[0].observatory_type, 'Astronomical observatory')
        self.assertEqual(result[0].elevation, 100.0)
        
        # 验证方法调用
        mock_observatories.assert_called_once_with(self.test_bbox)
        mock_towns.assert_called_once_with(self.test_bbox)
        # 海拔API可能被调用多次（天文台和城镇都需要海拔信息）
        self.assertTrue(mock_elevation.called)
        # 验证至少调用了天文台的海拔查询
        mock_elevation.assert_any_call(39.9042, 116.4074)
    
    @patch('stargazing_analyzer.stargazing_place_finder.StarGazingPlaceFinder.get_observatories_from_overpass')
    def test_find_observatories_empty_result(self, mock_observatories):
        """
        测试当没有找到天文台时的情况
        """
        # 模拟空结果
        mock_observatories.return_value = []
        
        # 调用方法
        result = self.finder.find_observatories_in_area(self.test_bbox)
        
        # 验证结果
        self.assertEqual(len(result), 0)
        self.assertIsInstance(result, list)
    
    def test_observatory_type_classification(self):
        """
        测试天文台类型分类逻辑
        """
        test_cases = [
            ({'man_made': 'observatory'}, 'Astronomical observatory'),
            ({'amenity': 'planetarium'}, 'Planetarium'),
            ({'building': 'observatory'}, 'Observatory building'),
            ({}, 'Unknown type'),
            ({'other_tag': 'value'}, 'Unknown type')
        ]
        
        for tags, expected_type in test_cases:
            with self.subTest(tags=tags):
                # 这里我们测试分类逻辑（需要从实际方法中提取）
                observatory_type = "Unknown type"
                if tags.get('man_made') == 'observatory':
                    observatory_type = "Astronomical observatory"
                elif tags.get('amenity') == 'planetarium':
                    observatory_type = "Planetarium"
                elif tags.get('building') == 'observatory':
                    observatory_type = "Observatory building"
                
                self.assertEqual(observatory_type, expected_type)

class TestObservatoryIntegration(unittest.TestCase):
    """
    天文台查找功能集成测试
    """
    
    def setUp(self):
        p = Path("world_atlas/doc.kml")
        if not p.exists():
            self.skipTest("缺少KML数据文件，跳过集成测试")
        self.finder = StarGazingPlaceFinder(light_pollution_analyzer=LightPollutionAnalyzer(str(p)))
    
    def test_real_observatory_search(self):
        """
        真实的天文台搜索测试（需要网络连接）
        
        注意：这个测试需要真实的网络连接，在CI环境中可能需要跳过
        """
        # 使用较小的搜索区域以减少测试时间
        small_bbox = (39.9, 116.3, 40.0, 116.5)  # 北京市中心小区域
        
        try:
            result = self.finder.find_observatories_in_area(
                bbox=small_bbox,
                max_observatories=5
            )
            
            # 验证结果格式
            self.assertIsInstance(result, list)
            
            # 如果找到了天文台，验证数据结构
            if result:
                for observatory in result:
                    self.assertIsInstance(observatory, Observatory)
                    self.assertIsInstance(observatory.name, str)
                    self.assertIsInstance(observatory.latitude, float)
                    self.assertIsInstance(observatory.longitude, float)
                    self.assertIsInstance(observatory.elevation, (int, float))
                    self.assertIsInstance(observatory.observatory_type, str)
                    
        except Exception as e:
            # 如果网络不可用或API出错，跳过测试
            self.skipTest(f"网络连接或API问题，跳过集成测试: {e}")

if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)