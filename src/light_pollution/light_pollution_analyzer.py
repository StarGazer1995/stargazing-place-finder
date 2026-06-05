#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Light Pollution Analyzer

Reads VIIRS DNB annual composite radiance values from a GeoTIFF file.
Returns nW/cm²/sr radiance directly — no more image-based inversion.

Data source: EOG VIIRS VNL v2.2 (https://eogdata.mines.edu/products/vnl/)
"""

import os
from typing import Optional, Tuple, Dict, Any, Union
from pathlib import Path

import numpy as np

try:
    from src.models import LightPollutionInfo
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from models import LightPollutionInfo

try:
    import rasterio
except ImportError:
    rasterio = None  # type: ignore


# ---------------------------------------------------------------------------
# Radiance conversion utilities
# ---------------------------------------------------------------------------

def radiance_to_bortle(radiance: float) -> int:
    """Convert VIIRS DNB radiance (nW/cm²/sr) to Bortle class (1-9).

    Thresholds derived from peer-reviewed literature correlating VIIRS DNB
    radiance with Sky Quality Meter (SQM) measurements.
    """
    if radiance <= 0.0:
        return 1   # Excellent dark sky
    if radiance <= 0.5:
        return 2   # Typical dark sky
    if radiance <= 1.5:
        return 3   # Rural sky
    if radiance <= 4.0:
        return 4   # Rural/suburban transition
    if radiance <= 10.0:
        return 5   # Suburban sky
    if radiance <= 25.0:
        return 6   # Bright suburban
    if radiance <= 60.0:
        return 7   # Suburban/urban transition
    if radiance <= 150.0:
        return 8   # City sky
    return 9       # Inner city sky


def radiance_to_brightness(radiance: float) -> int:
    """Map radiance (nW/cm²/sr) to a 0-255 brightness value for backward compatibility."""
    if radiance <= 0:
        return 0
    b = int(255.0 * (1.0 - 1.0 / (1.0 + radiance * 0.1)))
    return min(255, b)


def radiance_to_pollution_level(radiance: float) -> str:
    """Get a human-readable pollution level string from radiance."""
    bortle = radiance_to_bortle(radiance)
    descriptions = {
        1: "极低污染 (Class 1 - 优秀观星条件)",
        2: "低度污染 (Class 2 - 良好观星条件)",
        3: "轻度污染 (Class 3 - 一般观星条件)",
        4: "中度污染 (Class 4 - 较差观星条件)",
        5: "重度污染 (Class 5 - 差观星条件)",
        6: "严重污染 (Class 6 - 很差观星条件)",
        7: "严重污染 (Class 7 - 极差观星条件)",
        8: "极端污染 (Class 8 - 不适合观星)",
        9: "极端污染 (Class 9 - 完全不适合观星)",
    }
    return descriptions.get(bortle, "未知污染等级")


def radiance_to_false_color(radiance: float) -> Tuple[int, int, int]:
    """Map radiance to a false-color RGB for visualization.

    Dark (low radiance) → blue-black
    Medium → green-yellow
    High (urban) → red-white
    """
    if radiance <= 0:
        return (10, 10, 40)
    import math as _m
    v = _m.log10(max(radiance, 0.01) + 1) / _m.log10(1001)
    v = min(1.0, v)
    if v < 0.33:
        t = v / 0.33
        r, g, b = int(10 + 50 * t), int(30 + 150 * t), int(80 + 80 * (1 - t))
    elif v < 0.66:
        t = (v - 0.33) / 0.33
        r, g, b = int(60 + 150 * t), int(180 - 100 * t), int(80 - 60 * t)
    else:
        t = (v - 0.66) / 0.34
        r, g, b = int(210 + 45 * t), int(80 + 120 * t), int(20 + 20 * t)
    return (min(255, r), min(255, g), min(255, b))


class LightPollutionAnalyzer:
    """Light Pollution Analyzer

    Reads VIIRS DNB radiance values from a GeoTIFF file. This is the
    sole backend — old KML + image-tile support has been removed.

    Usage:
        analyzer = LightPollutionAnalyzer(geotiff_path="viirs_china_2025.tif")
        info = analyzer.get_light_pollution_color(39.9, 116.4)
    """

    def __init__(
        self,
        geotiff_path: Optional[Union[str, Path]] = None,
    ):
        """Initialize the analyzer.

        Args:
            geotiff_path: Path to VIIRS GeoTIFF file.
                If None, you must call init() later with a valid path.

        Raises:
            ImportError: When rasterio is not installed.
            FileNotFoundError: When the GeoTIFF file does not exist.
        """
        if rasterio is None:
            raise ImportError(
                "rasterio is required. Install with: uv add rasterio"
            )

        if geotiff_path is None:
            self._geotiff_path = None
            self._src = None
            return

        geotiff_path = str(geotiff_path)
        if not os.path.exists(geotiff_path):
            raise FileNotFoundError(f"GeoTIFF file not found: {geotiff_path}")

        self._geotiff_path = geotiff_path
        self._src = rasterio.open(geotiff_path)
        print(f"Light pollution analyzer initialized")
        print(f"  Data: {geotiff_path}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_radiance(self, latitude: float, longitude: float) -> Optional[float]:
        """Get VIIRS DNB radiance (nW/cm²/sr) at the given coordinates.

        Args:
            latitude: Latitude
            longitude: Longitude

        Returns:
            Radiance value or None if outside coverage.
        """
        if self._src is None:
            return None
        try:
            row, col = self._src.index(longitude, latitude)
            if not (0 <= row < self._src.height and 0 <= col < self._src.width):
                return None
            val = float(self._src.read(1, window=((row, row + 1), (col, col + 1)))[0, 0])
            return val
        except Exception:
            return None

    def get_light_pollution_color(self, latitude: float, longitude: float) -> Optional[LightPollutionInfo]:
        """Get light pollution information at the given coordinates.

        Args:
            latitude: Latitude
            longitude: Longitude

        Returns:
            LightPollutionInfo with fields: radiance, rgb, hex, brightness,
            pollution_level, bortle, overlay_name, coordinates.
            None if outside data coverage.

        Raises:
            ValueError: When coordinates are invalid.
        """
        if not (-90 <= latitude <= 90):
            raise ValueError(f"Latitude must be between -90 and 90, got {latitude}")
        if not (-180 <= longitude <= 180):
            raise ValueError(f"Longitude must be between -180 and 180, got {longitude}")

        if self._src is None:
            return None

        try:
            row, col = self._src.index(longitude, latitude)
            if not (0 <= row < self._src.height and 0 <= col < self._src.width):
                return None

            radiance = float(self._src.read(1, window=((row, row + 1), (col, col + 1)))[0, 0])
            brightness = radiance_to_brightness(radiance)
            bortle = radiance_to_bortle(radiance)
            r, g, b = radiance_to_false_color(radiance)

            return LightPollutionInfo(
                radiance=radiance,
                rgb=(r, g, b),
                hex=f"#{r:02x}{g:02x}{b:02x}",
                brightness=brightness,
                bortle=bortle,
                pollution_level=radiance_to_pollution_level(radiance),
                overlay_name='VIIRS-DNB-2025',
                latitude=latitude, longitude=longitude,
            )
        except Exception:
            return None

    def batch_analyze_coordinates(self, coordinates_list: list) -> list:
        """Batch-analyse multiple coordinates (optimised: grouped by row).

        Args:
            coordinates_list: List of (latitude, longitude) tuples.

        Returns:
            List of result dicts with keys: index, coordinates, pollution_info, success.
        """
        if self._src is None:
            return [
                {'index': i, 'coordinates': c, 'pollution_info': None, 'success': False,
                 'error': 'GeoTIFF not initialised'}
                for i, c in enumerate(coordinates_list)
            ]

        # Group by raster row for efficient reads
        row_groups: Dict[int, list] = {}
        for i, (lat, lon) in enumerate(coordinates_list):
            try:
                row, col = self._src.index(lon, lat)
                if 0 <= row < self._src.height and 0 <= col < self._src.width:
                    row_groups.setdefault(row, []).append((i, col, lat, lon))
            except Exception:
                pass

        results = [None] * len(coordinates_list)

        for row, items in row_groups.items():
            row_data = self._src.read(1, window=((row, row + 1), (0, self._src.width)))
            for idx, col, lat, lon in items:
                radiance = float(row_data[0, col])
                bortle = radiance_to_bortle(radiance)
                r, g, b = radiance_to_false_color(radiance)
                results[idx] = {
                    'index': idx,
                    'coordinates': (lat, lon),
                    'pollution_info': LightPollutionInfo(
                        radiance=radiance,
                        rgb=(r, g, b),
                        hex=f"#{r:02x}{g:02x}{b:02x}",
                        brightness=radiance_to_brightness(radiance),
                        pollution_level=radiance_to_pollution_level(radiance),
                        bortle=bortle,
                        overlay_name='VIIRS-DNB-2025',
                        latitude=lat, longitude=lon,
                    ),
                    'success': True,
                }

        # Fill missing entries
        for i, r in enumerate(results):
            if r is None:
                results[i] = {
                    'index': i,
                    'coordinates': coordinates_list[i],
                    'pollution_info': None,
                    'success': False,
                    'error': 'Outside data coverage',
                }
        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Return metadata about the loaded GeoTIFF."""
        if self._src is None:
            return {'backend': 'geotiff', 'error': 'not initialised'}
        return {
            'backend': 'geotiff',
            'data_path': self._geotiff_path,
            'width': self._src.width,
            'height': self._src.height,
            'crs': str(self._src.crs),
            'bounds': {
                'north': self._src.bounds.top,
                'south': self._src.bounds.bottom,
                'east': self._src.bounds.right,
                'west': self._src.bounds.left,
            },
            'count': self._src.count,
            'dtype': self._src.dtypes[0],
        }

    def close(self) -> None:
        """Close the underlying GeoTIFF file handle."""
        if self._src is not None:
            self._src.close()
            self._src = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()