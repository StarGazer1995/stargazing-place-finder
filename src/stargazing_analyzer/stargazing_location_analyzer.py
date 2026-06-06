#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stargazing Location Comprehensive Analyzer

This module integrates peak finding, light pollution analysis, and road connectivity detection,
providing users with one-stop stargazing location assessment services.
"""

import json
import os
from typing import List, Dict, Tuple, Optional, Any
import time
from datetime import datetime

# Import related modules
try:
    from .stargazing_place_finder import StarGazingPlaceFinder, Peak, PostGISClient
    from light_pollution.light_pollution_analyzer import LightPollutionAnalyzer
    from road_connectivity.road_connectivity_checker import RoadConnectivityChecker
    from src.models import StargazingLocation
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'src'))
    from stargazing_analyzer.stargazing_place_finder import StarGazingPlaceFinder, Peak, PostGISClient
    from light_pollution.light_pollution_analyzer import LightPollutionAnalyzer
    from road_connectivity.road_connectivity_checker import RoadConnectivityChecker
    from models import StargazingLocation


class StargazingLocationAnalyzer:
    """
    Stargazing Location Comprehensive Analyzer
    
    Integrates peak finding, light pollution analysis, and road connectivity detection,
    providing comprehensive stargazing suitability analysis for peaks within specified coordinate ranges.
    """
    
    def __init__(self, 
                 kml_file_path: Optional[str] = None,
                 images_base_path: Optional[str] = None,
                 geotiff_path: Optional[str] = None,
                 min_height_difference: float = 100.0,
                 road_search_radius_km: float = 10.0,
                 db_config_path: Optional[str] = None):
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
            db_config_path: Optional path to database config file (JSON or TOML)
        """
        # Initialize peak finder
        db_client = None
        cfg_path = db_config_path or os.environ.get('DB_CONFIG_PATH')
        if cfg_path and os.path.exists(cfg_path):
            try:
                db_cfg = self._load_db_config(cfg_path)
                db_client = PostGISClient(db_cfg)
                print("PostGIS client initialized successfully")
            except Exception as e:
                print(f"PostGIS client initialization failed: {e}")
                db_client = None
        
        # Initialize light pollution analyzer
        self.light_pollution_analyzer = None
        if geotiff_path and os.path.exists(geotiff_path):
            try:
                self.light_pollution_analyzer = LightPollutionAnalyzer(
                    geotiff_path=geotiff_path,
                )
                print("Light pollution analyzer initialized (GeoTIFF backend)")
            except Exception as e:
                print(f"Light pollution analyzer initialization failed: {e}")
                self.light_pollution_analyzer = None
            self.mountain_finder = StarGazingPlaceFinder(
                min_height_difference=min_height_difference,
                light_pollution_analyzer=self.light_pollution_analyzer,
                db_client=db_client,
            )
        elif kml_file_path and os.path.exists(kml_file_path):
            try:
                self.light_pollution_analyzer = LightPollutionAnalyzer(
                    kml_file_path=kml_file_path,
                    images_base_path=images_base_path,
                )
                print("Light pollution analyzer initialized (KML backend)")
            except Exception as e:
                print(f"Light pollution analyzer initialization failed: {e}")
                self.light_pollution_analyzer = None
            self.mountain_finder = StarGazingPlaceFinder(
                min_height_difference=min_height_difference,
                light_pollution_analyzer=self.light_pollution_analyzer,
                db_client=db_client,
            )
        else:
            if kml_file_path:
                print(f"⚠️  Warning: KML file {kml_file_path} does not exist")
            else:
                print("⚠️  Warning: No light pollution data file provided")
            print("⚠️  Light pollution data is an important component of stargazing location analysis")
            print("⚠️  Recommend downloading light pollution map KML files from:")
            print("   - Light Pollution Map: https://www.lightpollutionmap.info/")
            print("   - Dark Site Finder: https://darksitefinder.com/")
            self.mountain_finder = StarGazingPlaceFinder(min_height_difference=min_height_difference, db_client=db_client)
        
        # Initialize road connectivity checker
        self.road_checker = RoadConnectivityChecker(search_radius_km=road_search_radius_km)
        
        print("Stargazing location analyzer initialization completed")

    def _load_db_config(self, path: str) -> Dict[str, Any]:
        """
        Load database configuration from a file path (JSON or TOML).
        
        Args:
            path: File path to configuration
        
        Returns:
            Parsed configuration dictionary
        """
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.json', ''):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        elif ext == '.toml':
            try:
                import tomllib  # Python 3.11+
                with open(path, 'rb') as f:
                    return tomllib.load(f)
            except Exception as e:
                raise RuntimeError(f"Failed to parse TOML config: {e}")
        else:
            raise ValueError(f"Unsupported config format: {ext}")
    
    def analyze_area(self, 
                    bbox: Tuple[float, float, float, float],
                    max_locations: int = 50,
                    location_types: List[str] = None,
                    network_type: str = 'drive',
                    include_light_pollution: bool = True,
                    include_road_connectivity: bool = True) -> List[StargazingLocation]:
        """
        Analyze stargazing locations within specified area (supports multiple types like peaks, observatories, viewpoints)
        
        Args:
            bbox: Bounding box (south, west, north, east)
            max_locations: Maximum number of locations
            location_types: List of location types, options: ['mountain_peak', 'observatory', 'viewpoint']
                          If None, defaults to searching all types
            network_type: Road network type ('drive', 'walk', 'bike', 'all')
            include_light_pollution: Whether to include light pollution analysis
            include_road_connectivity: Whether to include road connectivity analysis
            
        Returns:
            List of stargazing locations
        """
        print(f"Starting area analysis: {bbox}")
        
        # Default to searching all types of locations
        if location_types is None:
            location_types = ['mountain_peak', 'observatory', 'viewpoint']
        
        all_locations = []
        
        # 1. Search for locations based on specified types
        for location_type in location_types:
            print(f"Searching for {location_type}...")
            
            if location_type == 'mountain_peak':
                locations = self.mountain_finder.find_peaks_in_area(bbox, max_locations=max_locations)
            elif location_type == 'observatory':
                locations = self.mountain_finder.find_observatories_in_area(bbox, max_observatories=max_locations)
            elif location_type == 'viewpoint':
                locations = self.mountain_finder.find_viewpoints_in_area(bbox, max_viewpoints=max_locations)
            else:
                print(f"  Warning: Unsupported location type {location_type}")
                continue
            
            if locations:
                print(f"Found {len(locations)} {location_type}")
                all_locations.extend(locations)
            else:
                print(f"No qualifying {location_type} found")
        
        if not all_locations:
            print("No qualifying stargazing locations found")
            return []
        
        # Limit total number
        if len(all_locations) > max_locations:
            all_locations = all_locations[:max_locations]
        
        print(f"Total {len(all_locations)} locations found, starting detailed analysis...")
        
        if os.environ.get('FAST_TESTS') == '1':
            include_road_connectivity = False
        
        # Fetch towns data once for town density computation
        towns_data = []
        try:
            towns_data = self.mountain_finder.get_towns_from_overpass(bbox)
        except Exception:
            pass  # Town density is optional
        
        # 2. Perform comprehensive analysis for each location
        stargazing_locations = []
        for i, location in enumerate(all_locations, 1):
            print(f"Analyzing location {i}/{len(all_locations)}: {location.name} ({location.location_type})")
            
            # Create stargazing location object, adapted to unified Location class
            stargazing_location = StargazingLocation(
                name=location.name,
                latitude=location.latitude,
                longitude=location.longitude,
                elevation=location.elevation,
                prominence=location.prominence or 0.0,
                distance_to_nearest_town=location.distance_to_nearest_town,
                nearest_town_name=location.nearest_town_name,
                height_difference=location.height_difference or 0.0,
                location_type=location.location_type,
                description=location.description
            )
            
            # Compute nearby town density
            if towns_data:
                stargazing_location.nearby_town_count = self._count_nearby_towns(
                    location.latitude, location.longitude, towns_data, radius_km=20.0
                )
            
            # 3. Light pollution analysis
            if include_light_pollution:
                if self.light_pollution_analyzer:
                    try:
                        light_info = self.light_pollution_analyzer.get_light_pollution_color(
                            location.latitude, location.longitude
                        )
                        if light_info:
                            stargazing_location.light_pollution_rgb = light_info.rgb
                            stargazing_location.light_pollution_hex = light_info.hex
                            stargazing_location.light_pollution_brightness = light_info.brightness
                            stargazing_location.light_pollution_level = light_info.pollution_level
                            stargazing_location.light_pollution_bortle = light_info.bortle
                            stargazing_location.light_pollution_overlay = light_info.overlay_name
                    except Exception as e:
                        print(f"  Light pollution analysis failed: {e}")
                else:
                    print(f"  ⚠️  Warning: Cannot get light pollution data for {location.name} - no light pollution data file provided")
            
            # 4. Road connectivity analysis
            if include_road_connectivity:
                try:
                    road_info = self.road_checker.get_accessibility_info(
                        location.latitude, location.longitude, network_type=network_type
                    )
                    stargazing_location.road_accessible = road_info['accessible']
                    stargazing_location.distance_to_road_km = road_info['distance_to_road_km']
                    stargazing_location.road_network_type = network_type
                    stargazing_location.road_check_error = road_info.get('error')
                except Exception as e:
                    print(f"  Road connectivity analysis failed: {e}")
                    stargazing_location.road_check_error = str(e)
            
            # 5. Calculate comprehensive score
            stargazing_location.stargazing_score = self._calculate_stargazing_score(stargazing_location)
            stargazing_location.recommendation_level = self._get_recommendation_level_with_warning(stargazing_location)
            stargazing_location.analysis_notes = self._generate_analysis_notes(stargazing_location)
            
            stargazing_locations.append(stargazing_location)
            
            if os.environ.get('FAST_TESTS') != '1':
                time.sleep(0.5)
        
        # Sort by score
        stargazing_locations.sort(key=lambda x: x.stargazing_score or 0, reverse=True)
        
        print(f"Analysis completed, total {len(stargazing_locations)} stargazing locations")
        return stargazing_locations
    
    def _count_nearby_towns(self, lat: float, lon: float, 
                            towns: List[Dict], radius_km: float = 20.0) -> int:
        """Count additional towns within a given radius (excluding the nearest).
        
        Args:
            lat, lon: Location coordinates
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
                if town.get('type') == 'node':
                    t_lat, t_lon = town['lat'], town['lon']
                elif 'center' in town:
                    t_lat, t_lon = town['center']['lat'], town['center']['lon']
                else:
                    continue
            except (KeyError, TypeError):
                continue
            
            distance = self.mountain_finder.calculate_distance(lat, lon, t_lat, t_lon)
            if distance <= radius_km:
                distances.append(distance)
        
        # Exclude the nearest town (count additional towns only)
        return max(0, len(distances) - 1)
    
    # Bortle → score mapping (0–35 points)
    _BORTLE_SCORES = {1: 35, 2: 31, 3: 26, 4: 20, 5: 14, 6: 8, 7: 3, 8: 1, 9: 0}
    
    def _calculate_stargazing_score(self, location: StargazingLocation) -> float:
        """
        Calculate comprehensive score for stargazing location.
        
        Scoring weights (total 100 points):
        - Light pollution  (0-35): Bortle scale — the most critical factor
        - Town isolation   (0-20): Distance to nearest town + density penalty
        - Road access      (0-20): Practical usability
        - Elevation+terrain(0-15): Altitude + height above surrounding towns
        - Location type    (0-10): Mountain prominence, observatory, viewpoint
        
        Args:
            location: Stargazing location object
            
        Returns:
            Comprehensive score (0-100 points)
        """
        score = 0.0
        
        # ================================================================
        # 1. Light Pollution (0-35 points) — Bortle-based
        # ================================================================
        if location.light_pollution_bortle is not None:
            score += self._BORTLE_SCORES.get(location.light_pollution_bortle, 18)
        elif location.light_pollution_brightness is not None:
            # Fallback: approximate Bortle from brightness, then score
            b = location.light_pollution_brightness
            if b < 30:
                score += 35      # ~Bortle 1
            elif b < 60:
                score += 31      # ~Bortle 2
            elif b < 90:
                score += 26      # ~Bortle 3
            elif b < 120:
                score += 20      # ~Bortle 4
            elif b < 150:
                score += 14      # ~Bortle 5
            elif b < 180:
                score += 8       # ~Bortle 6
            elif b < 210:
                score += 3       # ~Bortle 7
            elif b < 240:
                score += 1       # ~Bortle 8
            else:
                score += 0       # ~Bortle 9
        elif location.light_pollution_level:
            # Legacy string matching for old KML data
            legacy = {
                'Extremely Low': 35, 'Very Low': 31, 'Low': 26, 'Medium': 20,
                'High': 14, 'Very High': 8, 'Extremely High': 3
            }
            score += legacy.get(location.light_pollution_level, 18)
        else:
            print(f"⚠️  Warning: {location.name} lacks light pollution data, scoring accuracy affected")
            score += 18  # Conservative middle
        
        # ================================================================
        # 2. Town Isolation (0-20 points) — Distance + density
        # ================================================================
        town_dist = location.distance_to_nearest_town
        if town_dist is not None and town_dist > 0:
            if town_dist >= 50:
                dist_score = 16
            elif town_dist >= 30:
                dist_score = 14
            elif town_dist >= 20:
                dist_score = 11
            elif town_dist >= 10:
                dist_score = 7
            elif town_dist >= 5:
                dist_score = 3
            else:
                dist_score = 0
            
            # Density penalty: -2 per additional town within 20km (max -8)
            density_penalty = min(location.nearby_town_count * 2, 8)
            score += max(0, dist_score - density_penalty)
        else:
            score += 8  # Unknown town distance → medium
        
        # ================================================================
        # 3. Road Accessibility (0-20 points)
        # ================================================================
        if location.road_accessible is not None:
            if location.road_accessible:
                if location.distance_to_road_km is not None:
                    d = location.distance_to_road_km
                    if d < 0.5:
                        score += 14   # Very close — convenient but potential light/noise
                    elif d <= 5:
                        score += 20   # Ideal: remote enough yet accessible
                    elif d <= 10:
                        score += 16   # Acceptable distance
                    elif d <= 20:
                        score += 10   # Far, but reachable
                    else:
                        score += 4    # Very far — poor accessibility
                else:
                    score += 12       # Accessible but distance unknown
            else:
                score += 0            # Not accessible at all
        else:
            score += 10               # Unknown status
        
        # ================================================================
        # 4. Elevation + Terrain (0-15 points)
        #    Combines absolute altitude and height above nearest town
        # ================================================================
        if location.elevation:
            # Base elevation: 1pt per 200m, capped at 8 (1600m)
            elevation_score = min(location.elevation / 200.0, 8.0)
            
            # Height-difference bonus: the higher above nearest town, the better
            # (above the light/haze layer)
            height_bonus = 0.0
            if location.height_difference:
                height_bonus = min(location.height_difference / 200.0, 7.0)
            
            score += elevation_score + height_bonus
        
        # ================================================================
        # 5. Location Type (0-10 points)
        # ================================================================
        if location.is_mountain_peak():
            if location.prominence:
                # 1pt per 200m prominence, capped at 10 (2000m)
                score += min(location.prominence / 200.0, 10.0)
        elif location.is_observatory():
            score += 6   # Observatory base (city observatories exist)
        elif location.is_viewpoint():
            if location.height_difference:
                score += min(location.height_difference / 150.0, 10.0)
            else:
                score += 5
        
        return round(score, 1)
    
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
            notes.append(f"Significant altitude advantage, {location.height_difference:.0f}m higher than {location.nearest_town_name}")
        elif location.height_difference > 150:
            notes.append(f"Some altitude advantage, {location.height_difference:.0f}m higher than {location.nearest_town_name}")
        
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
                "has_light_pollution_analyzer": self.light_pollution_analyzer is not None
            },
            "locations": [location.model_dump(mode='json', exclude_none=True) for location in locations]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"Analysis results saved to: {filename}")
    
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
            print("No stargazing locations found")
            return
        
        print("\n=== Stargazing Location Analysis Summary ===")
        print(f"Total {len(locations)} stargazing locations found")
        
        # Check light pollution data completeness
        locations_with_light_data = sum(1 for loc in locations if loc.light_pollution_brightness is not None)
        locations_without_light_data = len(locations) - locations_with_light_data
        
        if locations_without_light_data > 0:
            print(f"\n⚠️  Data Completeness Reminder:")
            print(f"   - {locations_with_light_data} locations have complete light pollution data")
            print(f"   - {locations_without_light_data} locations lack light pollution data")
            print(f"   - Recommend providing light pollution KML file for more accurate assessment")
        
        # Statistics of recommendation level distribution
        recommendation_counts = {}
        for location in locations:
            level = location.recommendation_level
            recommendation_counts[level] = recommendation_counts.get(level, 0) + 1
        
        print("\nRecommendation Level Distribution:")
        for level, count in recommendation_counts.items():
            print(f"  {level}: {count} locations")
        
        # Display top 5 recommended locations
        top_locations = self.get_top_recommendations(locations, 5)
        print("\n=== Top 5 Recommended Locations ===")
        for i, location in enumerate(top_locations, 1):
            print(f"\n{i}. {location.name}")
            print(f"   Coordinates: ({location.latitude:.4f}, {location.longitude:.4f})")
            print(f"   Elevation: {location.elevation:.1f}m")
            print(f"   Overall Score: {location.stargazing_score}/100")
            print(f"   Recommendation Level: {location.recommendation_level}")
            if location.light_pollution_brightness is not None:
                print(f"   Light Pollution: {location.light_pollution_level}")
            else:
                print(f"   Light Pollution: ⚠️ Data Missing")
            if location.road_accessible is not None:
                accessibility = "Accessible" if location.road_accessible else "Not Accessible"
                print(f"   Road: {accessibility}")
            print(f"   Notes: {location.analysis_notes}")


def analyze_stargazing_area(south: float, west: float, north: float, east: float,
                           kml_file_path: Optional[str] = None,
                           max_locations: int = 30,
                           location_types: List[str] = None,
                           min_height_diff: float = 100.0,
                           road_radius_km: float = 10.0,
                           network_type: str = 'drive',
                           db_config_path: Optional[str] = None) -> List[StargazingLocation]:
    """
    Convenience function: Analyze stargazing locations in specified area
    
    Args:
        south, west, north, east: Bounding box coordinates
        kml_file_path: Light pollution KML file path (strongly recommended)
        max_locations: Maximum number of locations
        location_types: List of location types, options: ['mountain_peak', 'observatory', 'viewpoint']
        min_height_diff: Minimum height difference (only for peaks)
        road_radius_km: Road search radius
        network_type: Network type
        db_config_path: Optional path to database config file
        
    Returns:
        List of stargazing locations
        
    Note:
        Light pollution data is crucial for accurate stargazing location assessment.
        If kml_file_path is not provided, analysis accuracy will be affected.
    """
    if kml_file_path is None:
        print("⚠️  Warning: Convenience function did not provide light pollution data file")
        print("⚠️  This will affect the accuracy of stargazing location assessment")
    
    analyzer = StargazingLocationAnalyzer(
        kml_file_path=kml_file_path,
        min_height_difference=min_height_diff,
        road_search_radius_km=road_radius_km,
        db_config_path=db_config_path
    )
    
    bbox = (south, west, north, east)
    locations = analyzer.analyze_area(
        bbox=bbox,
        max_locations=max_locations,
        location_types=location_types,
        network_type=network_type,
        include_light_pollution=(kml_file_path is not None),
        include_road_connectivity=True
    )
    
    # Print summary
    analyzer.print_analysis_summary(locations)
    
    return locations


if __name__ == "__main__":
    # Example: Analyze stargazing locations around Beijing
    print("=== Stargazing Location Comprehensive Analyzer Example ===")
    
    # Define analysis area (around Beijing)
    bbox = (39.5, 115.5, 40.5, 117.5)  # (south, west, north, east)
    
    # Create analyzer (no KML file provided here, so skip light pollution analysis)
    analyzer = StargazingLocationAnalyzer(
        kml_file_path=None,  # If you have light pollution KML file, provide path here
        min_height_difference=100.0,
        road_search_radius_km=10.0
    )
    
    # Analyze area
    locations = analyzer.analyze_area(
        bbox=bbox,
        max_locations=20,
        location_types=['mountain_peak', 'observatory', 'viewpoint'],
        network_type='drive',
        include_light_pollution=False,  # Set to False when no KML file
        include_road_connectivity=True
    )
    
    # Save results
    if locations:
        analyzer.save_results_to_json(locations, "stargazing_analysis_results.json")
        
        # Print summary
        analyzer.print_analysis_summary(locations)
    else:
        print("No qualified stargazing locations found")
