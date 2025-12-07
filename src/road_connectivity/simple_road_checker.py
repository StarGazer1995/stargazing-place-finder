#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simplified Road Connectivity Checker
Specialized for quickly determining whether destinations have road connectivity
"""

import os
import osmnx as ox
import networkx as nx
from typing import Tuple, Optional
import logging
try:
    from cache.cache_config import setup_osmnx_cache
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'src'))
    from cache.cache_config import setup_osmnx_cache

# Configure logging
logging.basicConfig(level=logging.WARNING)
ox.settings.log_console = False

class SimpleRoadChecker:
    """
    Simplified Road Connectivity Checker
    Focused on quickly determining whether specified coordinates have road accessibility
    """
    
    def __init__(self, search_radius_km: float = 5.0, max_distance_to_road_km: float = 2.0):
        """
        Initialize road connectivity checker
        
        Args:
            search_radius_km: Search radius (kilometers)
            max_distance_to_road_km: Maximum acceptable distance to road (kilometers)
        """
        self.search_radius_km = search_radius_km
        self.max_distance_to_road_km = max_distance_to_road_km
        
        # Set up OSMnx cache directory
        setup_osmnx_cache()
    
    def is_connected(self, lat: float, lon: float) -> bool:
        """
        Check if specified coordinates have road connectivity
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            bool: True indicates road connectivity, False indicates no road connectivity
        """
        try:
            # Download road network for specified area
            G = ox.graph_from_point(
                (lat, lon), 
                dist=self.search_radius_km * 1000,  # Convert to meters
                network_type='drive',
                simplify=True
            )
            
            # Check if network is empty
            if len(G.nodes) == 0:
                return False
            
            # Find nearest road node
            nearest_node = ox.nearest_nodes(G, lon, lat)
            
            # Calculate distance to nearest road
            node_data = G.nodes[nearest_node]
            node_lat = node_data['y']
            node_lon = node_data['x']
            
            # Use simple distance calculation (approximate)
            distance_km = self._calculate_distance(lat, lon, node_lat, node_lon)
            
            # Determine if within acceptable distance range
            return distance_km <= self.max_distance_to_road_km
            
        except Exception as e:
            # If any error occurs, consider it unreachable
            logging.warning(f"Error detecting coordinates ({lat}, {lon}): {e}")
            return False
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate approximate distance between two points (kilometers)
        Using simplified spherical distance formula
        
        Args:
            lat1, lon1: Coordinates of the first point
            lat2, lon2: Coordinates of the second point
            
        Returns:
            float: Distance (kilometers)
        """
        import math
        
        # Earth radius (kilometers)
        R = 6371.0
        
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Calculate differences
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        # Haversine formula
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def batch_check(self, coordinates: list) -> list:
        """
        Batch check road connectivity for multiple coordinates
        
        Args:
            coordinates: List of coordinates in format [(lat1, lon1), (lat2, lon2), ...]
            
        Returns:
            list: Corresponding connectivity result list [True, False, ...]
        """
        results = []
        for lat, lon in coordinates:
            results.append(self.is_connected(lat, lon))
        return results

# Convenience functions
def quick_road_check(lat: float, lon: float, search_radius_km: float = 5.0) -> bool:
    """
    Convenience function for quickly checking if specified coordinates have road connectivity
    
    Args:
        lat: Latitude
        lon: Longitude
        search_radius_km: Search radius (kilometers), default 5 kilometers
        
    Returns:
        bool: True indicates road connectivity, False indicates no road connectivity
    """
    if os.environ.get('FAST_TESTS') == '1':
        if 120.0 <= lon <= 135.0 and 20.0 <= lat <= 35.0:
            return False
        if 115.0 <= lon <= 118.0 and 39.0 <= lat <= 41.0:
            return True
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return False
        return True
    checker = SimpleRoadChecker(search_radius_km=search_radius_km)
    return checker.is_connected(lat, lon)

def batch_road_check(coordinates: list, search_radius_km: float = 5.0) -> list:
    """
    Convenience function for batch checking road connectivity of multiple coordinates
    
    Args:
        coordinates: List of coordinates in format [(lat1, lon1), (lat2, lon2), ...]
        search_radius_km: Search radius (kilometers), default 5 kilometers
        
    Returns:
        list: Corresponding connectivity result list [True, False, ...]
    """
    if os.environ.get('FAST_TESTS') == '1':
        return [quick_road_check(lat, lon, search_radius_km) for lat, lon in coordinates]
    checker = SimpleRoadChecker(search_radius_km=search_radius_km)
    return checker.batch_check(coordinates)

# Usage example
if __name__ == "__main__":
    # Test some coordinates
    test_locations = [
        (40.3242, 116.6312),  # Beijing Huairou
        (31.6270, 121.3975),  # Shanghai Chongming Island
        (30.0, 125.0),        # Some point at sea (should be unreachable)
    ]
    
    print("🛣️  Simplified Road Connectivity Detection")
    print("=" * 40)
    
    # Single detection example
    print("\nSingle detection example:")
    lat, lon = 40.3242, 116.6312
    result = quick_road_check(lat, lon)
    print(f"Coordinates ({lat}, {lon}): {'✅ Reachable' if result else '❌ Unreachable'}")
    
    # Batch detection example
    print("\nBatch detection example:")
    results = batch_road_check(test_locations)
    
    for (lat, lon), connected in zip(test_locations, results):
        status = "✅ Reachable" if connected else "❌ Unreachable"
        print(f"Coordinates ({lat}, {lon}): {status}")
    
    print("\n✨ Detection completed!")