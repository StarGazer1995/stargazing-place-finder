#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stargazing Location Comprehensive Analyzer

This module integrates peak finding, light pollution analysis, and road connectivity detection,
providing users with one-stop stargazing location assessment services.
"""

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from config import StargazingConfig

# Import related modules
from gis_service.config import load_db_config as _load_gis_db_config
from gis_service.query_service import GisQueryService
from light_pollution.light_pollution_analyzer import LightPollutionAnalyzer
from models import (
    ConfigError,
    DataError,
    GeoCoordinate,
    GeoError,
    LatLonBox,
    LightPollutionInfo,
    Location,
    NetworkError,
    NoDataError,
    StargazingLocation,
)
from road_connectivity.road_connectivity_checker import RoadConnectivityChecker

from .stargazing_place_finder import StarGazingPlaceFinder

logger = logging.getLogger(__name__)


class StargazingLocationAnalyzer:
    """
    Stargazing Location Comprehensive Analyzer

    Integrates peak finding, light pollution analysis, and road connectivity detection,
    providing comprehensive stargazing suitability analysis for peaks within specified coordinate ranges.
    """

    def __init__(
        self,
        kml_file_path: Optional[str] = None,
        images_base_path: Optional[str] = None,
        geotiff_path: Optional[str] = None,
        min_height_difference: float = 100.0,
        road_search_radius_km: float = 10.0,
        max_distance_to_road_km: float = 0.2,
        db_config_path: Optional[str] = None,
        config: Optional[StargazingConfig] = None,
    ):
        """
        Initialize stargazing location analyzer

        Args:
            kml_file_path: Light pollution KML file path (legacy backend).
                If None and geotiff_path is also None, light pollution analysis is skipped.
            images_base_path: Light pollution image file base path (legacy backend).
            geotiff_path: VIIRS GeoTIFF file path (recommended).
                If provided, uses the GeoTIFF backend instead of KML.
            min_height_difference: Minimum height difference between peaks and surrounding towns (meters)
            road_search_radius_km: Search radius for road connectivity detection (kilometers)
            max_distance_to_road_km: Maximum acceptable distance to road (km), default 0.2 (200m walk)
            db_config_path: Optional path to database config file (JSON or TOML)
            config: Centralised StargazingConfig instance. When provided, its
                values override the individual keyword defaults above.
        """
        self._config = config
        if config is not None:
            min_height_difference = config.min_height_difference
            road_search_radius_km = config.road_search_radius_km
            max_distance_to_road_km = config.max_distance_to_road_km

        # Initialize GIS service
        gis_service = None
        db_cfg = _load_gis_db_config(db_config_path)
        if db_cfg is not None:
            try:
                gis_service = GisQueryService(db_config=db_cfg)
                logger.info("GIS query service initialized")
            except (ConfigError, NetworkError) as e:
                logger.error("GIS service initialization failed: %s", e)
                gis_service = None

        # Initialize light pollution analyzer (GeoTIFF backend only)
        self.light_pollution_analyzer = None
        if geotiff_path and os.path.exists(geotiff_path):
            try:
                self.light_pollution_analyzer = LightPollutionAnalyzer(
                    geotiff_path=geotiff_path,
                )
                logger.info("Light pollution analyzer initialized (GeoTIFF backend)")
            except (ConfigError, GeoError) as e:
                logger.error("Light pollution analyzer initialization failed: %s", e)
                self.light_pollution_analyzer = None
            self.mountain_finder = StarGazingPlaceFinder(
                min_height_difference=min_height_difference,
                light_pollution_analyzer=self.light_pollution_analyzer,
                gis_service=gis_service,
                config=config,
            )
        else:
            if geotiff_path:
                logger.warning("⚠️  Warning: GeoTIFF file %s does not exist", geotiff_path)
            else:
                logger.warning("⚠️  Warning: No light pollution data file provided")
            logger.warning("⚠️  Light pollution data is an important component of stargazing location analysis")
            logger.warning("⚠️  Provide a VIIRS GeoTIFF file path via geotiff_path parameter")
            self.mountain_finder = StarGazingPlaceFinder(
                min_height_difference=min_height_difference,
                gis_service=gis_service,
            )
        # Initialize road connectivity checker with GIS service for PostGIS fast path
        self.road_checker = RoadConnectivityChecker(
            search_radius_km=road_search_radius_km,
            max_distance_to_road_km=max_distance_to_road_km,
            gis_service=gis_service,
            config=config,
        )
        logger.info("Stargazing location analyzer initialization completed")

    def close(self) -> None:
        """
        Release internal resources.

        Closes the LightPollutionAnalyzer (GeoTIFF file handle) and the
        GisQueryService (PostGIS connection pool).
        """
        if self.light_pollution_analyzer is not None:
            try:
                self.light_pollution_analyzer.close()
            except (OSError, RuntimeError, AttributeError) as e:
                logger.warning("Error closing light pollution analyzer: %s", e)
            self.light_pollution_analyzer = None

        if self.mountain_finder is not None and self.mountain_finder.gis_service is not None:
            try:
                self.mountain_finder.gis_service.close()
            except (OSError, RuntimeError, AttributeError) as e:
                logger.warning("Error closing GIS service: %s", e)

    def analyze_area(
        self,
        bbox: LatLonBox,
        max_locations: int = 50,
        location_types: List[str] = None,
        network_type: str = "drive",
        include_light_pollution: bool = True,
        include_road_connectivity: bool = True,
        min_distance_to_road_km: Optional[float] = None,
        max_distance_to_road_km: Optional[float] = None,
    ) -> List[StargazingLocation]:
        """
        Analyze stargazing locations within specified area.

        Args:
            bbox: Bounding box (LatLonBox with south/west/north/east).
            max_locations: Maximum number of locations
            location_types: Location types to search. Defaults to all types.
            network_type: Road network type ('drive', 'walk', 'bike', 'all')
            include_light_pollution: Whether to include light pollution analysis
            include_road_connectivity: Whether to include road connectivity analysis
            min_distance_to_road_km: Minimum distance to road in km (filter out places too close)
            max_distance_to_road_km: Maximum distance to road in km (filter out places too far)

        Returns:
            List of stargazing locations
        """
        if isinstance(bbox, (tuple, list)):
            bbox = LatLonBox(south=bbox[0], west=bbox[1], north=bbox[2], east=bbox[3])
        logger.info("Starting area analysis: (%s, %s, %s, %s)", bbox.south, bbox.west, bbox.north, bbox.east)
        if location_types is None:
            location_types = ["mountain_peak", "observatory", "viewpoint"]

        all_locations = self._search_locations(bbox, max_locations, location_types)
        if not all_locations:
            return []

        towns_data = self._fetch_towns_data(bbox)
        light_pollution_batch = self._batch_light_pollution(all_locations, include_light_pollution)

        # Pre-load one road network for the entire area so all parallel workers
        # share it instead of each downloading their own (30x → 1x download).
        if include_road_connectivity:
            self.road_checker.preload_network_for_bbox(bbox, network_type=network_type)

        stargazing_locations = self._parallel_analyze_locations(
            all_locations,
            towns_data,
            light_pollution_batch,
            include_road_connectivity,
            network_type,
        )

        stargazing_locations = self._filter_by_road_distance(
            stargazing_locations,
            min_distance_to_road_km,
            max_distance_to_road_km,
        )

        stargazing_locations.sort(key=lambda x: x.stargazing_score or 0, reverse=True)
        logger.info("Analysis completed, total %s stargazing locations", len(stargazing_locations))
        return stargazing_locations

    def _search_locations(
        self,
        bbox: LatLonBox,
        max_locations: int,
        location_types: List[str],
    ) -> List[Location]:
        """Search for locations by type and collect results."""
        all_locations = []
        for location_type in location_types:
            logger.info("Searching for %s...", location_type)
            if location_type == "mountain_peak":
                locations = self.mountain_finder.find_peaks_in_area(bbox, max_locations=max_locations)
            elif location_type == "observatory":
                locations = self.mountain_finder.find_observatories_in_area(bbox, max_observatories=max_locations)
            elif location_type == "viewpoint":
                locations = self.mountain_finder.find_viewpoints_in_area(bbox, max_viewpoints=max_locations)
            else:
                logger.warning("Unsupported location type %s", location_type)
                continue
            if locations:
                logger.info("Found %s %s", len(locations), location_type)
                all_locations.extend(locations)
            else:
                logger.info("No qualifying %s found", location_type)

        if not all_locations:
            logger.info("No qualifying stargazing locations found")
            return []

        # Collect all qualifying locations from all types — no per-type cap.
        # The final scoring + sort + top-N happens after scoring in analyze_area.
        logger.info("Total %s locations found, starting detailed analysis...", len(all_locations))
        return all_locations

    def _fetch_towns_data(self, bbox: LatLonBox) -> List[Dict]:
        """Fetch towns data for town density computation (optional)."""
        try:
            return self.mountain_finder.gis_service.query_locations(bbox, "town")
        except Exception as e:
            logger.warning("Failed to fetch towns data: %s", e)
            return []

    def _batch_light_pollution(
        self,
        locations: List[Location],
        include_light_pollution: bool,
    ) -> Dict[Tuple[float, float], LightPollutionInfo]:
        """Batch light pollution analysis: one GeoTIFF read instead of N per-point reads."""
        batch: Dict[Tuple[float, float], LightPollutionInfo] = {}
        if not include_light_pollution or not self.light_pollution_analyzer:
            return batch
        try:
            coords = [(loc.latitude, loc.longitude) for loc in locations]
            batch_results = self.light_pollution_analyzer.batch_analyze_coordinates(coords)
            for r in batch_results:
                lat, lon = r["coordinates"]
                batch[(lat, lon)] = r.get("pollution_info")
            logger.info("  Batch light pollution: %s locations", len(batch_results))
        except GeoError as e:
            logger.error("  Batch light pollution failed: %s", e)
        return batch

    def _parallel_analyze_locations(
        self,
        locations: List[Location],
        towns_data: List[Dict],
        light_pollution_batch: Dict[Tuple[float, float], LightPollutionInfo],
        include_road_connectivity: bool,
        network_type: str,
    ) -> List[StargazingLocation]:
        """Parallel comprehensive analysis with ThreadPoolExecutor (max_workers=4)."""
        total = len(locations)
        stargazing_locations: List[StargazingLocation] = [None] * total
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(
                    self._process_one_location,
                    location,
                    towns_data,
                    light_pollution_batch,
                    include_road_connectivity,
                    network_type,
                    i,
                    total,
                ): i
                for i, location in enumerate(locations, 1)
            }
            for future in as_completed(futures):
                idx = futures[future] - 1
                try:
                    stargazing_locations[idx] = future.result()
                except DataError as e:
                    logger.error("  Location %s analysis failed: %s", idx + 1, e)
        return [loc for loc in stargazing_locations if loc is not None]

    def _filter_by_road_distance(
        self,
        locations: List[StargazingLocation],
        min_km: Optional[float],
        max_km: Optional[float],
    ) -> List[StargazingLocation]:
        """Filter locations by road distance constraints."""
        if min_km is None and max_km is None:
            return locations
        before = len(locations)
        filtered = []
        for loc in locations:
            d = loc.distance_to_road_km
            if d is None:
                continue
            if min_km is not None and d < min_km:
                continue
            if max_km is not None and d > max_km:
                continue
            filtered.append(loc)
        after = len(filtered)
        if after < before:
            logger.info("Road distance filter: removed %s locations (%s remaining)", before - after, after)
        return filtered

    def _process_one_location(
        self,
        location,
        towns_data,
        light_pollution_batch,
        include_road_connectivity,
        network_type,
        index,
        total,
    ) -> Optional[StargazingLocation]:
        """
        Process a single location for comprehensive analysis.
        Designed for parallel execution via ThreadPoolExecutor.
        Delegates to explicit pipeline stages: Build → Enrich → Score.
        """
        logger.info("Analyzing location %s/%s: %s (%s)", index, total, location.name, location.location_type)

        # Stage 1 — Build the stargazing location object from the raw location
        stargazing_location = self._build_stargazing_object(location)

        # Stage 2 — Enrich with town density, light pollution, and road data
        self._enrich_town_density(stargazing_location, location, towns_data)
        self._enrich_light_pollution(stargazing_location, location, light_pollution_batch)
        self._enrich_road_connectivity(
            stargazing_location,
            location,
            include_road_connectivity,
            network_type,
        )

        # Stage 3 — Compute final scores, recommendation level, and notes
        self._finalize_scores(stargazing_location)

        return stargazing_location

    # ------------------------------------------------------------------
    # Pipeline sub-stages (used by _process_one_location)
    # ------------------------------------------------------------------

    @staticmethod
    def _build_stargazing_object(location: Location) -> StargazingLocation:
        """Build a StargazingLocation from a raw Location (Stage 1)."""
        return StargazingLocation(
            name=location.name,
            latitude=location.latitude,
            longitude=location.longitude,
            elevation=location.elevation,
            prominence=location.prominence or 0.0,
            distance_to_nearest_town=location.distance_to_nearest_town,
            nearest_town_name=location.nearest_town_name,
            height_difference=location.height_difference or 0.0,
            location_type=location.location_type,
            description=location.description,
        )

    def _enrich_town_density(
        self,
        stargazing_loc: StargazingLocation,
        raw_location: Location,
        towns_data: List[Dict],
    ) -> None:
        """Enrich with nearby town count (Stage 2a)."""
        if towns_data:
            stargazing_loc.nearby_town_count = self._count_nearby_towns(
                GeoCoordinate(latitude=raw_location.latitude, longitude=raw_location.longitude),
                towns_data,
                radius_km=20.0,
            )

    def _enrich_light_pollution(
        self,
        stargazing_loc: StargazingLocation,
        raw_location: Location,
        light_pollution_batch: Dict[Tuple[float, float], LightPollutionInfo],
    ) -> None:
        """Enrich with light pollution data from pre-batched results (Stage 2b)."""
        if not light_pollution_batch:
            return
        light_info = light_pollution_batch.get((raw_location.latitude, raw_location.longitude))
        if light_info:
            stargazing_loc.light_pollution_rgb = light_info.rgb
            stargazing_loc.light_pollution_hex = light_info.hex
            stargazing_loc.light_pollution_brightness = light_info.brightness
            stargazing_loc.light_pollution_level = light_info.pollution_level
            stargazing_loc.light_pollution_bortle = light_info.bortle
            stargazing_loc.light_pollution_overlay = light_info.overlay_name

    def _enrich_road_connectivity(
        self,
        stargazing_loc: StargazingLocation,
        raw_location: Location,
        include_road_connectivity: bool,
        network_type: str,
    ) -> None:
        """Enrich with road accessibility info (Stage 2c).

        Only checks road connectivity for natural features (mountain_peak).
        Observatories and viewpoints are man-made and always have road access.
        """
        if not include_road_connectivity:
            return
        if raw_location.location_type != "mountain_peak":
            stargazing_loc.road_accessible = True
            stargazing_loc.distance_to_road_km = 0.0
            return
        try:
            road_info = self.road_checker.get_accessibility_info(
                GeoCoordinate(latitude=raw_location.latitude, longitude=raw_location.longitude),
                network_type=network_type,
            )
            stargazing_loc.road_accessible = road_info["accessible"]
            stargazing_loc.distance_to_road_km = road_info["distance_to_road_km"]
            stargazing_loc.road_network_type = network_type
            stargazing_loc.road_check_error = road_info.get("error")
        except (NetworkError, NoDataError) as e:
            logger.error("  Road connectivity analysis failed: %s", e)
            stargazing_loc.road_check_error = str(e)

    def _finalize_scores(self, stargazing_loc: StargazingLocation) -> None:
        """Compute final score, recommendation level, and analysis notes (Stage 3)."""
        stargazing_loc.stargazing_score = self._calculate_stargazing_score(stargazing_loc)
        stargazing_loc.recommendation_level = self._get_recommendation_level_with_warning(stargazing_loc)
        stargazing_loc.analysis_notes = self._generate_analysis_notes(stargazing_loc)

    def _count_nearby_towns(self, point: GeoCoordinate, towns: List[Dict], radius_km: float = 20.0) -> int:
        """Count additional towns within a given radius (excluding the nearest).

        Args:
            point: Location coordinate.
            towns: List of town data dicts
            radius_km: Search radius in km

        Returns:
            Number of additional towns within radius (0 = only nearest town or none)
        """
        if not towns:
            return 0

        distances = []
        for town in towns:
            try:
                if town.get("type") == "node":
                    t_lat, t_lon = town["lat"], town["lon"]
                elif "center" in town:
                    t_lat, t_lon = town["center"]["lat"], town["center"]["lon"]
                else:
                    continue
            except (KeyError, TypeError):
                continue

            town_point = GeoCoordinate(latitude=t_lat, longitude=t_lon)
            distance = self.mountain_finder.calculate_distance(point, town_point)
            if distance <= radius_km:
                distances.append(distance)

        # Exclude the nearest town (count additional towns only)
        return max(0, len(distances) - 1)

    # Bortle → score mapping (0–35 points)
    _BORTLE_SCORES = {1: 35, 2: 31, 3: 26, 4: 20, 5: 14, 6: 8, 7: 3, 8: 1, 9: 0}

    def _calculate_stargazing_score(self, location: StargazingLocation) -> float:
        """
        Calculate comprehensive score for stargazing location.

        Scoring weights (total 100 points, configurable via StargazingConfig):
        - Light pollution  (default 35): Bortle scale — the most critical factor
        - Town isolation   (default 20): Distance to nearest town + density penalty
        - Road access      (default 20): Practical usability
        - Elevation+terrain(default 15): Altitude + height above surrounding towns
        - Location type    (default 10): Mountain prominence, observatory, viewpoint

        Road distance now uses a smooth sigmoid decay instead of a hard
        200m threshold, and town isolation uses a continuous logarithmic
        function instead of discrete buckets.

        Args:
            location: Stargazing location object

        Returns:
            Comprehensive score (0-100 points)
        """
        cfg = self._config
        score = 0.0
        score += self._score_light_pollution(location, cfg.weight_light_pollution if cfg else 35)
        score += self._score_town_isolation(location, cfg)
        score += self._score_road_accessibility(location, cfg)
        score += self._score_elevation_terrain(location, cfg.weight_elevation if cfg else 15)
        score += self._score_location_type(location, cfg.weight_location_type if cfg else 10)
        return round(score, 1)

    def _score_light_pollution(self, location: StargazingLocation, max_weight: float = 35) -> float:
        """Light Pollution — Bortle-based or brightness fallback. Weight configurable."""
        scale = max_weight / 35.0
        if location.light_pollution_bortle is not None:
            return self._BORTLE_SCORES.get(location.light_pollution_bortle, 18) * scale

        if location.light_pollution_brightness is not None:
            b = location.light_pollution_brightness
            if b < 30:
                return 35 * scale
            if b < 60:
                return 31 * scale
            if b < 90:
                return 26 * scale
            if b < 120:
                return 20 * scale
            if b < 150:
                return 14 * scale
            if b < 180:
                return 8 * scale
            if b < 210:
                return 3 * scale
            if b < 240:
                return 1 * scale
            return 0

        if location.light_pollution_level:
            legacy = {
                "Extremely Low": 35,
                "Very Low": 31,
                "Low": 26,
                "Medium": 20,
                "High": 14,
                "Very High": 8,
                "Extremely High": 3,
            }
            return legacy.get(location.light_pollution_level, 18) * scale

        logger.warning("⚠️  Warning: %s lacks light pollution data, scoring accuracy affected", location.name)
        return 18 * scale

    def _score_town_isolation(self, location: StargazingLocation, cfg=None) -> float:
        """Town Isolation — continuous logarithmic function of distance.

        Replaces discrete distance buckets with a smooth curve:
        ~0 at 0km, ~10 at 20km, ~16 at 50km, ~20 at 100km+.
        """
        import math

        max_weight = cfg.weight_town_isolation if cfg else 20
        town_dist = location.distance_to_nearest_town
        if town_dist is None or town_dist <= 0:
            return max_weight * 0.4  # Unknown → 40% of max

        # Logarithmic scale: scores ~60% of max at 20km, ~80% at 50km
        dist_score = max_weight * min(1.0, math.log(town_dist + 1) / math.log(51))

        # Density penalty: -2 per additional town within 20km (max -8)
        density_penalty = min(location.nearby_town_count * 2, 8)
        return max(0.0, float(dist_score - density_penalty))

    def _score_road_accessibility(self, location: StargazingLocation, cfg=None) -> float:
        """Road Accessibility — smooth sigmoid decay instead of hard 200m cutoff.

        Uses a smooth decay centred on the half-decay distance (default 200m).
        Locations closer than the half-decay distance score >50%;
        locations farther score progressively less, without a cliff.
        """
        max_weight = cfg.weight_road_access if cfg else 20
        # Explicitly not accessible → zero score regardless of distance
        if location.road_accessible is False:
            return 0
        if location.distance_to_road_km is None:
            return max_weight * 0.5  # Unknown → middle
        d = location.distance_to_road_km
        half = cfg.road_distance_decay_km if cfg else 0.2
        # Logistic decay: score = max / (1 + (d/half)^2)
        # d=0 → max, d=half → max/2, d→∞ → 0
        ratio = d / half
        score = max_weight / (1.0 + ratio * ratio)
        # Bonus for ideal range (50-200m by default): slight bump near half
        if 0.25 <= ratio <= 1.0:
            score *= 1.1
        return round(min(max_weight, score), 1)

    def _score_elevation_terrain(self, location: StargazingLocation, max_weight: float = 15) -> float:
        """Elevation + Terrain. Combines altitude and height above towns."""
        if not location.elevation:
            return 0
        scale = max_weight / 15.0
        elevation_score = min(location.elevation / 200.0, 8.0)
        height_bonus = 0.0
        if location.height_difference:
            height_bonus = min(location.height_difference / 200.0, 7.0)
        return (elevation_score + height_bonus) * scale

    def _score_location_type(self, location: StargazingLocation, max_weight: float = 10) -> float:
        """Location Type. Weight configurable."""
        scale = max_weight / 10.0
        if location.is_mountain_peak():
            if location.prominence:
                return min(location.prominence / 200.0, 10.0) * scale
            return 0
        if location.is_observatory():
            return 6 * scale
        if location.is_viewpoint():
            if location.height_difference:
                return min(location.height_difference / 150.0, 10.0) * scale
            return 5 * scale
        return 0

    def _get_recommendation_level_with_warning(self, location: StargazingLocation) -> str:
        """
        Get recommendation level based on score, add warning when light pollution data is missing

        Args:
            location: Stargazing location object

        Returns:
            Recommendation level description (including warning information)
        """
        base_level = self._get_recommendation_level(location.stargazing_score)

        # Check if light pollution data is missing
        if location.light_pollution_brightness is None:
            return base_level + " (⚠️Missing light pollution data)"

        return base_level

    def _get_recommendation_level(self, score: Optional[float]) -> str:
        """
        Get recommendation level based on score

        Args:
            score: Comprehensive score

        Returns:
            Recommendation level description
        """
        if score is None:
            return "Unrated"

        if score >= 80:
            return "Highly Recommended ⭐⭐⭐⭐⭐"
        elif score >= 70:
            return "Recommended ⭐⭐⭐⭐"
        elif score >= 60:
            return "Generally Recommended ⭐⭐⭐"
        elif score >= 50:
            return "Consider ⭐⭐"
        else:
            return "Not Recommended ⭐"

    def _generate_analysis_notes(self, location: StargazingLocation) -> str:
        """
        Generate analysis notes

        Args:
            location: Stargazing location object

        Returns:
            Analysis notes string
        """
        notes = []

        # Altitude advantage
        if location.height_difference > 300:
            notes.append(
                f"Significant altitude advantage, {location.height_difference:.0f}m higher than {location.nearest_town_name}"
            )
        elif location.height_difference > 150:
            notes.append(
                f"Some altitude advantage, {location.height_difference:.0f}m higher than {location.nearest_town_name}"
            )

        # Light pollution status
        if location.light_pollution_brightness is not None:
            if location.light_pollution_brightness < 64:
                notes.append("Low light pollution level, good stargazing conditions")
            elif location.light_pollution_brightness < 128:
                notes.append("Medium light pollution level, average stargazing conditions")
            else:
                notes.append("Serious light pollution, may affect stargazing")
        else:
            notes.append("⚠️ Missing light pollution data, cannot accurately assess stargazing conditions")

        # Road accessibility
        if location.road_accessible is True:
            if location.distance_to_road_km and location.distance_to_road_km < 1:
                notes.append("Convenient transportation, very close to road")
            else:
                notes.append("Road accessible")
        elif location.road_accessible is False:
            notes.append("Road not accessible, hiking required")

        # Distance to town
        if location.distance_to_nearest_town > 50:
            notes.append("Far from town, quiet environment")
        elif location.distance_to_nearest_town < 10:
            notes.append("Close to town, may have light pollution impact")

        return "; ".join(notes) if notes else "No special notes"

    def save_results_to_json(self, locations: List[StargazingLocation], filename: str) -> None:
        """
        Save analysis results to JSON file

        Args:
            locations: List of stargazing locations
            filename: Output filename
        """
        # Convert to serializable format
        results = {
            "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_locations": len(locations),
            "analysis_parameters": {
                "min_height_difference": self.mountain_finder.min_height_difference,
                "road_search_radius_km": self.road_checker.search_radius_km,
                "has_light_pollution_analyzer": self.light_pollution_analyzer is not None,
            },
            "locations": [location.model_dump(mode="json", exclude_none=True) for location in locations],
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        logger.info("Analysis results saved to: %s", filename)

    def get_top_recommendations(self, locations: List[StargazingLocation], top_n: int = 5) -> List[StargazingLocation]:
        """
        Get top-rated recommended locations

        Args:
            locations: List of stargazing locations
            top_n: Number of recommendations to return

        Returns:
            List of highest-rated stargazing locations
        """
        # Sort by score and return top N
        sorted_locations = sorted(locations, key=lambda x: x.stargazing_score or 0, reverse=True)
        return sorted_locations[:top_n]

    def print_analysis_summary(self, locations: List[StargazingLocation]) -> None:
        """
        Print analysis results summary

        Args:
            locations: List of stargazing locations
        """
        if not locations:
            logger.info("No stargazing locations found")
            return

        logger.info("\n=== Stargazing Location Analysis Summary ===")
        logger.info("Total %s stargazing locations found", len(locations))

        # Check light pollution data completeness
        locations_with_light_data = sum(1 for loc in locations if loc.light_pollution_brightness is not None)
        locations_without_light_data = len(locations) - locations_with_light_data

        if locations_without_light_data > 0:
            logger.warning("\n⚠️  Data Completeness Reminder:")
            logger.warning("   - %s locations have complete light pollution data", locations_with_light_data)
            logger.warning("   - %s locations lack light pollution data", locations_without_light_data)
            logger.warning("   - Recommend providing light pollution KML file for more accurate assessment")

        # Statistics of recommendation level distribution
        recommendation_counts = {}
        for location in locations:
            level = location.recommendation_level
            recommendation_counts[level] = recommendation_counts.get(level, 0) + 1

        logger.info("\nRecommendation Level Distribution:")
        for level, count in recommendation_counts.items():
            logger.info("  %s: %s locations", level, count)

        # Display top 5 recommended locations
        top_locations = self.get_top_recommendations(locations, 5)
        logger.info("\n=== Top 5 Recommended Locations ===")
        for i, location in enumerate(top_locations, 1):
            logger.info("\n%s. %s", i, location.name)
            logger.info("   Coordinates: (%.4f, %.4f)", location.latitude, location.longitude)
            logger.info("   Elevation: %.1fm", location.elevation)
            logger.info("   Overall Score: %s/100", location.stargazing_score)
            logger.info("   Recommendation Level: %s", location.recommendation_level)
            if location.light_pollution_brightness is not None:
                logger.info("   Light Pollution: %s", location.light_pollution_level)
            else:
                logger.info("   Light Pollution: ⚠️ Data Missing")
            if location.road_accessible is not None:
                accessibility = "Accessible" if location.road_accessible else "Not Accessible"
                logger.info("   Road: %s", accessibility)
            logger.info("   Notes: %s", location.analysis_notes)


def analyze_stargazing_area(
    south: float,
    west: float,
    north: float,
    east: float,
    kml_file_path: Optional[str] = None,
    geotiff_path: Optional[str] = None,
    max_locations: int = 30,
    location_types: List[str] = None,
    min_height_diff: float = 100.0,
    road_radius_km: float = 10.0,
    network_type: str = "drive",
    db_config_path: Optional[str] = None,
    min_distance_to_road_km: Optional[float] = None,
    max_distance_to_road_km: Optional[float] = None,
    config: Optional[StargazingConfig] = None,
) -> List[StargazingLocation]:
    """
    Convenience function: Analyze stargazing locations in specified area

    Args:
        south, west, north, east: Bounding box coordinates
        kml_file_path: Deprecated, kept for backward compatibility.
        geotiff_path: VIIRS GeoTIFF file path. If None, uses the GeoTIFF backend
            with default bundled data (viirs_china_2025.tif).
        max_locations: Maximum number of locations
        location_types: List of location types, options: ['mountain_peak', 'observatory', 'viewpoint']
        min_height_diff: Minimum height difference (only for peaks)
        road_radius_km: Road search radius
        network_type: Network type
        db_config_path: Optional path to database config file
        min_distance_to_road_km: Minimum distance to road in km (filter out places too close)
        max_distance_to_road_km: Maximum distance to road in km (filter out places too far)
        config: Centralised StargazingConfig instance. When provided, its
            values override the individual keyword defaults above.

    Returns:
        List of stargazing locations
    """
    if config is not None:
        min_height_diff = config.min_height_difference
        road_radius_km = config.road_search_radius_km
        if max_distance_to_road_km is None:
            max_distance_to_road_km = config.max_distance_to_road_km
        if min_distance_to_road_km is None:
            min_distance_to_road_km = config.min_distance_to_road_km
    analyzer = StargazingLocationAnalyzer(
        geotiff_path=geotiff_path,
        kml_file_path=kml_file_path,
        min_height_difference=min_height_diff,
        road_search_radius_km=road_radius_km,
        max_distance_to_road_km=max_distance_to_road_km,
        db_config_path=db_config_path,
        config=config,
    )

    bbox = (south, west, north, east)
    locations = analyzer.analyze_area(
        bbox=bbox,
        max_locations=max_locations,
        location_types=location_types,
        network_type=network_type,
        include_light_pollution=True,
        include_road_connectivity=True,
        min_distance_to_road_km=min_distance_to_road_km,
        max_distance_to_road_km=max_distance_to_road_km,
    )

    # Print summary
    analyzer.print_analysis_summary(locations)

    return locations


if __name__ == "__main__":
    # Example: Analyze stargazing locations around Beijing
    logger.info("=== Stargazing Location Comprehensive Analyzer Example ===")

    # Define analysis area (around Beijing)
    bbox = (39.5, 115.5, 40.5, 117.5)  # (south, west, north, east)

    # Create analyzer (no KML file provided here, so skip light pollution analysis)
    analyzer = StargazingLocationAnalyzer(
        kml_file_path=None,  # If you have light pollution KML file, provide path here
        min_height_difference=100.0,
        road_search_radius_km=10.0,
    )

    # Analyze area
    locations = analyzer.analyze_area(
        bbox=bbox,
        max_locations=20,
        location_types=["mountain_peak", "observatory", "viewpoint"],
        network_type="drive",
        include_light_pollution=False,  # Set to False when no KML file
        include_road_connectivity=True,
    )

    # Save results
    if locations:
        analyzer.save_results_to_json(locations, "stargazing_analysis_results.json")

        # Print summary
        analyzer.print_analysis_summary(locations)
    else:
        logger.info("No qualified stargazing locations found")
