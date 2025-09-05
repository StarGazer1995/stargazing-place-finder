#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Light Pollution Visualization Module

This module provides visualization functionality for light pollution data around specified locations,
including heatmaps, contour maps, etc.
"""

import os
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Circle
from typing import List, Tuple, Dict, Optional, Any
from .light_pollution_analyzer import LightPollutionAnalyzer


class LightPollutionVisualizer:
    """
    Light Pollution Visualizer
    
    Provides light pollution data visualization functionality based on LightPollutionAnalyzer,
    including heatmaps, contour maps, scatter plots and other visualization methods.
    """
    
    def __init__(self, kml_file_path: str):
        """
        Initialize light pollution visualizer
        
        Args:
            kml_file_path: KML file path
        """
        self.analyzer = LightPollutionAnalyzer(kml_file_path)
        
        # Light pollution level color mapping - fixed color scheme: 1 is black, 7 is red
        self.pollution_colors = {
            'Class 1': '#000000',  # Black - best stargazing conditions
            'Class 2': '#0000FF',  # Blue - excellent stargazing conditions
            'Class 3': '#00FF00',  # Green - good stargazing conditions
            'Class 4': '#FFFF00',  # Yellow - average stargazing conditions
            'Class 5': '#FFA500',  # Orange - poor stargazing conditions
            'Class 6': '#FF4500',  # Orange-red - bad stargazing conditions
            'Class 7+': '#FF0000', # Red - very bad stargazing conditions
            'Unknown': '#AAAAAA'   # Gray - no data
        }
        
        # Set font support for international characters
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two geographic coordinates (kilometers)
        
        Args:
            lat1, lon1: Latitude and longitude of the first point
            lat2, lon2: Latitude and longitude of the second point
            
        Returns:
            Distance (kilometers)
        """
        # Use Haversine formula to calculate spherical distance
        R = 6371  # Earth radius (kilometers)
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def _generate_grid_coordinates(self, center_lat: float, center_lon: float, 
                                 radius_km: float, grid_size: int = 50) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate grid coordinates within specified range
        
        Args:
            center_lat: Center point latitude
            center_lon: Center point longitude
            radius_km: Radius (kilometers)
            grid_size: Grid size
            
        Returns:
            Longitude grid and latitude grid
        """
        # Calculate latitude and longitude range (rough estimation)
        lat_range = radius_km / 111.0  # 1 degree latitude ≈ 111 km
        lon_range = radius_km / (111.0 * math.cos(math.radians(center_lat)))  # Longitude varies with latitude
        
        # Generate grid
        lats = np.linspace(center_lat - lat_range, center_lat + lat_range, grid_size)
        lons = np.linspace(center_lon - lon_range, center_lon + lon_range, grid_size)
        
        return np.meshgrid(lons, lats)
    
    def _collect_pollution_data(self, center_lat: float, center_lon: float, 
                              radius_km: float, grid_size: int = 50) -> Dict[str, Any]:
        """
        Collect light pollution data within specified range
        
        Args:
            center_lat: Center point latitude
            center_lon: Center point longitude
            radius_km: Radius (kilometers)
            grid_size: Grid size
            
        Returns:
            Dictionary containing coordinates, brightness values, pollution levels and other information
        """
        lon_grid, lat_grid = self._generate_grid_coordinates(center_lat, center_lon, radius_km, grid_size)
        
        brightness_grid = np.full_like(lat_grid, np.nan)
        pollution_levels = []
        valid_coordinates = []
        
        print(f"Collecting light pollution data within {grid_size}x{grid_size} grid...")
        
        total_points = grid_size * grid_size
        processed_points = 0
        
        for i in range(grid_size):
            for j in range(grid_size):
                lat, lon = lat_grid[i, j], lon_grid[i, j]
                
                # Check if within specified radius
                distance = self._calculate_distance(center_lat, center_lon, lat, lon)
                if distance <= radius_km:
                    try:
                        pollution_info = self.analyzer.get_light_pollution_color(lat, lon)
                        if pollution_info:
                            brightness_grid[i, j] = pollution_info['brightness']
                            pollution_levels.append(pollution_info['pollution_level'])
                            valid_coordinates.append((lat, lon, pollution_info))
                    except Exception as e:
                        # Ignore errors, continue processing other points
                        pass
                
                processed_points += 1
                if processed_points % 500 == 0:
                    progress = (processed_points / total_points) * 100
                    print(f"Progress: {progress:.1f}% ({processed_points}/{total_points})")
        
        print(f"Data collection completed, valid data points: {len(valid_coordinates)}")
        
        return {
            'lon_grid': lon_grid,
            'lat_grid': lat_grid,
            'brightness_grid': brightness_grid,
            'pollution_levels': pollution_levels,
            'valid_coordinates': valid_coordinates,
            'center_lat': center_lat,
            'center_lon': center_lon,
            'radius_km': radius_km
        }
    
    def create_heatmap(self, center_lat: float, center_lon: float, radius_km: float = 10.0,
                      grid_size: int = 50, save_path: Optional[str] = None, 
                      show_plot: bool = True) -> str:
        """
        Create light pollution heatmap
        
        Args:
            center_lat: Center point latitude
            center_lon: Center point longitude
            radius_km: Radius (kilometers)
            grid_size: Grid size
            save_path: Save path (optional)
            show_plot: Whether to display the chart
            
        Returns:
            Chart save path or status information
        """
        # Collect data
        data = self._collect_pollution_data(center_lat, center_lon, radius_km, grid_size)
        
        # Create chart
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # Draw heatmap
        im = ax.contourf(data['lon_grid'], data['lat_grid'], data['brightness_grid'], 
                        levels=20, cmap='YlOrRd', alpha=0.8)
        
        # Add color bar
        cbar = plt.colorbar(im, ax=ax, shrink=0.8)
        cbar.set_label('Light Pollution Brightness (0-255)', fontsize=12)
        
        # Mark center point
        ax.plot(center_lon, center_lat, 'ko', markersize=10, markerfacecolor='blue', 
               markeredgecolor='white', markeredgewidth=2, label='Query Center Point')
        
        # Draw radius circle
        # Convert kilometers to latitude/longitude (rough estimation)
        lat_radius = radius_km / 111.0
        lon_radius = radius_km / (111.0 * math.cos(math.radians(center_lat)))
        circle = Circle((center_lon, center_lat), max(lat_radius, lon_radius), 
                       fill=False, color='blue', linestyle='--', linewidth=2, 
                       label=f'{radius_km}km Range')
        ax.add_patch(circle)
        
        # Set title and labels
        ax.set_title(f'Light Pollution Heatmap\nCenter: ({center_lat:.4f}°, {center_lon:.4f}°), Radius: {radius_km}km', 
                    fontsize=14, fontweight='bold')
        ax.set_xlabel('Longitude', fontsize=12)
        ax.set_ylabel('Latitude', fontsize=12)
        
        # Set coordinate axes
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Set coordinate axis scale
        ax.set_aspect('equal', adjustable='box')
        
        plt.tight_layout()
        
        # Save or display
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            result = f"Heatmap saved to: {save_path}"
        else:
            result = "Heatmap generated"
        
        if show_plot:
            plt.show()
        else:
            plt.close()
        
        return result
    
    def create_contour_map(self, center_lat: float, center_lon: float, radius_km: float = 10.0,
                          grid_size: int = 50, save_path: Optional[str] = None, 
                          show_plot: bool = True) -> str:
        """
        Create light pollution contour map
        
        Args:
            center_lat: Center point latitude
            center_lon: Center point longitude
            radius_km: Radius (kilometers)
            grid_size: Grid size
            save_path: Save path (optional)
            show_plot: Whether to display the chart
            
        Returns:
            Chart save path or status information
        """
        # Collect data
        data = self._collect_pollution_data(center_lat, center_lon, radius_km, grid_size)
        
        # Create chart
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # Draw contour lines
        levels = [0, 50, 100, 150, 200, 255]
        contour = ax.contour(data['lon_grid'], data['lat_grid'], data['brightness_grid'], 
                           levels=levels, colors='black', linewidths=1)
        ax.clabel(contour, inline=True, fontsize=10, fmt='%d')
        
        # Draw filled contour lines
        contourf = ax.contourf(data['lon_grid'], data['lat_grid'], data['brightness_grid'], 
                             levels=levels, cmap='YlOrRd', alpha=0.6)
        
        # Add color bar
        cbar = plt.colorbar(contourf, ax=ax, shrink=0.8)
        cbar.set_label('Light Pollution Brightness', fontsize=12)
        
        # Mark center point
        ax.plot(center_lon, center_lat, 'ko', markersize=10, markerfacecolor='blue', 
               markeredgecolor='white', markeredgewidth=2, label='Query Center Point')
        
        # Draw radius circle
        lat_radius = radius_km / 111.0
        lon_radius = radius_km / (111.0 * math.cos(math.radians(center_lat)))
        circle = Circle((center_lon, center_lat), max(lat_radius, lon_radius), 
                       fill=False, color='blue', linestyle='--', linewidth=2, 
                       label=f'{radius_km}km Range')
        ax.add_patch(circle)
        
        # Set title and labels
        ax.set_title(f'Light Pollution Contour Map\nCenter: ({center_lat:.4f}°, {center_lon:.4f}°), Radius: {radius_km}km', 
                    fontsize=14, fontweight='bold')
        ax.set_xlabel('Longitude', fontsize=12)
        ax.set_ylabel('Latitude', fontsize=12)
        
        # Set coordinate axes
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.set_aspect('equal', adjustable='box')
        
        plt.tight_layout()
        
        # Save or display
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            result = f"Contour map saved to: {save_path}"
        else:
            result = "Contour map generated"
        
        if show_plot:
            plt.show()
        else:
            plt.close()
        
        return result
    
    def create_scatter_plot(self, center_lat: float, center_lon: float, radius_km: float = 10.0,
                           sample_points: int = 200, save_path: Optional[str] = None, 
                           show_plot: bool = True) -> str:
        """
        Create light pollution scatter plot
        
        Args:
            center_lat: Center point latitude
            center_lon: Center point longitude
            radius_km: Radius (kilometers)
            sample_points: Number of sample points
            save_path: Save path (optional)
            show_plot: Whether to display the chart
            
        Returns:
            Chart save path or status information
        """
        # Generate random sample points
        coordinates = []
        pollution_data = []
        
        print(f"Sampling {sample_points} random points...")
        
        attempts = 0
        max_attempts = sample_points * 5  # Maximum attempts: 5 times the number of points
        
        while len(coordinates) < sample_points and attempts < max_attempts:
            # Generate random points within circular area
            angle = np.random.uniform(0, 2 * np.pi)
            r = np.random.uniform(0, radius_km)
            
            # Convert to latitude/longitude offset
            lat_offset = (r * np.cos(angle)) / 111.0
            lon_offset = (r * np.sin(angle)) / (111.0 * np.cos(math.radians(center_lat)))
            
            lat = center_lat + lat_offset
            lon = center_lon + lon_offset
            
            try:
                pollution_info = self.analyzer.get_light_pollution_color(lat, lon)
                if pollution_info:
                    coordinates.append((lat, lon))
                    pollution_data.append(pollution_info)
            except Exception:
                pass
            
            attempts += 1
            
            if len(coordinates) % 50 == 0 and len(coordinates) > 0:
                print(f"Sampled: {len(coordinates)} valid points")
        
        if not coordinates:
            return "No valid light pollution data points found"
        
        print(f"Sampling completed, obtained {len(coordinates)} valid data points")
        
        # Create chart
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # Extract data
        lats = [coord[0] for coord in coordinates]
        lons = [coord[1] for coord in coordinates]
        brightness_values = [data['brightness'] for data in pollution_data]
        
        # Draw scatter plot
        scatter = ax.scatter(lons, lats, c=brightness_values, cmap='YlOrRd', 
                           s=50, alpha=0.7, edgecolors='black', linewidth=0.5)
        
        # Add color bar
        cbar = plt.colorbar(scatter, ax=ax, shrink=0.8)
        cbar.set_label('Light Pollution Brightness', fontsize=12)
        
        # Mark center point
        ax.plot(center_lon, center_lat, 'ko', markersize=12, markerfacecolor='blue', 
               markeredgecolor='white', markeredgewidth=3, label='Query Center Point')
        
        # Draw radius circle
        lat_radius = radius_km / 111.0
        lon_radius = radius_km / (111.0 * math.cos(math.radians(center_lat)))
        circle = Circle((center_lon, center_lat), max(lat_radius, lon_radius), 
                       fill=False, color='blue', linestyle='--', linewidth=2, 
                       label=f'{radius_km}km Range')
        ax.add_patch(circle)
        
        # Set title and labels
        ax.set_title(f'Light Pollution Scatter Plot\nCenter: ({center_lat:.4f}°, {center_lon:.4f}°), Sample Points: {len(coordinates)}', 
                    fontsize=14, fontweight='bold')
        ax.set_xlabel('Longitude', fontsize=12)
        ax.set_ylabel('Latitude', fontsize=12)
        
        # Set coordinate axes
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.set_aspect('equal', adjustable='box')
        
        plt.tight_layout()
        
        # Save or display
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            result = f"Scatter plot saved to: {save_path}"
        else:
            result = "Scatter plot generated"
        
        if show_plot:
            plt.show()
        else:
            plt.close()
        
        return result
    
    def create_comprehensive_report(self, center_lat: float, center_lon: float, 
                                  radius_km: float = 10.0, location_name: str = "Query Location",
                                  output_dir: str = "visualization_output") -> Dict[str, str]:
        """
        Create comprehensive light pollution analysis report
        
        Args:
            center_lat: Center point latitude
            center_lon: Center point longitude
            radius_km: Radius (kilometers)
            location_name: Location name
            output_dir: Output directory
            
        Returns:
            Dictionary containing various chart paths
        """
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename prefix
        safe_name = location_name.replace(' ', '_').replace('/', '_')
        prefix = f"{safe_name}_{center_lat:.4f}_{center_lon:.4f}_{radius_km}km"
        
        results = {}
        
        print(f"Generating comprehensive light pollution analysis report for {location_name}...")
        
        # Generate heatmap
        print("1/3 Generating heatmap...")
        heatmap_path = os.path.join(output_dir, f"{prefix}_heatmap.png")
        results['heatmap'] = self.create_heatmap(center_lat, center_lon, radius_km, 
                                                save_path=heatmap_path, show_plot=False)
        
        # Generate contour map
        print("2/3 Generating contour map...")
        contour_path = os.path.join(output_dir, f"{prefix}_contour.png")
        results['contour'] = self.create_contour_map(center_lat, center_lon, radius_km, 
                                                   save_path=contour_path, show_plot=False)
        
        # Generate scatter plot
        print("3/3 Generating scatter plot...")
        scatter_path = os.path.join(output_dir, f"{prefix}_scatter.png")
        results['scatter'] = self.create_scatter_plot(center_lat, center_lon, radius_km, 
                                                    save_path=scatter_path, show_plot=False)
        
        print(f"Comprehensive report generation completed! Files saved in: {output_dir}")
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get visualizer statistics
        
        Returns:
            Statistics dictionary
        """
        analyzer_stats = self.analyzer.get_statistics()
        
        return {
            'analyzer_stats': analyzer_stats,
            'available_colors': list(self.pollution_colors.keys()),
            'color_mapping': self.pollution_colors
        }