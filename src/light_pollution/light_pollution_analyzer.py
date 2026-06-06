#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Light Pollution Analyzer

Reads VIIRS DNB annual composite radiance values from a GeoTIFF file.
Returns nW/cm²/sr radiance directly — no more image-based inversion.

Data source: EOG VIIRS VNL v2.2 (https://eogdata.mines.edu/products/vnl/)
"""

import math
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

try:
    from scipy.ndimage import gaussian_filter
except ImportError:
    gaussian_filter = None  # type: ignore

# GeoTIFF resolution in km/pixel (approximately)
_GEOTIFF_RES_DEG = 0.0041666667
_KM_PER_DEG = 111.0
_GEOTIFF_RES_KM = _GEOTIFF_RES_DEG * _KM_PER_DEG  # ~0.463 km/px


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
        skyglow_sigma_km: float = 15.0,
        skyglow_weight: float = 0.4,
    ):
        """Initialize the analyzer.

        Args:
            geotiff_path: Path to VIIRS GeoTIFF file.
                If None, you must call init() later with a valid path.
            skyglow_sigma_km: Gaussian sigma (km) for skyglow diffusion.
                0 disables skyglow correction.
            skyglow_weight: How much of the skyglow to add back (0-1).

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
            self._skyglow_grid = None
            self._skyglow_transform = None
            return

        geotiff_path = str(geotiff_path)
        if not os.path.exists(geotiff_path):
            raise FileNotFoundError(f"GeoTIFF file not found: {geotiff_path}")

        self._geotiff_path = geotiff_path
        self._src = rasterio.open(geotiff_path)
        self._skyglow_sigma_km = skyglow_sigma_km
        self._skyglow_weight = skyglow_weight
        self._skyglow_grid = None
        self._skyglow_transform = None
        self._skyglow_ds = 1

        print(f"Light pollution analyzer initialized")
        print(f"  Data: {geotiff_path}")
        print(f"  Skyglow model: sigma={skyglow_sigma_km}km, weight={skyglow_weight}")
        if skyglow_sigma_km > 0:
            self._compute_skyglow()

    # ------------------------------------------------------------------
    # Skyglow diffusion model
    # ------------------------------------------------------------------

    def _compute_skyglow(self) -> None:
        """Compute a downsampled skyglow raster by Gaussian-blurring the VIIRS data.

        VIIRS vcm data has background (ZTH) subtraction, which removes diffuse
        skyglow from the signal. This method creates a smooth skyglow estimate
        by blurring the light emission data at a coarse resolution — simulating
        how city light scatters through the atmosphere.

        The result is stored as a low-resolution grid (~7.4 km/px) to save memory.
        """
        if self._src is None or gaussian_filter is None:
            return

        full = self._src.read(1)

        # Downsample factor (16x → ~7.4 km/px at equator)
        ds = 16
        h, w = full.shape
        dh, dw = h // ds, w // ds
        trimmed = full[:dh * ds, :dw * ds]

        # Block average — mean of each ds × ds block
        downsampled = trimmed.reshape(dh, ds, dw, ds).mean(axis=(1, 3))

        # Convert sigma from km to pixels in downsampled grid
        sigma_px = self._skyglow_sigma_km / (_GEOTIFF_RES_KM * ds)

        # Apply Gaussian blur — this is the skyglow model
        self._skyglow_grid = gaussian_filter(
            downsampled.astype(np.float64), sigma=max(sigma_px, 0.5)
        ).astype(np.float32)

        # Geo-transform for the downsampled grid
        self._skyglow_transform = (
            float(self._src.bounds.left),        # west (x origin)
            float(self._src.res[0] * ds),        # pixel width (degrees)
            0.0,                                  # x rotation
            float(self._src.bounds.top),          # north (y origin)
            0.0,                                  # y rotation
            -float(self._src.res[1] * ds),        # pixel height (degrees, negative)
        )
        self._skyglow_ds = ds
        self._skyglow_shape = self._skyglow_grid.shape

        print(f"  Skyglow grid: {self._skyglow_shape[1]}×{self._skyglow_shape[0]} "
              f"at ~{_GEOTIFF_RES_KM * ds:.1f} km/px")

    def _get_skyglow(self, latitude: float, longitude: float) -> float:
        """Get the skyglow contribution (nW/cm²/sr) at a point via interpolation.

        Args:
            latitude: Latitude in degrees.
            longitude: Longitude in degrees.

        Returns:
            Skyglow radiance value, or 0.0 if no skyglow model is loaded.
        """
        if self._skyglow_grid is None:
            return 0.0

        try:
            west, res_x, _, north, _, res_y = self._skyglow_transform
            col = (longitude - west) / res_x
            row = (latitude - north) / res_y  # negative since res_y < 0

            # Clamp to grid bounds
            row = max(0, min(self._skyglow_shape[0] - 1, row))
            col = max(0, min(self._skyglow_shape[1] - 1, col))

            # Bilinear interpolation
            r0, c0 = int(math.floor(row)), int(math.floor(col))
            r1, c1 = min(r0 + 1, self._skyglow_shape[0] - 1), min(c0 + 1, self._skyglow_shape[1] - 1)
            dr, dc = row - r0, col - c0

            v00 = self._skyglow_grid[r0, c0]
            v10 = self._skyglow_grid[r1, c0]
            v01 = self._skyglow_grid[r0, c1]
            v11 = self._skyglow_grid[r1, c1]

            v0 = v00 * (1 - dr) + v10 * dr
            v1 = v01 * (1 - dr) + v11 * dr
            return float(v0 * (1 - dc) + v1 * dc)
        except Exception:
            return 0.0

    def get_skyglow_for_window(
        self,
        west: float, east: float,
        south: float, north: float,
        out_shape: Tuple[int, int],
    ) -> np.ndarray:
        """Sample the skyglow grid over a geographic window, returned at out_shape.

        Args:
            west, east, south, north: Geographic bounds in degrees.
            out_shape: (height, width) of the output array.

        Returns:
            2D numpy array of skyglow radiance values (float32),
            or zeros if no skyglow model.
        """
        if self._skyglow_grid is None:
            return np.zeros(out_shape, dtype=np.float32)

        gw, gx, _, gn, _, gy = self._skyglow_transform
        gx, gy = float(gx), float(gy)

        # Pixel coordinates of the window corners in the skyglow grid
        c0 = max(0.0, (west - gw) / gx)
        c1 = min(self._skyglow_shape[1] - 1, (east - gw) / gx)
        r0 = max(0.0, (north - gn) / gy)  # negative gy
        r1 = min(self._skyglow_shape[0] - 1, (south - gn) / gy)

        h_out, w_out = out_shape
        if h_out <= 1 or w_out <= 1:
            return np.zeros(out_shape, dtype=np.float32)

        # Build sampling coordinates
        rows = np.linspace(r0, r1, h_out)
        cols = np.linspace(c0, c1, w_out)
        rr, cc = np.meshgrid(rows, cols, indexing='ij')

        # Bilinear interpolation on the grid
        r0_i = np.floor(rr).astype(np.int32)
        c0_i = np.floor(cc).astype(np.int32)
        r1_i = np.minimum(r0_i + 1, self._skyglow_shape[0] - 1)
        c1_i = np.minimum(c0_i + 1, self._skyglow_shape[1] - 1)
        dr = rr - r0_i
        dc = cc - c0_i

        v00 = self._skyglow_grid[r0_i, c0_i]
        v10 = self._skyglow_grid[r1_i, c0_i]
        v01 = self._skyglow_grid[r0_i, c1_i]
        v11 = self._skyglow_grid[r1_i, c1_i]

        v0 = v00 * (1 - dr) + v10 * dr
        v1 = v01 * (1 - dr) + v11 * dr
        return (v0 * (1 - dc) + v1 * dc).astype(np.float32)

    # ------------------------------------------------------------------
    # Radiance accessors
    # ------------------------------------------------------------------

    def get_raw_radiance(self, latitude: float, longitude: float) -> Optional[float]:
        """Get raw VIIRS DNB radiance (nW/cm²/sr) WITHOUT skyglow correction.

        Args:
            latitude: Latitude
            longitude: Longitude

        Returns:
            Raw radiance value or None if outside coverage.
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

    def get_radiance(self, latitude: float, longitude: float) -> Optional[float]:
        """Get total radiance (nW/cm²/sr) INCLUDING skyglow correction.

        The skyglow correction adds back diffuse atmospheric scattering from
        nearby cities, which is subtracted out in the VIIRS vcm product.

        Args:
            latitude: Latitude
            longitude: Longitude

        Returns:
            Total radiance value (raw + skyglow), or None if outside coverage.
        """
        raw = self.get_raw_radiance(latitude, longitude)
        if raw is None:
            return None
        skyglow = self._get_skyglow(latitude, longitude)
        return raw + self._skyglow_weight * skyglow

    def get_light_pollution_color(self, latitude: float, longitude: float) -> Optional[LightPollutionInfo]:
        """Get light pollution information at the given coordinates.

        Uses the skyglow-corrected radiance.

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
            radiance = self.get_radiance(latitude, longitude)
            if radiance is None:
                return None

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
                # Add skyglow correction
                raw = float(row_data[0, col])
                skyglow = self._get_skyglow(lat, lon)
                radiance = raw + self._skyglow_weight * skyglow
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