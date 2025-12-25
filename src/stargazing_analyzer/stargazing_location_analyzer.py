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
from dataclasses import dataclass, asdict
import time
from datetime import datetime

# Import related modules
try:
    from .stargazing_place_finder import StarGazingPlaceFinder, Peak, PostGISClient
    from light_pollution.light_pollution_analyzer import LightPollutionAnalyzer
    from road_connectivity.road_connectivity_checker import RoadConnectivityChecker
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'src'))
    from stargazing_analyzer.stargazing_place_finder import StarGazingPlaceFinder, Peak, PostGISClient
    from light_pollution.light_pollution_analyzer import LightPollutionAnalyzer
    from road_connectivity.road_connectivity_checker import RoadConnectivityChecker


@dataclass
class StargazingLocation:
    """
    Stargazing location data class
    Supports multiple types of stargazing locations such as peaks, observatories, viewpoints
    Contains basic location information, light pollution data, and road connectivity information
    """
    # Basic location information (adapted to unified Location class)
    name: str
    latitude: float
    longitude: float
    elevation: float
    distance_to_nearest_town: float
    nearest_town_name: str
    
    # Location type and description
    location_type: str = "mountain_peak"  # "mountain_peak", "observatory", "viewpoint"
    description: Optional[str] = None
    
    # Peak-specific information
    prominence: Optional[float] = None
    height_difference: Optional[float] = None
    
    # Light pollution information
    light_pollution_rgb: Optional[Tuple[int, int, int]] = None
    light_pollution_hex: Optional[str] = None
    light_pollution_brightness: Optional[int] = None
    light_pollution_level: Optional[str] = None
    light_pollution_overlay: Optional[str] = None
    
    # Road connectivity information
    road_accessible: Optional[bool] = None
    distance_to_road_km: Optional[float] = None
    road_network_type: Optional[str] = None
    road_check_error: Optional[str] = None
    
    # Comprehensive scoring
    stargazing_score: Optional[float] = None
    recommendation_level: Optional[str] = None
    analysis_notes: Optional[str] = None
    
    def is_mountain_peak(self) -> bool:
        """Check if it's a mountain peak"""
        return self.location_type == "mountain_peak"
    
    def is_observatory(self) -> bool:
        """Check if it's an observatory"""
        return self.location_type == "observatory"
    
    def is_viewpoint(self) -> bool:
        """Check if it's a viewpoint"""
        return self.location_type == "viewpoint"


class StargazingLocationAnalyzer:
    """
    Stargazing Location Comprehensive Analyzer
    
    Integrates peak finding, light pollution analysis, and road connectivity detection,
    providing comprehensive stargazing suitability analysis for peaks within specified coordinate ranges.
    """
    
    def __init__(self, 
                 kml_file_path: Optional[str] = None,
                 images_base_path: Optional[str] = None,
                 min_height_difference: float = 100.0,
                 road_search_radius_km: float = 10.0,
                 db_config_path: Optional[str] = None):
        """
        Initialize stargazing location analyzer
        
        Args:
            kml_file_path: Light pollution KML file path, skip light pollution analysis if None (strongly recommended to provide)
            images_base_path: Light pollution image file base path
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
        
        # Initialize light pollution analyzer (if KML file is provided)
        self.light_pollution_analyzer = None
        if kml_file_path and os.path.exists(kml_file_path):
            try:
                self.light_pollution_analyzer = LightPollutionAnalyzer(
                    kml_file_path=kml_file_path,
                    images_base_path=images_base_path
                )
                print("Light pollution analyzer initialized successfully")
            except Exception as e:
                print(f"Light pollution analyzer initialization failed: {e}")
                self.light_pollution_analyzer = None
            self.mountain_finder = StarGazingPlaceFinder(min_height_difference=min_height_difference, light_pollution_analyzer=self.light_pollution_analyzer, db_client=db_client)
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
                prominence=location.prominence if hasattr(location, 'prominence') and location.prominence else 0.0,
                distance_to_nearest_town=location.distance_to_nearest_town,
                nearest_town_name=location.nearest_town_name,
                height_difference=location.height_difference if hasattr(location, 'height_difference') and location.height_difference else 0.0,
                location_type=location.location_type,
                description=location.description if hasattr(location, 'description') else None
            )
            
            # 3. Light pollution analysis
            if include_light_pollution:
                if self.light_pollution_analyzer:
                    try:
                        light_info = self.light_pollution_analyzer.get_light_pollution_color(
                            location.latitude, location.longitude
                        )
                        if light_info:
                            stargazing_location.light_pollution_rgb = light_info['rgb']
                            stargazing_location.light_pollution_hex = light_info['hex']
                            stargazing_location.light_pollution_brightness = light_info['brightness']
                            stargazing_location.light_pollution_level = light_info['pollution_level']
                            stargazing_location.light_pollution_overlay = light_info.get('overlay_name')
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
    
    def _calculate_stargazing_score(self, location: StargazingLocation) -> float:
        """
        Calculate comprehensive score for stargazing location (adapted for multiple location types)
        
        Scoring criteria:
        - Elevation (0-30 points): Higher elevation is better
        - Location type specific score (0-25 points): Calculated based on different types
        - Light pollution level (0-25 points): Less light pollution is better
        - Road accessibility (0-20 points): Accessible with moderate distance is best
        
        Args:
            location: Stargazing location object
            
        Returns:
            Comprehensive score (0-100 points)
        """
        score = 0.0
        
        # 1. Elevation score (0-30 points)
        if location.elevation:
            # 1 point per 100 meters elevation, maximum 30 points
            elevation_score = min(location.elevation / 100 * 1, 30)
            score += elevation_score
        
        # 2. Location type specific score (0-25 points)
        if location.is_mountain_peak():
            # Mountain peak: prominence score
            if location.prominence:
                # 1 point per 50 meters prominence, maximum 25 points
                prominence_score = min(location.prominence / 50 * 1, 25)
                score += prominence_score
        elif location.is_observatory():
            # Observatory: fixed high score (professional observation facility)
            score += 25
        elif location.is_viewpoint():
            # Viewpoint: score based on height difference
            if location.height_difference:
                # 1 point per 40 meters height difference, maximum 25 points
                height_diff_score = min(location.height_difference / 40 * 1, 25)
                score += height_diff_score
            else:
                score += 15  # Default medium score
        
        # 3. Light pollution score (0-25 points)
        if location.light_pollution_level:
            pollution_scores = {
                'Extremely Low': 25, 'Very Low': 20, 'Low': 15, 'Medium': 10, 
                'High': 5, 'Very High': 2, 'Extremely High': 0
            }
            score += pollution_scores.get(location.light_pollution_level, 0)
        elif location.light_pollution_brightness is not None:
            # If no level but brightness data available, calculate based on brightness
            light_score = max(0, (255 - location.light_pollution_brightness) / 255.0 * 25)
            score += light_score
        else:
            # If no light pollution data, give warning and use default score
            print(f"⚠️  Warning: {location.name} lacks light pollution data, scoring accuracy affected")
            score += 12  # Half of 25 points weight
        
        # 4. Road accessibility score (0-20 points)
        if location.road_accessible is not None:
            if location.road_accessible:
                # When accessible, closer to road is better (but not too close)
                if location.distance_to_road_km is not None:
                    if 0.5 <= location.distance_to_road_km <= 5:
                        # Ideal distance: 0.5-5 km
                        score += 20
                    elif location.distance_to_road_km <= 10:
                        # Acceptable distance: 5-10 km
                        score += 15
                    elif location.distance_to_road_km <= 20:
                        # Far distance: 10-20 km
                        score += 10
                    else:
                        # Very far distance: >20 km
                        score += 5
                else:
                    score += 10  # Accessible but distance unknown
            else:
                score += 0  # Not accessible
        else:
            score += 10  # Unknown status given medium score
        
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
            "locations": [asdict(location) for location in locations]
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
