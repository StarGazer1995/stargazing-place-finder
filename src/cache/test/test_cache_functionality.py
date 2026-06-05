#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
山峰查找器缓存功能测试脚本
测试缓存的各种功能和边界情况
"""

import sys
import os
import unittest
import tempfile
import shutil
import time
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from src.stargazing_analyzer.stargazing_place_finder import StarGazingPlaceFinder, OverpassCache

class TestOverpassCache(unittest.TestCase):
    """
    测试OverpassCache类的功能
    """
    
    def setUp(self):
        """
        测试前的设置
        """
        # 创建临时目录用于测试
        self.temp_dir = tempfile.mkdtemp()
        self.cache = OverpassCache(cache_dir=self.temp_dir, expiry_hours=1)
        
    def tearDown(self):
        """
        测试后的清理
        """
        # 删除临时目录
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_cache_key_generation(self):
        """
        测试缓存键生成
        """
        query = "test query"
        data_type = "test_type"
        bbox = (1.0, 2.0, 3.0, 4.0)
        
        key1 = self.cache._generate_cache_key(query, data_type, bbox)
        key2 = self.cache._generate_cache_key(query, data_type, bbox)
        
        # 相同输入应该生成相同的键
        self.assertEqual(key1, key2)
        
        # 不同输入应该生成不同的键
        key3 = self.cache._generate_cache_key("different query", data_type, bbox)
        self.assertNotEqual(key1, key3)
    
    def test_cache_save_and_get(self):
        """
        测试缓存保存和获取
        """
        query = "test query"
        data_type = "test_type"
        bbox = (1.0, 2.0, 3.0, 4.0)
        test_data = [{"id": 1, "name": "test"}]
        
        # 保存到缓存
        self.cache.save_to_cache(query, data_type, bbox, test_data)
        
        # 从缓存获取
        cached_data = self.cache.get_from_cache(query, data_type, bbox)
        
        self.assertIsNotNone(cached_data)
        self.assertEqual(cached_data, test_data)
    
    def test_cache_expiry(self):
        """
        测试缓存过期功能
        """
        # 创建一个过期时间很短的缓存
        short_cache = OverpassCache(cache_dir=self.temp_dir, expiry_hours=0.001)  # 约3.6秒
        
        query = "test query"
        data_type = "test_type"
        bbox = (1.0, 2.0, 3.0, 4.0)
        test_data = [{"id": 1, "name": "test"}]
        
        # 保存到缓存
        short_cache.save_to_cache(query, data_type, bbox, test_data)
        
        # 立即获取应该成功
        cached_data = short_cache.get_from_cache(query, data_type, bbox)
        self.assertIsNotNone(cached_data)
        
        # 等待过期
        time.sleep(4)
        
        # 过期后获取应该返回None
        expired_data = short_cache.get_from_cache(query, data_type, bbox)
        self.assertIsNone(expired_data)
    
    def test_cache_clear(self):
        """
        测试缓存清除功能
        """
        query = "test query"
        data_type = "test_type"
        bbox = (1.0, 2.0, 3.0, 4.0)
        test_data = [{"id": 1, "name": "test"}]
        
        # 保存到缓存
        self.cache.save_to_cache(query, data_type, bbox, test_data)
        
        # 确认缓存存在
        cached_data = self.cache.get_from_cache(query, data_type, bbox)
        self.assertIsNotNone(cached_data)
        
        # 清除缓存
        self.cache.clear_cache()
        
        # 确认缓存已清除
        cleared_data = self.cache.get_from_cache(query, data_type, bbox)
        self.assertIsNone(cleared_data)
    
    def test_cache_info(self):
        """
        测试缓存信息获取
        """
        # 初始状态
        info = self.cache.get_cache_info()
        self.assertEqual(info['file_count'], 0)
        self.assertEqual(info['total_size'], '0.0 B')
        
        # 添加一些缓存数据
        query = "test query"
        data_type = "test_type"
        bbox = (1.0, 2.0, 3.0, 4.0)
        test_data = [{"id": 1, "name": "test"}]
        
        self.cache.save_to_cache(query, data_type, bbox, test_data)
        
        # 检查更新后的信息
        info_after = self.cache.get_cache_info()
        self.assertEqual(info_after['file_count'], 1)
        self.assertNotEqual(info_after['total_size'], '0.0 B')

class TestStarGazingPlaceFinderCache(unittest.TestCase):
    """
    测试StarGazingPlaceFinder的缓存集成功能
    """
    
    def setUp(self):
        """
        测试前的设置
        """
        # 创建临时目录用于测试
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """
        测试后的清理
        """
        # 删除临时目录
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @patch('src.stargazing_analyzer.stargazing_place_finder.get_cache_dir')
    def test_cache_enabled_initialization(self, mock_get_cache_dir):
        """
        测试启用缓存的初始化
        """
        mock_get_cache_dir.return_value = self.temp_dir
        
        finder = StarGazingPlaceFinder(enable_cache=True, cache_expiry_hours=2)
        
        self.assertIsNotNone(finder.cache)
        self.assertEqual(finder.cache.expiry_hours, 2 * 3600)  # 2 hours converted to seconds
    
    def test_cache_disabled_initialization(self):
        """
        测试禁用缓存的初始化
        """
        finder = StarGazingPlaceFinder(enable_cache=False)
        
        self.assertIsNone(finder.cache)
    
    @patch('src.stargazing_analyzer.stargazing_place_finder.get_cache_dir')
    def test_cache_management_methods(self, mock_get_cache_dir):
        """
        测试缓存管理方法
        """
        mock_get_cache_dir.return_value = self.temp_dir
        
        # 启用缓存的查找器
        finder_with_cache = StarGazingPlaceFinder(enable_cache=True)
        
        # 测试获取缓存信息
        cache_info = finder_with_cache.get_cache_info()
        self.assertIsNotNone(cache_info)
        self.assertIn('file_count', cache_info)
        self.assertIn('total_size', cache_info)
        
        # 测试清除缓存（不应该抛出异常）
        finder_with_cache.clear_cache()
        
        # 禁用缓存的查找器
        finder_no_cache = StarGazingPlaceFinder(enable_cache=False)
        
        # 测试获取缓存信息（应该返回None）
        cache_info_none = finder_no_cache.get_cache_info()
        self.assertIsNone(cache_info_none)
    
    @patch('src.stargazing_analyzer.stargazing_place_finder.get_cache_dir')
    @patch('src.stargazing_analyzer.stargazing_place_finder.StarGazingPlaceFinder._make_overpass_request')
    def test_cache_integration_in_queries(self, mock_request, mock_get_cache_dir):
        """
        测试查询方法中的缓存集成
        """
        mock_get_cache_dir.return_value = self.temp_dir
        mock_request.return_value = [{"id": 1, "name": "test"}]
        
        finder = StarGazingPlaceFinder(enable_cache=True)
        bbox = (39.8, 116.2, 40.0, 116.5)
        
        # 第一次调用应该触发网络请求
        result1 = finder.get_peaks_from_overpass(bbox)
        self.assertEqual(len(mock_request.call_args_list), 1)
        
        # 第二次调用应该使用缓存（如果缓存正常工作）
        result2 = finder.get_peaks_from_overpass(bbox)
        
        # 验证结果一致
        self.assertEqual(result1, result2)

def run_tests():
    """
    运行所有测试
    """
    print("🧪 Starting cache functionality tests...")
    print("=" * 50)
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加OverpassCache测试
    test_suite.addTest(unittest.makeSuite(TestOverpassCache))
    
    # 添加StarGazingPlaceFinder缓存集成测试
    test_suite.addTest(unittest.makeSuite(TestStarGazingPlaceFinderCache))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 输出测试结果摘要
    print("\n" + "=" * 50)
    print(f"🧪 Tests completed!")
    print(f"✅ Success: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Failed: {len(result.failures)}")
    print(f"💥 Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ Failed tests:")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback.split('\n')[-2]}")
    
    if result.errors:
        print("\n💥 Error tests:")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback.split('\n')[-2]}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)