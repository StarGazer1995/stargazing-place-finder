#!/usr/bin/env python3
"""
光污染排序功能测试脚本
专门测试山峰查找器中的光污染分析和排序功能
"""

import sys
import os

# 添加 src 目录到Python路径以加载顶层包
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))

from stargazing_analyzer.stargazing_place_finder import StarGazingPlaceFinder
from light_pollution.light_pollution_analyzer import LightPollutionAnalyzer
import unittest
from unittest.mock import Mock, patch

class TestLightPollutionSorting(unittest.TestCase):
    """
    光污染排序功能测试类
    
    测试山峰查找器中光污染分析和排序相关的功能，
    包括数据处理、排序逻辑和边界条件处理
    """
    
    def setUp(self):
        """
        测试前的初始化设置
        
        创建测试用的山峰查找器实例和模拟的光污染分析器
        """
        # 创建模拟的光污染分析器
        self.mock_light_analyzer = Mock(spec=LightPollutionAnalyzer)
        self.finder = StarGazingPlaceFinder(
            min_height_difference=100.0,
            light_pollution_analyzer=self.mock_light_analyzer
        )
        
        # 测试用的地点数据
        self.test_places = [
            {'type': 'node', 'lat': 40.0, 'lon': 116.0, 'tags': {'name': '地点A'}},
            {'type': 'node', 'lat': 40.1, 'lon': 116.1, 'tags': {'name': '地点B'}},
            {'type': 'node', 'lat': 40.2, 'lon': 116.2, 'tags': {'name': '地点C'}}
        ]
    
    def test_sort_places_without_light_analyzer(self):
        """
        测试没有光污染分析器时的排序行为
        
        验证当没有光污染分析器时，函数应该返回原始列表不变
        """
        finder_no_analyzer = StarGazingPlaceFinder(min_height_difference=100.0)
        result = finder_no_analyzer._sort_places_by_lightpollution(self.test_places)
        
        # 应该返回原始列表
        self.assertEqual(result, self.test_places)
        self.assertEqual(len(result), 3)
    
    def test_sort_places_with_light_analyzer(self):
        """
        测试有光污染分析器时的排序行为
        
        验证光污染分析器正确调用和数据正确排序
        """
        # 模拟光污染分析结果（按brightness从低到高）
        mock_pollution_results = [
            {'index': 0, 'pollution_info': {'brightness': 0.3}},  # 地点A - 低光污染
            {'index': 1, 'pollution_info': {'brightness': 0.8}},  # 地点B - 高光污染
            {'index': 2, 'pollution_info': {'brightness': 0.5}}   # 地点C - 中等光污染
        ]
        
        self.mock_light_analyzer.batch_analyze_coordinates.return_value = mock_pollution_results
        
        result = self.finder._sort_places_by_lightpollution(self.test_places)
        
        # 验证调用了光污染分析器
        self.mock_light_analyzer.batch_analyze_coordinates.assert_called_once()
        
        # 验证传递给分析器的坐标格式正确
        called_coords = self.mock_light_analyzer.batch_analyze_coordinates.call_args[0][0]
        expected_coords = [[40.0, 116.0], [40.1, 116.1], [40.2, 116.2]]
        self.assertEqual(called_coords, expected_coords)
        
        # 验证排序结果：应该按光污染从低到高排序
        # 期望顺序：地点A(0.3) -> 地点C(0.5) -> 地点B(0.8)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['tags']['name'], '地点A')  # 最低光污染
        self.assertEqual(result[1]['tags']['name'], '地点C')  # 中等光污染
        self.assertEqual(result[2]['tags']['name'], '地点B')  # 最高光污染
    
    def test_sort_places_empty_list(self):
        """
        测试空列表的处理
        
        验证函数能正确处理空输入列表
        """
        # 对于空列表，不应该调用光污染分析器
        result = self.finder._sort_places_by_lightpollution([])
        self.assertEqual(result, [])
        
        # 确保没有调用光污染分析器
        self.mock_light_analyzer.batch_analyze_coordinates.assert_not_called()
    
    def test_sort_places_single_item(self):
        """
        测试单个地点的处理
        
        验证函数能正确处理只有一个地点的情况
        """
        single_place = [{'type': 'node', 'lat': 40.0, 'lon': 116.0, 'tags': {'name': '单个地点'}}]
        
        mock_pollution_result = [
            {'index': 0, 'pollution_info': {'brightness': 0.5}}
        ]
        self.mock_light_analyzer.batch_analyze_coordinates.return_value = mock_pollution_result
        
        result = self.finder._sort_places_by_lightpollution(single_place)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['tags']['name'], '单个地点')
    
    def test_coordinate_extraction(self):
        """
        测试坐标提取的正确性
        
        验证从地点数据中正确提取经纬度坐标
        """
        # 包含不同坐标格式的测试数据
        test_places_varied = [
            {'type': 'node', 'lat': 39.9042, 'lon': 116.4074},  # 北京
            {'type': 'node', 'lat': 31.2304, 'lon': 121.4737},  # 上海
            {'type': 'node', 'lat': 22.3193, 'lon': 114.1694}   # 香港
        ]
        
        mock_pollution_results = [
            {'index': 0, 'pollution_info': {'brightness': 0.1}},
            {'index': 1, 'pollution_info': {'brightness': 0.2}},
            {'index': 2, 'pollution_info': {'brightness': 0.3}}
        ]
        
        self.mock_light_analyzer.batch_analyze_coordinates.return_value = mock_pollution_results
        
        self.finder._sort_places_by_lightpollution(test_places_varied)
        
        # 验证传递的坐标格式
        called_coords = self.mock_light_analyzer.batch_analyze_coordinates.call_args[0][0]
        expected_coords = [
            [39.9042, 116.4074],
            [31.2304, 121.4737],
            [22.3193, 114.1694]
        ]
        self.assertEqual(called_coords, expected_coords)

def run_light_pollution_tests():
    """
    运行光污染排序相关的所有测试
    
    执行单元测试并输出详细的测试结果报告
    """
    print("=== Light Pollution Sorting Function Test ===")
    print("Testing light pollution analysis and sorting functions in peak finder")
    print("=" * 50)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLightPollutionSorting)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 50)
    print(f"Test results: {result.testsRun - len(result.failures) - len(result.errors)}/{result.testsRun} tests passed")
    
    if result.failures:
        print(f"Failed tests: {len(result.failures)}")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print(f"Error tests: {len(result.errors)}")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Error:')[-1].strip()}")
    
    if result.wasSuccessful():
        print("🎉 All light pollution sorting tests passed!")
        return True
    else:
        print("⚠️ Some tests failed, please check code logic")
        return False

if __name__ == "__main__":
    run_light_pollution_tests()