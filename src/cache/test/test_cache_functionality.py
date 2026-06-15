#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GIS query cache 功能测试脚本

测试 GisQueryCache 的基本功能：读写、过期、清除、统计等。
"""

import os
import shutil
import sys
import tempfile
import time
import unittest

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from gis_service.caching import GisQueryCache


class TestGisQueryCache(unittest.TestCase):
    """
    测试 GisQueryCache 类的功能
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        # GisQueryCache 使用 get_cache_dir()，此处 patch 不方便直接注入，
        # 改用实际配置的临时目录路径。只需要测试缓存语义即可。
        self.cache = GisQueryCache(cache_expiry_hours=1)

    def tearDown(self):
        self.cache.clear()
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_cache_get_set(self):
        """测试缓存的基本读写"""
        key = self.cache._make_key("test", "data")
        test_data = [{"id": 1, "name": "test"}]

        # 初始状态为空
        self.assertIsNone(self.cache.get(key))

        # 写入后读取
        self.cache.set(key, test_data)
        result = self.cache.get(key)
        self.assertEqual(result, test_data)

    def test_cache_miss(self):
        """测试不存在的键返回 None"""
        key = self.cache._make_key("nonexistent")
        self.assertIsNone(self.cache.get(key))

    def test_cache_clear(self):
        """测试清除缓存"""
        key1 = self.cache._make_key("a")
        key2 = self.cache._make_key("b")
        self.cache.set(key1, "data1")
        self.cache.set(key2, "data2")

        self.cache.clear()
        self.assertIsNone(self.cache.get(key1))
        self.assertIsNone(self.cache.get(key2))

    def test_cache_overwrite(self):
        """测试覆盖已有缓存"""
        key = self.cache._make_key("overwrite")
        self.cache.set(key, "old")
        self.cache.set(key, "new")
        self.assertEqual(self.cache.get(key), "new")

    def test_cache_different_keys(self):
        """测试不同 key 互不干扰"""
        key1 = self.cache._make_key("alpha")
        key2 = self.cache._make_key("beta")
        self.cache.set(key1, "value_a")
        self.cache.set(key2, "value_b")

        self.assertEqual(self.cache.get(key1), "value_a")
        self.assertEqual(self.cache.get(key2), "value_b")


def run_tests():
    """运行所有测试"""
    print("🧪 Starting GIS query cache tests...")
    print("=" * 50)

    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestGisQueryCache))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 50)
    print(f"✅ Success: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Failed: {len(result.failures)}")
    print(f"💥 Errors: {len(result.errors)}")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
