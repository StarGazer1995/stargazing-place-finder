#!/usr/bin/env python3
"""
Stargazing Place Finder Module

Orchestrates location discovery (peaks, observatories, viewpoints) using
GisQueryService for data retrieval and gis_service.parsers for data transformation.
"""

import importlib.resources as res
import json
import logging
from typing import Dict, List, Optional

from config import StargazingConfig
from gis_service.parsers import (
    extract_coordinates,
    find_nearest_town,
    process_observatory_data,
    process_peak_data,
    process_viewpoint_data,
    sort_places_by_lightpollution,
)
from gis_service.query_service import GisQueryService
from light_pollution.light_pollution_analyzer import LightPollutionAnalyzer
from models import GeoCoordinate, LatLonBox, Location, Observatory, Peak, Viewpoint

logger = logging.getLogger(__name__)


class StarGazingPlaceFinder:
    """
    Stargazing place finder class.
    Orchestrates location discovery by delegating GIS queries to GisQueryService
    and data transformation to parsers.
    """

    def __init__(
        self,
        min_height_difference: float = 100.0,
        light_pollution_analyzer: Optional[LightPollutionAnalyzer] = None,
        gis_service: Optional[GisQueryService] = None,
        config: Optional[StargazingConfig] = None,
    ):
        """
        Initialize stargazing place finder.

        Args:
            min_height_difference: Minimum height difference from surrounding
                                   towns (meters), default 100m.
            light_pollution_analyzer: Light pollution analyzer instance.
            gis_service: GisQueryService instance for unified GIS queries.
                         If None, a default instance is created.
            config: Centralised StargazingConfig instance. When provided, its
                values override the individual keyword defaults above.
        """
        if config is not None:
            min_height_difference = config.min_height_difference
        self.min_height_difference = min_height_difference
        self.light_pollution_analyzer = light_pollution_analyzer
        self.gis_service = gis_service or GisQueryService()

    # ── Core orchestration ──────────────────────────────────────────

    def _find_locations_in_area(
        self,
        bbox: LatLonBox,
        location_type: str,
        max_locations: int,
        location_processor_func,
    ) -> List[Location]:
        """
        Generic location finding function to reduce code duplication.

        Args:
            bbox: Bounding box (LatLonBox with south/west/north/east).
            location_type: Location type ('mountain_peak', 'observatory', 'viewpoint').
            max_locations: Maximum number of locations to return.
            location_processor_func: Callable to build a Location object from raw data.

        Returns:
            List of location objects.
        """
        bbox_tuple = (bbox.south, bbox.west, bbox.north, bbox.east)
        logger.info("Searching %s area: %s", location_type, bbox_tuple)
        logger.info("Getting %s data...", location_type)

        locations_data = self.gis_service.query_locations(bbox, location_type)
        locations_data = sort_places_by_lightpollution(locations_data, self.light_pollution_analyzer)
        logger.info("Found %s %s", len(locations_data), location_type)

        if not locations_data:
            logger.info("No %s data found", location_type)
            return []

        # Get town data
        logger.info("Getting town data...")
        towns_data = self.gis_service.query_locations(bbox, "town")
        logger.info("Found %s towns", len(towns_data))

        res_list = []
        remaining = max_locations

        for i, location_data in enumerate(locations_data[:max_locations]):
            if i % 5 == 0:
                logger.info("Processing progress: %s/%s", i + 1, min(len(locations_data), max_locations))

            point = extract_coordinates(location_data)
            if point is None:
                logger.warning(
                    "%s data missing coordinate information, skipping: %s",
                    location_type,
                    location_data.get("id", "unknown"),
                )
                continue

            tags = location_data.get("tags", {})
            name = tags.get("name", f"{location_type}_{i + 1}")

            # Elevation: tags > gis_service
            elevation = None
            if "ele" in tags:
                try:
                    elevation = float(tags["ele"])
                except ValueError:
                    pass
            if elevation is None:
                elevation = self.gis_service.find_elevation(point.latitude, point.longitude)
            if elevation is None:
                elevation = 0.0

            # Nearest town
            nearest_town = "Unknown"
            distance_to_town = 0.0
            town_elevation = None
            if towns_data:
                town_info = find_nearest_town(
                    point,
                    towns_data,
                    elevation_func=self.gis_service.find_elevation
                    if hasattr(self.gis_service, "find_elevation")
                    else None,
                )
                nearest_town = town_info.name or "Unknown"
                distance_to_town = town_info.distance_km
                town_elevation = town_info.elevation_m

            # Light pollution
            light_pollution_level = None
            if "light_pollution" in location_data:
                light_pollution_level = getattr(
                    location_data["light_pollution"], "pollution_level", "Unknown pollution level"
                )

            location = location_processor_func(
                name,
                point,
                elevation,
                tags,
                nearest_town,
                distance_to_town,
                town_elevation,
                light_pollution_level,
                i,
            )
            if location:
                res_list.append(location)
                remaining -= 1

        logger.info("\nTotal found %s %s", len(res_list), location_type)
        return res_list

    # ── Public entry points ─────────────────────────────────────────

    def find_peaks_in_area(self, bbox: LatLonBox, max_locations: int = 50) -> List[Peak]:
        """Find qualified peaks in specified area."""
        return self._find_locations_in_area(
            bbox=bbox,
            location_type="peak",
            max_locations=max_locations,
            location_processor_func=lambda *a: process_peak_data(*a, min_height_difference=self.min_height_difference),
        )

    def find_observatories_in_area(self, bbox: LatLonBox, max_observatories: int = 50) -> List[Observatory]:
        """Find observatories in specified area."""
        return self._find_locations_in_area(
            bbox=bbox,
            location_type="observatory",
            max_locations=max_observatories,
            location_processor_func=process_observatory_data,
        )

    def find_viewpoints_in_area(self, bbox: LatLonBox, max_viewpoints: int = 50) -> List[Viewpoint]:
        """Find viewpoints in specified area."""
        return self._find_locations_in_area(
            bbox=bbox,
            location_type="viewpoint",
            max_locations=max_viewpoints,
            location_processor_func=process_viewpoint_data,
        )

    # ── Utilities ───────────────────────────────────────────────────

    def save_results_to_json(self, peaks: List[Peak], filename: str) -> None:
        """Save peak results to a JSON file."""
        results = {
            "search_criteria": {"min_height_difference": self.min_height_difference},
            "total_peaks_found": len(peaks),
            "peaks": [
                {
                    "name": peak.name,
                    "latitude": peak.latitude,
                    "longitude": peak.longitude,
                    "elevation": peak.elevation,
                    "height_difference": peak.height_difference,
                    "distance_to_nearest_town": peak.distance_to_nearest_town,
                    "nearest_town_name": peak.nearest_town_name,
                }
                for peak in peaks
            ],
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info("Results saved to: %s", filename)

    def clear_cache(self):
        """Clear GIS query cache."""
        if self.gis_service:
            self.gis_service.clear_cache()
        else:
            logger.warning("No GIS service available to clear cache")

    def get_cache_info(self) -> Optional[Dict]:
        """Get cache information (delegated to GisQueryService)."""
        if self.gis_service:
            stats = self.gis_service.get_elevation_statistics()
            return {"elevation_statistics": stats, "note": "Cache is managed internally by GisQueryService"}
        return None

    def calculate_distance(self, p1: GeoCoordinate, p2: GeoCoordinate) -> float:
        """Calculate Haversine distance (km). Delegates to parsers."""
        from gis_service.parsers import calculate_distance as _calc_dist

        return _calc_dist(p1, p2)


# ── Convenience functions ──────────────────────────────────────────


def find_peaks_with_height_difference(
    south: float, west: float, north: float, east: float, min_height_diff: float = 100.0, max_locations: int = 50
) -> List[Peak]:
    """
    Find peaks with sufficient height difference from surrounding towns.

    Args:
        south, west, north, east: Bounding box coordinates.
        min_height_diff: Minimum height difference (meters).
        max_locations: Maximum number of peaks to search.

    Returns:
        List of qualified peaks.
    """
    geotiff_path = str(res.files("light_pollution").joinpath("resources", "viirs_china_2025.tif"))
    finder = StarGazingPlaceFinder(
        min_height_difference=min_height_diff,
        light_pollution_analyzer=LightPollutionAnalyzer(geotiff_path=geotiff_path),
    )
    return finder.find_peaks_in_area(LatLonBox(south=south, west=west, north=north, east=east), max_locations)


def find_viewpoints(south: float, west: float, north: float, east: float, max_viewpoints: int = 50) -> List[Viewpoint]:
    """
    Find viewpoints in specified area, sorted by elevation.

    Args:
        south, west, north, east: Bounding box coordinates.
        max_viewpoints: Maximum number of viewpoints to search.

    Returns:
        List of viewpoints.
    """
    geotiff_path = str(res.files("light_pollution").joinpath("resources", "viirs_china_2025.tif"))
    finder = StarGazingPlaceFinder(
        min_height_difference=100.0, light_pollution_analyzer=LightPollutionAnalyzer(geotiff_path=geotiff_path)
    )
    return finder.find_viewpoints_in_area(LatLonBox(south=south, west=west, north=north, east=east), max_viewpoints)


if __name__ == "__main__":
    # Example: Search for peaks around Beijing
    logger.info("=== Peak Finder Example ===")

    bbox = LatLonBox(south=39.5, west=115.5, north=40.5, east=117.5)

    geotiff_path = str(res.files("light_pollution").joinpath("resources", "viirs_china_2025.tif"))
    finder = StarGazingPlaceFinder(
        min_height_difference=100.0, light_pollution_analyzer=LightPollutionAnalyzer(geotiff_path=geotiff_path)
    )

    peaks = finder.find_peaks_in_area(bbox, max_locations=20)

    if peaks:
        logger.info("\n=== Qualified Peaks ===")
        for i, peak in enumerate(peaks, 1):
            logger.info("%s. %s", i, peak.name)
            logger.info("   Coordinates: (%.4f, %.4f)", peak.latitude, peak.longitude)
            logger.info("   Elevation: %.1fm", peak.elevation)
            logger.info("   Height difference from %s: %.1fm", peak.nearest_town_name, peak.height_difference)
            logger.info("   Distance to nearest town: %.1fkm", peak.distance_to_nearest_town)
            logger.info("")

        finder.save_results_to_json(peaks, "mountain_peaks_results.json")
    else:
        logger.info("No qualified peaks found")
