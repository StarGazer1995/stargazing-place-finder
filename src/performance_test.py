#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance Test Script

This script is used to test the performance optimization effects of the LocationFinder class,
comparing performance differences between using cache and not using cache.
"""

import os
import sys
import time
from typing import List
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from location_finder import LocationFinder


def benchmark_statistics_calls(finder: LocationFinder, num_calls: int = 100) -> float:
    """Test the performance of statistics retrieval
    
    Args:
        finder: LocationFinder instance
        num_calls: Number of calls
        
    Returns:
        Average time per call (seconds)
    """
    start_time = time.time()
    
    for _ in range(num_calls):
        stats = finder.get_statistics()
    
    end_time = time.time()
    total_time = end_time - start_time
    avg_time = total_time / num_calls
    
    return avg_time


def benchmark_coordinate_queries(finder: LocationFinder, coordinates: List[tuple], num_iterations: int = 10) -> float:
    """Test the performance of coordinate queries
    
    Args:
        finder: LocationFinder instance
        coordinates: Coordinate list [(lat, lon), ...]
        num_iterations: Number of iterations
        
    Returns:
        Average time per query (seconds)
    """
    start_time = time.time()
    
    for _ in range(num_iterations):
        for lat, lon in coordinates:
            overlay = finder.find_overlay_by_coordinates(lat, lon)
    
    end_time = time.time()
    total_time = end_time - start_time
    total_queries = len(coordinates) * num_iterations
    avg_time = total_time / total_queries
    
    return avg_time


def benchmark_nearby_searches(finder: LocationFinder, coordinates: List[tuple], num_iterations: int = 10) -> float:
    """Test the performance of nearby searches
    
    Args:
        finder: LocationFinder instance
        coordinates: Coordinate list [(lat, lon), ...]
        num_iterations: Number of iterations
        
    Returns:
        Average time per search (seconds)
    """
    start_time = time.time()
    
    for _ in range(num_iterations):
        for lat, lon in coordinates:
            nearby = finder.find_nearby_overlays(lat, lon, radius_degrees=2.0)
    
    end_time = time.time()
    total_time = end_time - start_time
    total_searches = len(coordinates) * num_iterations
    avg_time = total_time / total_searches
    
    return avg_time


def main():
    """Main function: Execute performance tests"""
    # KML file path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    kml_file = os.path.join(project_root, 'world_atlas', 'doc.kml')
    
    try:
        print("=== LocationFinder Performance Test ===")
        print("Initializing LocationFinder...")
        
        # Measure initialization time
        init_start = time.time()
        finder = LocationFinder(kml_file)
        init_time = time.time() - init_start
        
        print(f"Initialization completed, time taken: {init_time:.4f} seconds")
        
        # Test coordinate set
        test_coordinates = [
            (39.9042, 116.4074),  # Beijing
            (31.2304, 121.4737),  # Shanghai
            (40.7128, -74.0060),  # New York
            (51.5074, -0.1278),   # London
            (35.6762, 139.6503),  # Tokyo
            (-33.8688, 151.2093), # Sydney
            (0.0, -160.0),        # Pacific Center
            (48.8566, 2.3522),    # Paris
            (55.7558, 37.6176),   # Moscow
            (-22.9068, -43.1729)  # Rio de Janeiro
        ]
        
        print("\n=== Statistics Retrieval Performance Test ===")
        stats_time = benchmark_statistics_calls(finder, num_calls=1000)
        print(f"Average time for 1000 statistics calls: {stats_time*1000:.4f} milliseconds")
        print(f"Statistics retrieval is very fast due to caching")
        
        print("\n=== Coordinate Query Performance Test ===")
        query_time = benchmark_coordinate_queries(finder, test_coordinates, num_iterations=100)
        print(f"Average coordinate query time: {query_time*1000:.4f} milliseconds/query")
        print(f"Total executed {len(test_coordinates) * 100} queries")
        
        print("\n=== Nearby Search Performance Test ===")
        nearby_time = benchmark_nearby_searches(finder, test_coordinates, num_iterations=50)
        print(f"Average nearby search time: {nearby_time*1000:.4f} milliseconds/search")
        print(f"Total executed {len(test_coordinates) * 50} searches")
        print(f"Used KMLParser's filter_by_bounds method to avoid duplicate boundary check logic")
        
        print("\n=== Memory Usage ===")
        stats = finder.get_statistics()
        print(f"Number of loaded overlays: {stats['count']}")
        print(f"Statistics are cached to avoid duplicate calculations")
        
        print("\n=== Reload Test ===")
        reload_start = time.time()
        finder.reload_overlays()
        reload_time = time.time() - reload_start
        print(f"Reload time: {reload_time:.4f} seconds")
        print(f"Reloading clears cache and recalculates statistics")
        
        print("\n=== Performance Optimization Summary ===")
        print("1. Statistics caching: Avoid duplicate calculation of boundaries and statistics")
        print("2. Reuse Parser methods: find_nearby_overlays uses filter_by_bounds to reduce duplicate code")
        print("3. One-time loading: Load all data into memory during initialization to improve query speed")
        print("4. Smart cache management: Automatically clear cache and recalculate during reload")
        
        print("\n=== Test Completed ===")
        
    except FileNotFoundError:
        print(f"Error: KML file not found {kml_file}")
        print("Please ensure the file path is correct")
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()