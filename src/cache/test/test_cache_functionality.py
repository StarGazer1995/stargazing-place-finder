#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GIS query cache 功能测试脚本

测试 GisQueryCache 的基本功能：读写、过期、清除、统计等。
"""

import os
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

from gis_service.caching import GisQueryCache


class TestGisQueryCache(unittest.TestCase):
    """Tests for GisQueryCache — each test gets an isolated temp directory."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        # Re-route cache to isolated temp directory so tests don't share disk state
        from pathlib import Path

        self._cache_dir_patcher = patch("gis_service.caching.get_cache_dir", return_value=Path(self.temp_dir))
        self._cache_dir_patcher.start()
        self.cache = GisQueryCache(cache_expiry_hours=1)

    def tearDown(self):
        self._cache_dir_patcher.stop()
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

    def test_memory_cache_expiry_deletes_entry(self):
        """Expired memory cache entry is deleted (line 64)."""
        key = self.cache._make_key("expired")
        # Manually insert an expired entry (old timestamp)
        self.cache._memory[key] = (0.0, "stale_data")
        result = self.cache.get(key)
        self.assertIsNone(result)
        self.assertNotIn(key, self.cache._memory)

    def test_disk_cache_promotes_to_memory(self):
        """Valid disk cache entry is loaded and promoted to memory (lines 73-74)."""
        import pickle

        key = self.cache._make_key("disk_hit")
        now = time.time()
        disk_path = self.cache._disk_path(key)
        self.cache.cache_dir.mkdir(parents=True, exist_ok=True)
        with open(disk_path, "wb") as f:
            pickle.dump((now, "disk_data"), f)

        # Should load from disk and promote to memory
        result = self.cache.get(key)
        self.assertEqual(result, "disk_data")
        self.assertIn(key, self.cache._memory)

        # Clean up
        disk_path.unlink(missing_ok=True)

    @patch("gis_service.caching.pickle.dump")
    def test_atomic_write_cleans_up_temp_file_on_failure(self, mock_dump):
        """When pickle.dump fails, temp file is cleaned up (lines 97, 99-103)."""
        mock_dump.side_effect = RuntimeError("pickle failure")
        key = self.cache._make_key("write_fail")
        # Pre-populate cache_dir so mkdir doesn't fail
        self.cache.cache_dir.mkdir(parents=True, exist_ok=True)

        with patch("gis_service.caching.os.unlink") as mock_unlink:
            with self.assertRaises(RuntimeError):
                self.cache.set(key, "will_fail")

            # Verify temp file cleanup was attempted before re-raise
            mock_unlink.assert_called()

    @patch("gis_service.caching.pickle.dump")
    @patch("gis_service.caching.os.unlink")
    def test_atomic_write_cleanup_oserror_is_silent(self, mock_unlink, mock_dump):
        """When os.unlink fails during cleanup, OSError is silently ignored (lines 101-102)."""
        mock_dump.side_effect = RuntimeError("pickle failure")
        mock_unlink.side_effect = OSError("permission denied")
        key = self.cache._make_key("write_fail_unlink")
        self.cache.cache_dir.mkdir(parents=True, exist_ok=True)

        # Should still raise the original RuntimeError, not OSError
        with self.assertRaises(RuntimeError):
            self.cache.set(key, "will_fail")
        mock_unlink.assert_called()
