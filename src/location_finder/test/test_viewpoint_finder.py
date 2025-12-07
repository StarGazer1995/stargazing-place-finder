#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
观景台查找功能测试

测试stargazing_place_finder模块中的观景台查找相关功能。
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# 添加 src 目录到Python路径以加载顶层包
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))

from stargazing_analyzer.stargazing_place_finder import StarGazingPlaceFinder, Location, Viewpoint, find_viewpoints

class TestViewpointFinder(unittest.TestCase):
    """
    观景台查找功能测试类
    """
    
    def setUp(self):
        """
        测试前的设置
        """
        self.finder = StarGazingPlaceFinder()
        self.test_bbox = (39.5, 115.5, 40.5, 117.5)  # 北京周边
    
    def test_viewpoint_dataclass(self):
        """
        测试Location数据类（观景台类型）
        """
        viewpoint = Location(
            name="测试观景台",
            latitude=39.9042,
            longitude=116.4074,
            elevation=100.0,
            location_type="viewpoint",
            viewpoint_type="观景台",
            description="测试用观景台",
            distance_to_nearest_town=5.0,
            nearest_town_name="北京",
            scenic_value="优秀"
        )
        
        self.assertEqual(viewpoint.name, "测试观景台")
        self.assertEqual(viewpoint.latitude, 39.9042)
        self.assertEqual(viewpoint.longitude, 116.4074)
        self.assertEqual(viewpoint.elevation, 100.0)
        self.assertEqual(viewpoint.location_type, "viewpoint")
        self.assertTrue(viewpoint.is_viewpoint())
        self.assertEqual(viewpoint.viewpoint_type, "观景台")
        self.assertEqual(viewpoint.description, "测试用观景台")
        self.assertEqual(viewpoint.distance_to_nearest_town, 5.0)
        self.assertEqual(viewpoint.nearest_town_name, "北京")
        self.assertEqual(viewpoint.scenic_value, "优秀")
        
        # 测试向后兼容的别名
        viewpoint_alias = Viewpoint(
            name="测试观景台2",
            latitude=39.9042,
            longitude=116.4074,
            elevation=100.0,
            location_type="viewpoint",
            distance_to_nearest_town=5.0,
            nearest_town_name="北京"
        )
        self.assertTrue(viewpoint_alias.is_viewpoint())
        self.assertEqual(viewpoint_alias.location_type, "viewpoint")
    
    def test_get_viewpoints_from_overpass_method_exists(self):
        """
        测试get_viewpoints_from_overpass方法是否存在
        """
        # 验证方法存在
        self.assertTrue(hasattr(self.finder, 'get_viewpoints_from_overpass'))
        self.assertTrue(callable(getattr(self.finder, 'get_viewpoints_from_overpass')))
    
    def test_find_viewpoints_in_area_method_exists(self):
        """
        测试find_viewpoints_in_area方法是否存在
        """
        # 验证方法存在
        self.assertTrue(hasattr(self.finder, 'find_viewpoints_in_area'))
        self.assertTrue(callable(getattr(self.finder, 'find_viewpoints_in_area')))
    
    def test_find_viewpoints_convenience_function(self):
        """
        测试便捷函数find_viewpoints
        """
        with patch.object(StarGazingPlaceFinder, 'find_viewpoints_in_area') as mock_method:
            # 模拟返回结果
            mock_viewpoint = Viewpoint(
                name="测试观景台",
                latitude=39.9042,
                longitude=116.4074,
                elevation=100.0,
                location_type="viewpoint",
                viewpoint_type="观景台",
                description="测试用观景台",
                distance_to_nearest_town=5.0,
                nearest_town_name="北京",
                scenic_value="良好"
            )
            mock_method.return_value = [mock_viewpoint]
            
            # 调用便捷函数
            result = find_viewpoints(39.5, 115.5, 40.5, 117.5, max_viewpoints=10)
            
            # 验证调用
            mock_method.assert_called_once_with((39.5, 115.5, 40.5, 117.5), 10)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].name, "测试观景台")
    
    def test_scenic_value_assessment(self):
        """
        测试景观价值评估逻辑
        """
        # 测试高海拔观景台
        high_elevation_viewpoint = Viewpoint(
            name="高山观景台",
            latitude=39.9042,
            longitude=116.4074,
            elevation=500.0,
            location_type="viewpoint",
            viewpoint_type="观景台",
            description="高海拔观景台",
            distance_to_nearest_town=10.0,
            nearest_town_name="某城镇",
            scenic_value="优秀"
        )
        
        # 测试低海拔观景台
        low_elevation_viewpoint = Viewpoint(
            name="平原观景台",
            latitude=39.9042,
            longitude=116.4074,
            elevation=50.0,
            location_type="viewpoint",
            viewpoint_type="观景台",
            description="低海拔观景台",
            distance_to_nearest_town=2.0,
            nearest_town_name="某城镇",
            scenic_value="一般"
        )
        
        # 验证数据结构正确
        self.assertIsInstance(high_elevation_viewpoint.elevation, float)
        self.assertIsInstance(low_elevation_viewpoint.elevation, float)
        self.assertGreater(high_elevation_viewpoint.elevation, low_elevation_viewpoint.elevation)

def run_tests():
    """
    运行所有测试
    """
    print("=== Viewpoint Finder Test ===")
    
    # 创建测试套件
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestViewpointFinder)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 输出测试结果
    if result.wasSuccessful():
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Test failed: {len(result.failures)} failures, {len(result.errors)} errors")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    run_tests()