#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试更新后的analyze_area函数

验证analyze_area函数在Git更新后的功能，包括:
1. 支持多种地点类型（山峰、天文台、观景台）
2. 新的统一Location数据结构
3. 更新的评分算法
4. 参数变更（max_peaks -> max_locations）

作者: StarGazing Place Finder
日期: 2024
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# 添加 src 目录到Python路径，加载顶层包
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../src'))

from stargazing_analyzer.stargazing_location_analyzer import StargazingLocationAnalyzer, StargazingLocation

class TestUpdatedAnalyzeArea(unittest.TestCase):
    """
    测试更新后的analyze_area函数
    """
    
    def setUp(self):
        """设置测试环境"""
        self.analyzer = StargazingLocationAnalyzer()
        self.test_bbox = (39.8, 116.2, 40.0, 116.6)  # 北京周边
    
    def test_analyze_area_with_multiple_location_types(self):
        """
        测试分析多种地点类型
        """
        print("\nTest 1: Testing multiple location types")
        
        locations = self.analyzer.analyze_area(
            bbox=self.test_bbox,
            max_locations=5,
            location_types=['mountain_peak', 'observatory', 'viewpoint'],
            include_light_pollution=False,
            include_road_connectivity=False  # 跳过道路连通性检查以加快测试
        )
        
        # 验证返回结果
        self.assertIsInstance(locations, list)
        self.assertLessEqual(len(locations), 5)
        
        # 验证每个地点都是StargazingLocation对象
        for location in locations:
            self.assertIsInstance(location, StargazingLocation)
            self.assertIn(location.location_type, ['mountain_peak', 'observatory', 'viewpoint'])
            self.assertIsNotNone(location.name)
            self.assertIsNotNone(location.latitude)
            self.assertIsNotNone(location.longitude)
            self.assertIsNotNone(location.stargazing_score)
        
        print(f"✓ Found {len(locations)} locations")
        for loc in locations:
            print(f"  - {loc.name} ({loc.location_type}): {loc.stargazing_score} points")
    
    def test_analyze_area_mountain_peaks_only(self):
        """
        测试只分析山峰
        """
        print("\nTest 2: Testing mountain peaks only")
        
        locations = self.analyzer.analyze_area(
            bbox=self.test_bbox,
            max_locations=3,
            location_types=['mountain_peak'],
            include_light_pollution=False,
            include_road_connectivity=False
        )
        
        # 验证所有地点都是山峰
        for location in locations:
            self.assertEqual(location.location_type, 'mountain_peak')
            self.assertTrue(location.is_mountain_peak())
            self.assertFalse(location.is_observatory())
            self.assertFalse(location.is_viewpoint())
        
        print(f"✓ Found {len(locations)} mountain peaks")
        for loc in locations:
            print(f"  - {loc.name}: Elevation {loc.elevation}m, Score {loc.stargazing_score} points")
    
    def test_analyze_area_observatories_only(self):
        """
        测试只分析天文台
        """
        print("\nTest 3: Testing observatories only")
        
        locations = self.analyzer.analyze_area(
            bbox=self.test_bbox,
            max_locations=3,
            location_types=['observatory'],
            include_light_pollution=False,
            include_road_connectivity=False
        )
        
        # 验证所有地点都是天文台
        for location in locations:
            self.assertEqual(location.location_type, 'observatory')
            self.assertFalse(location.is_mountain_peak())
            self.assertTrue(location.is_observatory())
            self.assertFalse(location.is_viewpoint())
        
        print(f"✓ Found {len(locations)} observatories")
        for loc in locations:
            print(f"  - {loc.name}: Elevation {loc.elevation}m, Score {loc.stargazing_score} points")
    
    def test_analyze_area_viewpoints_only(self):
        """
        测试只分析观景台
        """
        print("\nTest 4: Testing viewpoints only")
        
        locations = self.analyzer.analyze_area(
            bbox=self.test_bbox,
            max_locations=3,
            location_types=['viewpoint'],
            include_light_pollution=False,
            include_road_connectivity=False
        )
        
        # 验证所有地点都是观景台
        for location in locations:
            self.assertEqual(location.location_type, 'viewpoint')
            self.assertFalse(location.is_mountain_peak())
            self.assertFalse(location.is_observatory())
            self.assertTrue(location.is_viewpoint())
        
        print(f"✓ Found {len(locations)} viewpoints")
        for loc in locations:
            print(f"  - {loc.name}: Elevation {loc.elevation}m, Score {loc.stargazing_score} points")
    
    def test_stargazing_location_dataclass(self):
        """
        测试StargazingLocation数据类的新功能
        """
        print("\nTest 5: StargazingLocation dataclass functionality")
        
        # 创建不同类型的测试地点
        mountain_peak = StargazingLocation(
            name="测试山峰",
            latitude=40.0,
            longitude=116.0,
            elevation=1000,
            location_type="mountain_peak",
            distance_to_nearest_town=25.0,
            nearest_town_name="测试城镇",
            prominence=500,
            height_difference=300,
            stargazing_score=75.0,
            recommendation_level="推荐"
        )
        
        observatory = StargazingLocation(
            name="测试天文台",
            latitude=40.0,
            longitude=116.0,
            elevation=500,
            location_type="observatory",
            distance_to_nearest_town=15.0,
            nearest_town_name="测试城镇",
            stargazing_score=80.0,
            recommendation_level="强烈推荐"
        )
        
        viewpoint = StargazingLocation(
            name="测试观景台",
            latitude=40.0,
            longitude=116.0,
            elevation=300,
            location_type="viewpoint",
            distance_to_nearest_town=10.0,
            nearest_town_name="测试城镇",
            height_difference=200,
            stargazing_score=65.0,
            recommendation_level="可考虑"
        )
        
        # 测试类型检查方法
        self.assertTrue(mountain_peak.is_mountain_peak())
        self.assertFalse(mountain_peak.is_observatory())
        self.assertFalse(mountain_peak.is_viewpoint())
        
        self.assertFalse(observatory.is_mountain_peak())
        self.assertTrue(observatory.is_observatory())
        self.assertFalse(observatory.is_viewpoint())
        
        self.assertFalse(viewpoint.is_mountain_peak())
        self.assertFalse(viewpoint.is_observatory())
        self.assertTrue(viewpoint.is_viewpoint())
        
        print("✓ StargazingLocation type checking methods work properly")
        print(f"  - Mountain peak: {mountain_peak.name} (prominence: {mountain_peak.prominence}m)")
        print(f"  - Observatory: {observatory.name} (Score: {observatory.stargazing_score} points)")
        print(f"  - Viewpoint: {viewpoint.name} (Height difference: {viewpoint.height_difference}m)")
    
    def test_scoring_algorithm_for_different_types(self):
        """
        测试不同类型地点的评分算法
        """
        print("\nTest 6: Scoring algorithm for different location types")
        
        # 获取一些实际地点进行评分测试
        locations = self.analyzer.analyze_area(
            bbox=self.test_bbox,
            max_locations=6,
            location_types=['mountain_peak', 'observatory', 'viewpoint'],
            include_light_pollution=False,
            include_road_connectivity=False
        )
        
        # 按类型分组
        by_type = {'mountain_peak': [], 'observatory': [], 'viewpoint': []}
        for loc in locations:
            by_type[loc.location_type].append(loc)
        
        # 验证评分逻辑
        for location_type, locs in by_type.items():
            if locs:
                print(f"\n  {location_type} type location scores:")
                for loc in locs:
                    print(f"    - {loc.name}: {loc.stargazing_score} points")
                    
                    # 验证评分在合理范围内
                    self.assertGreaterEqual(loc.stargazing_score, 0)
                    self.assertLessEqual(loc.stargazing_score, 100)
        
        print("\n✓ Scoring algorithm works properly")

def run_tests():
    """
    运行所有测试
    """
    print("=" * 60)
    print("Testing updated analyze_area function")
    print("=" * 60)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUpdatedAnalyzeArea)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出总结
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ All tests passed! analyze_area function update successful")
    else:
        print("❌ Some tests failed, further investigation needed")
        for failure in result.failures:
            print(f"Failed: {failure[0]}")
            print(f"Reason: {failure[1]}")
        for error in result.errors:
            print(f"Error: {error[0]}")
            print(f"Reason: {error[1]}")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()