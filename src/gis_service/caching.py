# -*- coding: utf-8 -*-
"""
GIS 查询缓存模块。

迁移自 stargazing_place_finder.py 中的 LocationCache。
支持内存 + 磁盘两级缓存。
"""

import hashlib
import logging
import os
import pickle
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from cache.cache_config import get_cache_dir
from config import StargazingConfig
from models import DataError

logger = logging.getLogger(__name__)


class GisQueryCache:
    """
    通用 GIS 查询结果缓存。

    支持内存缓存 + 磁盘 pickle 缓存两级，
    自动过期清理。
    """

    def __init__(
        self,
        cache_expiry_hours: int = 24,
        cache_type: str = "location_results",
        config: Optional[StargazingConfig] = None,
    ):
        if config is not None:
            cache_expiry_hours = config.cache_expiry_hours
        self.cache_expiry_seconds = cache_expiry_hours * 3600
        self.cache_dir = get_cache_dir(cache_type)

        # 内存缓存: {cache_key: (timestamp, data)}
        self._memory: Dict[str, tuple] = {}
        self._lock = threading.Lock()

    def _make_key(self, *args, **kwargs) -> str:
        """从参数生成唯一缓存键。"""
        raw = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存（线程安全）。检查内存和磁盘，过期自动丢弃。"""
        now = time.time()

        with self._lock:
            # 内存缓存
            if key in self._memory:
                ts, data = self._memory[key]
                if now - ts < self.cache_expiry_seconds:
                    return data
                del self._memory[key]

        # 磁盘缓存（锁外读取 I/O，避免阻塞其他线程）
        cache_path = self._disk_path(key)
        if cache_path.exists():
            try:
                with open(cache_path, "rb") as f:
                    ts, data = pickle.load(f)
                if now - ts < self.cache_expiry_seconds:
                    with self._lock:
                        self._memory[key] = (ts, data)
                    return data
                # 过期删除
                cache_path.unlink(missing_ok=True)
            except (DataError, pickle.PickleError) as e:
                logger.debug("Cache read failed for %s: %s", key, e)

        return None

    def set(self, key: str, data: Any):
        """写入内存 + 磁盘缓存（线程安全，原子写入）。"""
        now = time.time()
        with self._lock:
            self._memory[key] = (now, data)
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            disk_path = self._disk_path(key)
            # Atomic write: temp file + rename avoids TOCTOU corruption
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pkl", prefix=".tmp-", dir=str(self.cache_dir))
            try:
                with os.fdopen(tmp_fd, "wb") as f:
                    pickle.dump((now, data), f)
                os.replace(tmp_path, disk_path)
            except Exception:
                # Clean up temp file on failure
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except DataError as e:
            logger.debug("Cache write failed for %s: %s", key, e)

    def _disk_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.pkl"

    def clear(self):
        """清空所有缓存。"""
        self._memory.clear()
        if self.cache_dir.exists():
            import shutil

            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
