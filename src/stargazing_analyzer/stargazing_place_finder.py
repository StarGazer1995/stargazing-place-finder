#!/usr/bin/env python3
"""
Peak Finder Module
Used to find peaks with sufficient height difference from surrounding towns within specified geographic coordinate ranges
"""

import requests
import json
from typing import List, Dict, Tuple, Optional
import math
from dataclasses import dataclass
import time
import random
import hashlib
import pickle
from pathlib import Path
import importlib.resources as res
try:
    from light_pollution.light_pollution_analyzer import LightPollutionAnalyzer
    from cache.cache_config import get_cache_dir
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'src'))
    from light_pollution.light_pollution_analyzer import LightPollutionAnalyzer
    from cache.cache_config import get_cache_dir
import math

class PostGISClient:
    """
    Lightweight PostGIS client providing location and elevation queries.
    Encapsulates all database interactions to keep the finder class decoupled.
    """

    def __init__(self, config: dict):
        """
        Initialize the PostGIS client with a connection config dict.

        Args:
            config: Connection parameters for psycopg2 (host, port, dbname, user, password)
        """
        self.config = config or {}

    def query_locations_in_bbox(self, lon_min, lat_min, lon_max, lat_max, location_type=None, filters=None):
        """
        Query locations within bbox and return Overpass-compatible dicts.

        Args:
            lon_min, lat_min, lon_max, lat_max: Bounding box in WGS84
            location_type: Optional type filter ('town', 'observatory', 'viewpoint', 'peak')
            filters: Optional extra SQL conditions

        Returns:
            List[dict]: Elements formatted similar to Overpass API results
        """
        import psycopg2

        conn = psycopg2.connect(**self.config)
        cursor = conn.cursor()

        base_query = """
            SELECT 
                osm_id,
                name,
                ST_X(ST_Transform(way, 4326)) as longitude,
                ST_Y(ST_Transform(way, 4326)) as latitude,
                amenity,
                tourism,
                shop,
                highway,
                place,
                man_made,
                "tower:type" as tower_type,
                leisure,
                "natural"
            FROM planet_osm_point
            WHERE ST_Transform(way, 4326) && ST_MakeEnvelope(%s, %s, %s, %s, 4326)
        """

        type_conditions = []
        if location_type == 'town':
            type_conditions.append("place IN ('city', 'town', 'village', 'hamlet')")
            type_conditions.append("name IS NOT NULL")
        elif location_type == 'observatory':
            type_conditions.append("(amenity = 'observatory' OR man_made = 'telescope' OR (man_made = 'tower' AND \"tower:type\" = 'astronomical') OR amenity = 'planetarium')")
        elif location_type == 'viewpoint':
            type_conditions.append("(tourism = 'viewpoint' OR (man_made = 'tower' AND \"tower:type\" = 'observation') OR amenity = 'observation_deck' OR leisure = 'viewing_platform')")
        elif location_type == 'peak':
            type_conditions.append("(\"natural\" IN ('peak','volcano'))")

        conditions = []
        if type_conditions:
            conditions.extend(type_conditions)
        if filters:
            conditions.append(filters)

        if conditions:
            query = base_query + " AND " + " AND ".join(conditions)
        else:
            query = base_query

        cursor.execute(query, (lon_min, lat_min, lon_max, lat_max))
        results = cursor.fetchall()

        formatted_results = []
        for row in results:
            result = {
                'type': 'node',
                'id': row[0],
                'lat': row[3],
                'lon': row[2],
                'tags': {}
            }
            if row[1]:
                result['tags']['name'] = row[1]
            if row[4]:
                result['tags']['amenity'] = row[4]
            if row[5]:
                result['tags']['tourism'] = row[5]
            if row[6]:
                result['tags']['shop'] = row[6]
            if row[7]:
                result['tags']['highway'] = row[7]
            if row[8]:
                result['tags']['place'] = row[8]
            if row[9]:
                result['tags']['man_made'] = row[9]
            if row[10]:
                result['tags']['tower:type'] = row[10]
            if row[11]:
                result['tags']['leisure'] = row[11]
            if row[12]:
                result['tags']['natural'] = row[12]
            formatted_results.append(result)

        cursor.close()
        conn.close()
        return formatted_results

    def find_elevation_at_point(self, lat: float, lon: float) -> Optional[float]:
        """
        Find elevation near a point using nearest ele-tagged OSM node.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Elevation in meters or None
        """
        import psycopg2

        try:
            conn = psycopg2.connect(**self.config)
            cursor = conn.cursor()
            query = """
                SELECT 
                    ele::float as elevation_meters
                FROM planet_osm_point
                WHERE ele IS NOT NULL 
                    AND ele ~ '^[0-9]+(\\.[0-9]+)?$'
                    AND ele::float >= -500 
                    AND ele::float <= 9000
                ORDER BY ST_Transform(way, 4326) <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                LIMIT 1;
            """
            cursor.execute(query, (lon, lat))
            result = cursor.fetchone()
            if result:
                return result[0]
            return None
        except Exception:
            return None
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass


@dataclass
class Location:
    """Unified location data class supporting multiple types like mountain peaks, observatories, viewpoints, etc."""
    # Basic required fields
    name: str  # Location name
    latitude: float  # Latitude
    longitude: float  # Longitude
    elevation: float  # Elevation (meters)
    distance_to_nearest_town: float  # Distance to nearest town (kilometers)
    nearest_town_name: str  # Nearest town name
    location_type: str  # Location type: "mountain_peak", "observatory", "viewpoint"
    
    # Optional fields, used according to different types
    description: Optional[str] = None  # Description information
    prominence: Optional[float] = None  # Relative height (meters) - mainly for peaks
    height_difference: Optional[float] = None  # Height difference from nearest town (meters) - mainly for peaks
    observatory_type: Optional[str] = None  # Observatory type - only for observatories
    viewpoint_type: Optional[str] = None  # Viewpoint type - only for viewpoints
    light_pollution_level: Optional[str] = None  # Light pollution level
    scenic_value: Optional[str] = None  # Scenic value level - mainly for viewpoints
    
    def is_mountain_peak(self) -> bool:
        """Check if it's a mountain peak"""
        return self.location_type == "mountain_peak"
    
    def is_observatory(self) -> bool:
        """Check if it's an observatory"""
        return self.location_type == "observatory"
    
    def is_viewpoint(self) -> bool:
        """Check if it's a viewpoint"""
        return self.location_type == "viewpoint"

# For backward compatibility, keep original class names as aliases
Peak = Location
Observatory = Location
Viewpoint = Location

class LocationCache:
    """
    Location search result cache management class
    Used to cache results from _find_locations_in_area method to reduce redundant calculations
    """
    
    def __init__(self, cache_expiry_hours: int = 24):
        """
        Initialize cache manager
        
        Args:
            cache_expiry_hours: Cache expiry time (hours)
        """
        self.cache_dir = Path(get_cache_dir('default')) / 'location_results'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.expiry_hours = cache_expiry_hours * 3600
        self.cache_mem_data = {}
    
    def _generate_cache_key(self, location_type: str) -> str:
        """
        Generate cache key
        
        Args:
            location_type: Location type
            
        Returns:
            Cache key string
        """
        # Only use location type to generate cache key
        return hashlib.md5(location_type.encode('utf-8')).hexdigest()
    
    def _get_cache_file_path(self, cache_key: str) -> Path:
        """
        Get cache file path
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cache file path
        """
        return self.cache_dir / f"{cache_key}.pkl"
    
    def _is_cache_valid(self, cache_file: Path) -> bool:
        """
        Check if cache is valid (not expired)
        
        Args:
            cache_file: Cache file path
            
        Returns:
            Whether cache is valid
        """
        if not cache_file.exists():
            return False
        
        # Check file modification time
        file_mtime = cache_file.stat().st_mtime
        current_time = time.time()
        
        return (current_time - file_mtime) < self.expiry_hours
    
    def get_cached_result(self, location_type: str) -> Optional[List[Location]]:
        """
        Get query results from cache
        
        Args:
            location_type: Location type
            
        Returns:
            Cached query results, returns None if no valid cache exists
        """
        if location_type in self.cache_mem_data:
            return self.cache_mem_data[location_type]
        
        cache_key = self._generate_cache_key(location_type)
        cache_file = self._get_cache_file_path(cache_key)
        
        if self._is_cache_valid(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                    print(f"✅ Loaded data from cache: {len(cached_data)} records")
                    return cached_data
            except Exception as e:
                print(f"⚠️ Failed to read cache file: {e}")
                # Delete corrupted cache file
                try:
                    cache_file.unlink()
                except:
                    pass
        
        return None
    
    def save_to_cache(self, location_type: str, data: List[Location]):
        """
        Save query results to cache
        
        Args:
            location_type: Location type
            data: Query result data
        """
        
        cache_key = self._generate_cache_key(location_type)
        cache_file = self._get_cache_file_path(cache_key)
        cached_data = self.get_cached_result(location_type)
        if cached_data is None:
            cached_data = data
        else:
            for item in data:
                if item not in cached_data:
                    cached_data.append(item)
        self.cache_mem_data[location_type] = cached_data
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(cached_data, f)
            print(f"💾 Query results cached: {len(data)} records")
        except Exception as e:
            print(f"⚠️ Failed to save cache: {e}")
    
    def check_data_in_cache(self, location_type: str, data: List[Location]) -> bool:
        """
        Check if data is already in cache
        
        Args:
            location_type: Location type
            data: Data to check
            
        Returns:
            Whether already in cache
        """
        cached_data = self.get_cached_result(location_type)
        if cached_data is None:
            return False
        
        # Check if data is in cache
        for item in data:
            if item in cached_data:
                return True
        return False
    
    def clear_cache(self):
        """
        Clear all cache files
        """
        try:
            import shutil
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(exist_ok=True)
                print("🧹 Overpass query cache cleared")
        except Exception as e:
            print(f"⚠️ Failed to clear cache: {e}")
    
    def get_location_by_coordinates(self, cache_data: List[Location], latitude: float, longitude: float, tolerance: float = 0.001) -> Optional[Location]:
        """
        Find specific location from cache by location type and coordinates
        
        Args:
            cache_data: Cache data
            latitude: Latitude
            longitude: Longitude
            tolerance: Coordinate matching tolerance, default 0.001 degrees (about 100 meters)
            
        Returns:
            Matched location object, returns None if not found
        """
        if cache_data is None:
            return None
        for location in cache_data:
            if abs(location.latitude - latitude) <= tolerance and abs(location.longitude - longitude) <= tolerance:
                return location
        return None

    
    def get_locations_in_radius(self, location_type: str, center_latitude: float, center_longitude: float, radius_km: float) -> List[Location]:
        """
        Find all locations within specified radius from cache by location type and center coordinates
        
        Args:
            location_type: Location type ("mountain_peak", "observatory", "viewpoint")
            center_latitude: Center latitude
            center_longitude: Center longitude
            radius_km: Search radius (kilometers)
            
        Returns:
            List of locations within radius
        """
        # First get all locations of this type from cache
        cached_locations = self.get_cached_result(location_type)
        
        if not cached_locations:
            print(f"⚠️ No location data of type '{location_type}' found in cache")
            return []
        
        # Calculate distance and filter locations within radius
        locations_in_radius = []
        
        for location in cached_locations:
            # Use simplified distance calculation formula (suitable for small ranges)
            lat_diff = location.latitude - center_latitude
            lon_diff = location.longitude - center_longitude
            
            # Convert latitude/longitude difference to approximate kilometers (1 degree ≈ 111 km)
            distance_km = math.sqrt((lat_diff * 111) ** 2 + (lon_diff * 111 * math.cos(math.radians(center_latitude))) ** 2)
            
            if distance_km <= radius_km:
                locations_in_radius.append(location)
        
        print(f"✅ Found {len(locations_in_radius)} '{location_type}' type locations within {radius_km}km radius in cache")
        return sorted(locations_in_radius, key=lambda loc: 
                     math.sqrt((loc.latitude - center_latitude) ** 2 + (loc.longitude - center_longitude) ** 2))
    
    def get_cache_info(self) -> Dict:
        """
        Get cache information
        
        Returns:
            Cache information dictionary
        """
        cache_files = list(self.cache_dir.glob('*.pkl'))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        def format_size(size_bytes: int) -> str:
            """Format file size"""
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.1f} {unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.1f} TB"
        
        return {
            'cache_dir': str(self.cache_dir),
            'file_count': len(cache_files),
            'total_size': format_size(total_size),
            'expiry_hours': self.expiry_hours / 3600
        }

class OverpassCache:
    """
    Overpass API query result cache management class
    Used to cache Overpass API query results to reduce redundant network requests
    """
    
    def __init__(self, cache_dir: str = None, expiry_hours: int = 24):
        """
        Initialize Overpass cache manager
        
        Args:
            cache_dir: Cache directory path, uses default if None
            expiry_hours: Cache expiry time (hours)
        """
        if cache_dir is None:
            self.cache_dir = Path(get_cache_dir('default')) / 'overpass_queries'
        else:
            self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.expiry_hours = expiry_hours * 3600
    
    def _generate_cache_key(self, query: str, data_type: str, bbox: Tuple[float, float, float, float]) -> str:
        """
        Generate cache key for Overpass query
        
        Args:
            query: Overpass query string
            data_type: Data type identifier
            bbox: Bounding box (south, west, north, east)
            
        Returns:
            Cache key string
        """
        # Combine query, data type and bbox to generate unique key
        key_string = f"{query}_{data_type}_{bbox[0]}_{bbox[1]}_{bbox[2]}_{bbox[3]}"
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()
    
    def _get_cache_file_path(self, cache_key: str) -> Path:
        """
        Get cache file path
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cache file path
        """
        return self.cache_dir / f"{cache_key}.pkl"
    
    def _is_cache_valid(self, cache_file: Path) -> bool:
        """
        Check if cache is valid (not expired)
        
        Args:
            cache_file: Cache file path
            
        Returns:
            Whether cache is valid
        """
        if not cache_file.exists():
            return False
        
        # Check file modification time
        file_mtime = cache_file.stat().st_mtime
        current_time = time.time()
        
        return (current_time - file_mtime) < self.expiry_hours
    
    def get_from_cache(self, query: str, data_type: str, bbox: Tuple[float, float, float, float]) -> Optional[List[Dict]]:
        """
        Get query results from cache
        
        Args:
            query: Overpass query string
            data_type: Data type identifier
            bbox: Bounding box
            
        Returns:
            Cached query results, returns None if no valid cache exists
        """
        cache_key = self._generate_cache_key(query, data_type, bbox)
        cache_file = self._get_cache_file_path(cache_key)
        
        if self._is_cache_valid(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                    return cached_data
            except Exception as e:
                # Delete corrupted cache file
                try:
                    cache_file.unlink()
                except:
                    pass
        
        return None
    
    def save_to_cache(self, query: str, data_type: str, bbox: Tuple[float, float, float, float], data: List[Dict]):
        """
        Save query results to cache
        
        Args:
            query: Overpass query string
            data_type: Data type identifier
            bbox: Bounding box
            data: Query result data
        """
        cache_key = self._generate_cache_key(query, data_type, bbox)
        cache_file = self._get_cache_file_path(cache_key)
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            pass
    
    def clear_cache(self):
        """
        Clear all cache files
        """
        try:
            import shutil
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(exist_ok=True)
        except Exception as e:
            pass
    
    def get_cache_info(self) -> Dict:
        """
        Get cache information
        
        Returns:
            Cache information dictionary
        """
        cache_files = list(self.cache_dir.glob('*.pkl'))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        def format_size(size_bytes: int) -> str:
            """Format file size"""
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.1f} {unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.1f} TB"
        
        return {
            'cache_dir': str(self.cache_dir),
            'file_count': len(cache_files),
            'total_size': format_size(total_size),
            'expiry_hours': self.expiry_hours / 3600
        }

class StarGazingPlaceFinder:
    """
    Stargazing place finder class
    Used to find suitable stargazing locations within specified ranges
    """
    
    def __init__(self, min_height_difference: float = 100.0, light_pollution_analyzer: Optional[LightPollutionAnalyzer] = None, enable_cache: bool = True, cache_expiry_hours: int = 24*365, db_client: Optional[PostGISClient] = None):
        """
        Initialize stargazing place finder
        
        Args:
            min_height_difference: Minimum height difference from surrounding towns (meters), default 100m
            light_pollution_analyzer: Light pollution analyzer instance
            enable_cache: Whether to enable cache, default True
            cache_expiry_hours: Cache expiry time (hours), default 24 hours
        """
        self.min_height_difference = min_height_difference
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self.light_pollution_analyzer = light_pollution_analyzer
        self.enable_cache = enable_cache
        self.cache = LocationCache(cache_expiry_hours) if enable_cache else None
        self.db_client = db_client
        self.postgis_enabled = self.db_client is not None
        
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two geographic coordinates (kilometers)
        Using Haversine formula
        
        Args:
            lat1, lon1: Latitude and longitude of first point
            lat2, lon2: Latitude and longitude of second point
            
        Returns:
            Distance (kilometers)
        """
        R = 6371  # Earth radius (kilometers)
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat/2) * math.sin(delta_lat/2) + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon/2) * math.sin(delta_lon/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def get_peaks_from_overpass(self, bbox: Tuple[float, float, float, float]) -> List[Dict]:
        """
        Get peak data from Overpass API within specified bounding box
        
        Args:
            bbox: Bounding box (south, west, north, east)
            
        Returns:
            List of peak data
        """
        
        south, west, north, east = bbox
        if self.postgis_enabled:
            print(f"Query peaks in PostGIS: {west}, {south}, {east}, {north}")
            return self.db_client.query_locations_in_bbox(west, south, east, north, "peak")
        
        # Overpass QL query statement
        query = f"""
        [out:json][timeout:25];
        (
          node["natural"="peak"]({south},{west},{north},{east});
          node["natural"="volcano"]({south},{west},{north},{east});
        );
        out geom;
        """
        
        return self._make_overpass_request(query, "peaks")
    
    def get_towns_from_overpass(self, bbox: Tuple[float, float, float, float]) -> List[Dict]:
        """
        Get town data from Overpass API within specified bounding box
        
        Args:
            bbox: Bounding box (south, west, north, east)
            
        Returns:
            List of town data
        """
        south, west, north, east = bbox
        if self.postgis_enabled:
            print(f"Query towns in PostGIS: {west}, {south}, {east}, {north}")
            return self.db_client.query_locations_in_bbox(west, south, east, north, "town")
        
        # Overpass QL query statement - get towns, villages and other settlements
        query = f"""
        [out:json][timeout:25];
        (
          node["place"~"^(city|town|village|hamlet)$"]({south},{west},{north},{east});
          way["place"~"^(city|town|village|hamlet)$"]({south},{west},{north},{east});
          relation["place"~"^(city|town|village|hamlet)$"]({south},{west},{north},{east});
        );
        out center geom;
        """
        
        return self._make_overpass_request(query, "towns")
    
    def get_observatories_from_overpass(self, bbox: Tuple[float, float, float, float]) -> List[Dict]:
        """
        Get observatory data from Overpass API within specified bounding box
        
        Args:
            bbox: Bounding box (south, west, north, east)
            
        Returns:
            List of observatory data
        """
        south, west, north, east = bbox
        if self.postgis_enabled:
            print(f"Query observatories in PostGIS: {west}, {south}, {east}, {north}")
            return self.db_client.query_locations_in_bbox(west, south, east, north, "observatory")
        
        # Overpass QL query statement - get observatories, observation stations, etc.
        query = f"""
        [out:json][timeout:25];
        (
          node["man_made"="observatory"]({south},{west},{north},{east});
          way["man_made"="observatory"]({south},{west},{north},{east});
          relation["man_made"="observatory"]({south},{west},{north},{east});
          node["amenity"="planetarium"]({south},{west},{north},{east});
          way["amenity"="planetarium"]({south},{west},{north},{east});
          node["building"="observatory"]({south},{west},{north},{east});
          way["building"="observatory"]({south},{west},{north},{east});
        );
        out center geom;
        """
        
        return self._make_overpass_request(query, "observatories")
    
    def get_viewpoints_from_overpass(self, bbox: Tuple[float, float, float, float]) -> List[Dict]:
        """
        Get viewpoint data from Overpass API within specified bounding box
        
        Args:
            bbox: Bounding box (south, west, north, east)
            
        Returns:
            List of viewpoint data
        """
        south, west, north, east = bbox
        
        # Overpass QL query statement - get viewpoints, scenic spots, etc.
        query = f"""
        [out:json][timeout:25];
        (
          node["tourism"="viewpoint"]({south},{west},{north},{east});
          way["tourism"="viewpoint"]({south},{west},{north},{east});
          relation["tourism"="viewpoint"]({south},{west},{north},{east});
          node["man_made"="tower"]["tower:type"="observation"]({south},{west},{north},{east});
          way["man_made"="tower"]["tower:type"="observation"]({south},{west},{north},{east});
          node["amenity"="observation_deck"]({south},{west},{north},{east});
          way["amenity"="observation_deck"]({south},{west},{north},{east});
          node["leisure"="viewing_platform"]({south},{west},{north},{east});
          way["leisure"="viewing_platform"]({south},{west},{north},{east});
        );
        out center geom;
        """
        
        return self._make_overpass_request(query, "viewpoints")

    def _query_locations_in_bbox(self, lon_min, lat_min, lon_max, lat_max, location_type=None, filters=None):
        """
        Backward-compatible wrapper to query locations via injected PostGIS client.
        """
        if not self.db_client:
            return []
        return self.db_client.query_locations_in_bbox(lon_min, lat_min, lon_max, lat_max, location_type, filters)


    def _make_postgis_request(self, lon_min, lat_min, lon_max, lat_max, location_type: str = "data") -> List[Dict]:
        """
        Send request to PostGIS database with retry mechanism and error handling
        
        Args:
            lon_min: Minimum longitude of bounding box
            lat_min: Minimum latitude of bounding box
            lon_max: Maximum longitude of bounding box
            lat_max: Maximum latitude of bounding box
            location_type: Type of location data to query (town, observatory, viewpoint)
            
        Returns:
            List of elements returned by database
        """
        if location_type in ['town', 'observatory', 'viewpoint', 'peak']:
            return self._query_locations_in_bbox(lon_min, lat_min, lon_max, lat_max, location_type)
        else:
            raise ValueError(f"Unsupported location type: {location_type}")

    
    def _make_overpass_request(self, query: str, data_type: str = "data", max_retries: int = 3, debug: bool = False) -> List[Dict]:
        """
        Send request to Overpass API with retry mechanism and error handling
        
        Args:
            query: Overpass query statement
            data_type: Data type description (for error messages)
            max_retries: Maximum retry attempts
            debug: Whether to show debug information
            
        Returns:
            List of elements returned by API
        """
        if debug:
            print(f"Query statement:\n{query}")
            print("-" * 50)
        
        for attempt in range(max_retries):
            try:
                # Add random delay to avoid API limits
                if attempt > 0:
                    delay = random.uniform(1, 3) * (attempt + 1)
                    print(f"Retry attempt {attempt + 1}, waiting {delay:.1f} seconds...")
                    time.sleep(delay)
                
                print(f"Getting {data_type} data...")
                response = requests.post(self.overpass_url, data=query, timeout=45)
                
                if debug:
                    print(f"Response status code: {response.status_code}")
                    if response.status_code != 200:
                        print(f"Response content: {response.text[:500]}")
                
                response.raise_for_status()
                data = response.json()
                elements = data.get('elements', [])
                print(f"Found {len(elements)} {data_type}")
                return elements
                
            except requests.exceptions.Timeout:
                print(f"Getting {data_type} data timeout (attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    print(f"⚠️ Still timeout after {max_retries} attempts, may be network issue or Overpass API server busy")
                    print("Suggest retry later or check network connection")
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 504:
                    print(f"Overpass API gateway timeout (attempt {attempt + 1}/{max_retries})")
                    if attempt == max_retries - 1:
                        print("⚠️ Overpass API server currently busy, please retry later")
                elif e.response.status_code == 429:
                    print(f"API request rate limit (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(60)  # Wait longer
                elif e.response.status_code == 400:
                    print(f"Query statement error (400 Bad Request)")
                    if debug:
                        print(f"Error response: {e.response.text[:500]}")
                    print("⚠️ Please check query statement format")
                    break  # 400 errors usually don't need retry
                else:
                    print(f"HTTP error: {e}")
                    if debug and hasattr(e, 'response'):
                        print(f"Error response: {e.response.text[:500]}")
                    break
            except requests.exceptions.RequestException as e:
                print(f"Network request error: {e} (attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    print("⚠️ Network connection issue, please check network settings")
            except json.JSONDecodeError:
                print(f"API returned data format error (attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    print("⚠️ API returned data format is incorrect")
            except Exception as e:
                print(f"Error getting {data_type} data: {e} (attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    print("⚠️ Unknown error occurred, please check query parameters or retry later")
        
        return []
    
    def get_elevation_from_api(self, lat: float, lon: float) -> Optional[float]:
        """
        Get elevation from elevation API for specified coordinates
        Using Open-Elevation API
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Elevation (meters), returns None if failed to get
        """
        try:
            url = f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('results'):
                return data['results'][0].get('elevation')
        except Exception as e:
            print(f"Error getting elevation data ({lat}, {lon}): {e}")
        
        return None
    
    def find_nearest_town(self, peak_lat: float, peak_lon: float, towns: List[Dict]) -> Tuple[Optional[str], float, Optional[float]]:
        """
        Find the nearest town to the peak
        
        Args:
            peak_lat: Peak latitude
            peak_lon: Peak longitude
            towns: List of town data
            
        Returns:
            (Nearest town name, distance(km), town elevation)
        """
        min_distance = float('inf')
        nearest_town = None
        nearest_town_elevation = None
        
        for town in towns:
            # Get town coordinates
            try:
                if town['type'] == 'node':
                    town_lat = town['lat']
                    town_lon = town['lon']
                elif 'center' in town:
                    town_lat = town['center']['lat']
                    town_lon = town['center']['lon']
                else:
                    continue
            except KeyError:
                # Skip town data missing coordinate information
                continue
            
            # Calculate distance
            distance = self.calculate_distance(peak_lat, peak_lon, town_lat, town_lon)
            
            if distance < min_distance:
                min_distance = distance
                nearest_town = town.get('tags', {}).get('name', 'Unknown town')
                # Get town elevation
                nearest_town_elevation = self.get_elevation_from_api(town_lat, town_lon)
                time.sleep(0.1)  # Avoid API requests too frequently
        
        return nearest_town, min_distance, nearest_town_elevation

    def _sort_places_by_lightpollution(self, places: List[Dict]) -> List[Dict]: 
        """
        Sort places by light pollution level
        
        Args:
            places: List of places, each place contains lat and lon fields
            
        Returns:
            List of places sorted by light pollution level (lower pollution first, suitable for stargazing)
        """
        # If no light pollution analyzer or empty list, return original list directly
        if not self.light_pollution_analyzer or not places:
            return places
             
        # Safely get coordinate information
        places_coord = []
        valid_places = []
        for place in places:
            try:
                if place['type'] == 'node':
                    lat = place['lat']
                    lon = place['lon']
                elif 'center' in place:
                    lat = place['center']['lat']
                    lon = place['center']['lon']
                else:
                    continue  # Skip places where coordinates cannot be obtained
                places_coord.append([lat, lon])
                valid_places.append(place)
            except KeyError:
                # Skip places missing coordinate information
                continue
        
        # If no valid places, return empty list
        if not places_coord:
            return []
        places_light_pollutions = self.light_pollution_analyzer.batch_analyze_coordinates(places_coord)
        # Sort by light pollution level, lower pollution is better for stargazing, so reverse=False
        places_light_pollutions = sorted(places_light_pollutions, key=lambda x: x['pollution_info']["brightness"], reverse=False)
        # Rearrange places list according to sorted indices
        sorted_places = [valid_places[place_light_pollution['index']] for place_light_pollution in places_light_pollutions]
        # Add light pollution information
        for place, light_pollution in zip(sorted_places, places_light_pollutions):
            place['light_pollution'] = light_pollution['pollution_info']
        print(f"Sorted places: {sorted_places[:3]}")
        return sorted_places
    
    def clear_cache(self):
        """
        Clear Overpass query cache
        """
        if self.cache:
            self.cache.clear_cache()
        else:
            print("⚠️ Cache function not enabled")
    
    def get_cache_info(self) -> Optional[Dict]:
        """
        Get cache information
        
        Returns:
            Cache information dictionary, returns None if cache not enabled
        """
        if self.cache:
            return self.cache.get_cache_info()
        else:
            print("⚠️ Cache function not enabled")
            return None
    
    def _extract_coordinates(self, data: Dict) -> Tuple[Optional[float], Optional[float]]:
        """
        Extract coordinates from location data
        
        Args:
            data: Location data dictionary
            
        Returns:
            (latitude, longitude) or (None, None) if extraction fails
        """
        try:
            if data['type'] == 'node':
                return data['lat'], data['lon']
            elif 'center' in data:
                return data['center']['lat'], data['center']['lon']
            else:
                return None, None
        except KeyError:
            return None, None
    
    def _find_elevation_at_point_postgis(self, lat: float, lon: float) -> Optional[float]:
        """
        Find elevation at a specific point
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Elevation in meters or None if not found
        """
        if not self.postgis_enabled:
            print("PostGIS not enabled, cannot query elevation data")
            return None

        elevation = self.db_client.find_elevation_at_point(lat, lon) if self.db_client else None
        if elevation is None:
            print(f"在坐标 ({lat}, {lon}) 附近未找到海拔数据")
        return elevation
    
    def _find_locations_in_area(self, 
                               bbox: Tuple[float, float, float, float],
                               location_type: str,
                               max_locations: int,
                               data_getter_func,
                               location_processor_func) -> List[Location]:
        """
        Generic location finding function to reduce code duplication
        
        Args:
            bbox: Bounding box (south, west, north, east)
            location_type: Location type ('mountain_peak', 'observatory', 'viewpoint')
            max_locations: Maximum number of locations to return
            data_getter_func: Function to get specific type data
            location_processor_func: Function to process specific type locations
            
        Returns:
            List of locations
        """
        print(f"Searching {location_type} area: {bbox}")
        
        # Get specific type data
        print(f"Getting {location_type} data...")
        locations_data = data_getter_func(bbox)
        locations_data = self._sort_places_by_lightpollution(locations_data)
        print(f"Found {len(locations_data)} {location_type}")

        res = []
        if self.cache is not None:
            cached_data = self.cache.get_cached_result(location_type)
            for location in locations_data:
                lat, lon = self._extract_coordinates(location)
                if (lat is not None) and (lon is not None) and (cached_data is not None):
                    cache = self.cache.get_location_by_coordinates(cache_data=cached_data, latitude=lat, longitude=lon)
                    if cache is not None:
                        res.append(cache)

        print(f"Retrieved {len(res)} {location_type} data from cache")
        if len(res) >= max_locations:
            return res[:max_locations]
        
        # Get town data
        print("Getting town data...")
        towns_data = self.get_towns_from_overpass(bbox)
        print(f"Found {len(towns_data)} towns")
        
        if not locations_data:
            print(f"No {location_type} data found")
            return []
        
        locations = []
        locations_data = locations_data[len(res):]
        remaining_locations = max_locations - len(res)
        for i, location_data in enumerate(locations_data[:remaining_locations]):
            if i % 5 == 0:
                print(f"Processing progress: {i+1}/{min(len(locations_data), remaining_locations)}")
            
            # Extract coordinates
            lat, lon = self._extract_coordinates(location_data)
            if lat is None or lon is None:
                print(f"Warning: {location_type} data missing coordinate information, skipping: {location_data.get('id', 'unknown')}")
                continue
            
            # Get basic information
            tags = location_data.get('tags', {})
            name = tags.get('name', f'{location_type}_{i+1}')
            
            # Get elevation
            elevation = None
            if 'ele' in tags:
                try:
                    elevation = float(tags['ele'])
                except ValueError:
                    pass
            
            if elevation is None:
                elevation = self._find_elevation_at_point_postgis(lat, lon)
                if elevation is None:
                    print(f"Warning: {location_type} data missing elevation information, skipping: {location_data.get('id', 'unknown')}")
            
            if elevation is None:
                elevation = self.get_elevation_from_api(lat, lon)
                time.sleep(0.1)  # Avoid API requests being too frequent
                if elevation is None:
                    print(f"Warning: {location_type} data missing elevation information, skipping: {location_data.get('id', 'unknown')}")
            
            if elevation is None:
                elevation = 0.0  # Default elevation
            
            # Find nearest town
            nearest_town = "Unknown"
            distance_to_town = 0.0
            town_elevation = None
            
            if towns_data:
                nearest_town, distance_to_town, town_elevation = self.find_nearest_town(
                    lat, lon, towns_data
                )
            
            # Get light pollution information
            light_pollution_level = None
            if 'light_pollution' in location_data:
                light_pollution_level = location_data['light_pollution'].get('pollution_level', 'Unknown pollution level')
            
            # Use specific processing function to create Location object
            location = location_processor_func(
                name, lat, lon, elevation, tags, 
                nearest_town, distance_to_town, town_elevation,
                light_pollution_level, i
            )
            
            if location:
                res.append(location)
        
        print(f"\nTotal found {len(locations)} {location_type}")
        
        # Save results to cache
        if self.cache:
            self.cache.save_to_cache(location_type, res)
            
        return res
    
    def _process_peak_data(self, name: str, lat: float, lon: float, elevation: float, 
                          tags: Dict, nearest_town: str, distance_to_town: float, 
                          town_elevation: Optional[float], light_pollution_level: Optional[str], 
                          index: int) -> Optional[Peak]:
        """
        Process mountain peak data and create Peak object
        """
        # Calculate height difference
        height_difference = None
        if town_elevation is not None:
            height_difference = elevation - town_elevation
            
            # Check if height difference requirement is met
            if height_difference < self.min_height_difference:
                print(f"Peak {name} insufficient height difference ({height_difference:.1f}m < {self.min_height_difference}m), skipping")
                return None
        
        return Peak(
            name=name,
            latitude=lat,
            longitude=lon,
            elevation=elevation,
            nearest_town_name=nearest_town,
            distance_to_nearest_town=distance_to_town,
            location_type="mountain_peak",
            height_difference=height_difference,
            light_pollution_level=light_pollution_level
        )
    
    def _process_observatory_data(self, name: str, lat: float, lon: float, elevation: float, 
                                 tags: Dict, nearest_town: str, distance_to_town: float, 
                                 town_elevation: Optional[float], light_pollution_level: Optional[str], 
                                 index: int) -> Optional[Observatory]:
        """
        Process observatory data and create Observatory object
        """
        # Determine observatory type
        observatory_type = "Unknown type"
        if tags.get('man_made') == 'observatory':
            observatory_type = "Astronomical observatory"
        elif tags.get('amenity') == 'planetarium':
            observatory_type = "Planetarium"
        elif tags.get('building') == 'observatory':
            observatory_type = "Observatory building"
        elif tags.get('man_made') == 'telescope':
            observatory_type = "Telescope"
        
        # Get description information
        description = tags.get('description', '')
        if not description:
            description = tags.get('note', '')
        
        return Observatory(
            name=name,
            latitude=lat,
            longitude=lon,
            elevation=elevation,
            nearest_town_name=nearest_town,
            distance_to_nearest_town=distance_to_town,
            location_type="observatory",
            observatory_type=observatory_type,
            description=description,
            light_pollution_level=light_pollution_level
        )
    
    def _process_viewpoint_data(self, name: str, lat: float, lon: float, elevation: float, 
                               tags: Dict, nearest_town: str, distance_to_town: float, 
                               town_elevation: Optional[float], light_pollution_level: Optional[str], 
                               index: int) -> Optional[Viewpoint]:
        """
        Process viewpoint data and create Viewpoint object
        """
        # Determine viewpoint type
        viewpoint_type = "Viewpoint"
        if 'tourism' in tags:
            if tags['tourism'] == 'viewpoint':
                viewpoint_type = "Viewpoint"
        elif 'natural' in tags:
            if tags['natural'] == 'peak':
                viewpoint_type = "Peak viewpoint"
        
        # Get description information
        description = tags.get('description', '')
        if not description:
            description = tags.get('note', '')
        
        # Evaluate scenic value
        scenic_value = "Medium"
        if elevation > 1000:
            scenic_value = "High"
        elif elevation > 500:
            scenic_value = "Medium"
        else:
            scenic_value = "Low"
        
        return Viewpoint(
            name=name,
            latitude=lat,
            longitude=lon,
            elevation=elevation,
            nearest_town_name=nearest_town,
            distance_to_nearest_town=distance_to_town,
            location_type="viewpoint",
            viewpoint_type=viewpoint_type,
            description=description,
            scenic_value=scenic_value,
            light_pollution_level=light_pollution_level
        )
     
    def find_peaks_in_area(self, bbox: Tuple[float, float, float, float], 
                           max_locations: int = 50) -> List[Peak]:
        """
        Find qualified peaks in specified area
        
        Args:
            bbox: Bounding box (south, west, north, east)
            max_locations: Maximum number of peaks to return
            
        Returns:
            List of qualified peaks
        """
        return self._find_locations_in_area(
            bbox=bbox,
            location_type="mountain_peak",
            max_locations=max_locations,
            data_getter_func=self.get_peaks_from_overpass,
            location_processor_func=self._process_peak_data
        )
    
    def find_observatories_in_area(self, bbox: Tuple[float, float, float, float], 
                                  max_observatories: int = 50) -> List[Observatory]:
        """
        Find observatories in specified area
        
        Args:
            bbox: Bounding box (south, west, north, east)
            max_observatories: Maximum number of observatories to return
            
        Returns:
            List of observatories
        """
        return self._find_locations_in_area(
            bbox=bbox,
            location_type="observatory",
            max_locations=max_observatories,
            data_getter_func=self.get_observatories_from_overpass,
            location_processor_func=self._process_observatory_data
        )
    
    def find_viewpoints_in_area(self, bbox: Tuple[float, float, float, float], 
                               max_viewpoints: int = 50) -> List[Viewpoint]:
        """
        Find viewpoints in specified area
        
        Args:
            bbox: Bounding box (south, west, north, east)
            max_viewpoints: Maximum number of viewpoints to return
            
        Returns:
            List of viewpoints
        """
        return self._find_locations_in_area(
            bbox=bbox,
            location_type="viewpoint",
            max_locations=max_viewpoints,
            data_getter_func=self.get_viewpoints_from_overpass,
            location_processor_func=self._process_viewpoint_data
        )
    
    def save_results_to_json(self, peaks: List[Peak], filename: str) -> None:
        """
        Save results to JSON file
        
        Args:
            peaks: List of peaks
            filename: Output filename
        """
        results = {
            "search_criteria": {
                "min_height_difference": self.min_height_difference
            },
            "total_peaks_found": len(peaks),
            "peaks": [
                {
                    "name": peak.name,
                    "latitude": peak.latitude,
                    "longitude": peak.longitude,
                    "elevation": peak.elevation,
                    "height_difference": peak.height_difference,
                    "distance_to_nearest_town": peak.distance_to_nearest_town,
                    "nearest_town_name": peak.nearest_town_name
                }
                for peak in peaks
            ]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"Results saved to: {filename}")

# Convenience functions
def find_peaks_with_height_difference(south: float, west: float, north: float, east: float,
                                     min_height_diff: float = 100.0,
                                     max_locations: int = 50) -> List[Peak]:
    """
    Find peaks with sufficient height difference from surrounding towns in specified area
    
    Args:
        south, west, north, east: Bounding box coordinates
        min_height_diff: Minimum height difference (meters)
        max_locations: Maximum number of peaks to search
        
    Returns:
        List of qualified peaks
    """
    kml_path = str(res.files('light_pollution').joinpath('resources', 'world_atlas', 'doc.kml'))
    finder = StarGazingPlaceFinder(min_height_difference=min_height_diff, light_pollution_analyzer=LightPollutionAnalyzer(kml_path))
    return finder.find_peaks_in_area((south, west, north, east), max_locations)

def find_viewpoints(south: float, west: float, north: float, east: float,
                   max_viewpoints: int = 50) -> List[Viewpoint]:
    """
    Find viewpoints in specified area
    
    Args:
        south, west, north, east: Bounding box coordinates
        max_viewpoints: Maximum number of viewpoints to search
        
    Returns:
        List of viewpoints, sorted by elevation
    """
    kml_path = str(res.files('light_pollution').joinpath('resources', 'world_atlas', 'doc.kml'))
    finder = StarGazingPlaceFinder(min_height_difference=100.0, light_pollution_analyzer=LightPollutionAnalyzer(kml_path))
    return finder.find_viewpoints_in_area((south, west, north, east), max_viewpoints)

if __name__ == "__main__":
    # Example: Search for peaks around Beijing
    print("=== Peak Finder Example ===")
    
    # Define search area (around Beijing)
    bbox = (39.5, 115.5, 40.5, 117.5)  # (south, west, north, east)
    
    # Create finder
    kml_path = str(res.files('light_pollution').joinpath('resources', 'world_atlas', 'doc.kml'))
    finder = StarGazingPlaceFinder(min_height_difference=100.0, light_pollution_analyzer=LightPollutionAnalyzer(kml_path))
    
    # Find peaks
    peaks = finder.find_peaks_in_area(bbox, max_locations=20)
    
    # Display results
    if peaks:
        print("\n=== Qualified Peaks ===")
        for i, peak in enumerate(peaks, 1):
            print(f"{i}. {peak.name}")
            print(f"   Coordinates: ({peak.latitude:.4f}, {peak.longitude:.4f})")
            print(f"   Elevation: {peak.elevation:.1f}m")
            print(f"   Height difference from {peak.nearest_town_name}: {peak.height_difference:.1f}m")
            print(f"   Distance to nearest town: {peak.distance_to_nearest_town:.1f}km")
            print()
        
        # Save results
        finder.save_results_to_json(peaks, "mountain_peaks_results.json")
    else:
        print("No qualified peaks found")
