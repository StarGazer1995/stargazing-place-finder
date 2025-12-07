from typing import List, Optional, Tuple
try:
    from utils.kml_parser import KMLParser, GroundOverlay
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'src'))
    from utils.kml_parser import KMLParser, GroundOverlay


class LocationFinder:
    """Geographic location finder
    
    This class uses KMLParser to parse KML files and provides functionality to find corresponding GroundOverlay based on geographic coordinates.
    Mainly used to find dark sky map overlay layers that contain the specified position based on latitude and longitude coordinates.
    """
    
    def __init__(self, kml_file_path: str):
        """Initialize geographic location finder
        
        Args:
            kml_file_path: KML file path
            
        Raises:
            FileNotFoundError: When KML file does not exist
            ValueError: When KML file format is incorrect
        """
        self.kml_file_path = kml_file_path
        self.parser = KMLParser(kml_file_path)
        self.overlays = None
        self._cached_stats = None
        self._load_overlays()
    
    def _load_overlays(self) -> None:
        """Load and cache all GroundOverlay data
        
        This method is called during initialization to load all GroundOverlay data into memory to improve query performance.
        Also pre-calculates statistical information to avoid repeated calculations.
        """
        self.overlays = self.parser.parse()
        # Pre-calculate statistical information to avoid repeated calculations
        self._cached_stats = self.parser.get_statistics(self.overlays)
        print(f"Loaded {len(self.overlays)} ground overlay layers")
    
    def find_overlay_by_coordinates(self, latitude: float, longitude: float) -> Optional[GroundOverlay]:
        """Find corresponding GroundOverlay based on geographic coordinates
        
        Args:
            latitude: Latitude (between -90 and 90)
            longitude: Longitude (between -180 and 180)
            
        Returns:
            GroundOverlay object containing the coordinates, or None if not found
            
        Raises:
            ValueError: When coordinate values are outside valid range
        """
        # Validate coordinate validity
        if not (-90 <= latitude <= 90):
            raise ValueError(f"Latitude must be between -90 and 90, current value: {latitude}")
        if not (-180 <= longitude <= 180):
            raise ValueError(f"Longitude must be between -180 and 180, current value: {longitude}")
        
        if self.overlays is None:
            return None
        
        # Find GroundOverlay containing the coordinates
        for overlay in self.overlays:
            if self._is_point_in_overlay(latitude, longitude, overlay):
                return overlay
        
        return None
    
    def find_all_overlays_by_coordinates(self, latitude: float, longitude: float) -> List[GroundOverlay]:
        """Find all GroundOverlays containing the specified point based on geographic coordinates
        
        Since there may be overlapping overlay layers, this method returns all GroundOverlays containing the specified coordinates.
        
        Args:
            latitude: Latitude (between -90 and 90)
            longitude: Longitude (between -180 and 180)
            
        Returns:
            List of all GroundOverlay objects containing the coordinates
            
        Raises:
            ValueError: When coordinate values are outside valid range
        """
        # Validate coordinate validity
        if not (-90 <= latitude <= 90):
            raise ValueError(f"Latitude must be between -90 and 90, current value: {latitude}")
        if not (-180 <= longitude <= 180):
            raise ValueError(f"Longitude must be between -180 and 180, current value: {longitude}")
        
        if self.overlays is None:
            return []
        
        # Find all GroundOverlays containing the coordinates
        matching_overlays = []
        for overlay in self.overlays:
            if self._is_point_in_overlay(latitude, longitude, overlay):
                matching_overlays.append(overlay)
        
        return matching_overlays
    
    def _is_point_in_overlay(self, latitude: float, longitude: float, overlay: GroundOverlay) -> bool:
        """Determine if a point is within the bounding box of a GroundOverlay
        
        Args:
            latitude: Latitude
            longitude: Longitude
            overlay: GroundOverlay object
            
        Returns:
            True if the point is within the bounding box, False otherwise
        """
        box = overlay.lat_lon_box
        
        # Check latitude range
        lat_in_range = box.south <= latitude <= box.north
        
        # Check longitude range (need to handle crossing 180-degree meridian)
        if box.west <= box.east:
            # Normal case: west longitude is less than east longitude
            lon_in_range = box.west <= longitude <= box.east
        else:
            # Crossing 180-degree meridian case: west longitude is greater than east longitude
            lon_in_range = longitude >= box.west or longitude <= box.east
        
        return lat_in_range and lon_in_range
    
    def get_overlay_info(self, latitude: float, longitude: float) -> dict:
        """Get detailed overlay information for the specified coordinate position
        
        Args:
            latitude: Latitude
            longitude: Longitude
            
        Returns:
            Dictionary containing location information and overlay details
        """
        overlays = self.find_all_overlays_by_coordinates(latitude, longitude)
        
        return {
            'coordinates': {
                'latitude': latitude,
                'longitude': longitude
            },
            'overlay_count': len(overlays),
            'overlays': [
                {
                    'name': overlay.name,
                    'icon_href': overlay.icon.href,
                    'draw_order': overlay.draw_order,
                    'color': overlay.color,
                    'bounds': {
                        'north': overlay.lat_lon_box.north,
                        'south': overlay.lat_lon_box.south,
                        'east': overlay.lat_lon_box.east,
                        'west': overlay.lat_lon_box.west
                    }
                } for overlay in overlays
            ]
        }
    
    def find_nearby_overlays(self, latitude: float, longitude: float, radius_degrees: float = 1.0) -> List[GroundOverlay]:
        """Find GroundOverlays near the specified coordinates
        
        Uses KMLParser's filter_by_bounds method to reduce redundant boundary check calculations.
        
        Args:
            latitude: Center point latitude
            longitude: Center point longitude
            radius_degrees: Search radius (degrees)
            
        Returns:
            List of nearby GroundOverlays
        """
        if self.overlays is None:
            return []
        
        # Calculate search boundaries
        min_lat = latitude - radius_degrees
        max_lat = latitude + radius_degrees
        min_lon = longitude - radius_degrees
        max_lon = longitude + radius_degrees
        
        # Use parser's filter_by_bounds method to avoid reimplementing boundary check logic
        return self.parser.filter_by_bounds(self.overlays, min_lat, max_lat, min_lon, max_lon)
    
    def find_overlays_in_bounds(self, north: float, south: float, 
                               east: float, west: float) -> List[GroundOverlay]:
        """Find all GroundOverlays within the specified geographic boundaries
        
        Args:
            north: North boundary latitude
            south: South boundary latitude
            east: East boundary longitude
            west: West boundary longitude
            
        Returns:
            List of GroundOverlays within the specified boundaries
        """
        if self.overlays is None:
            return []
        
        # Use parser's filter_by_bounds method to filter overlays
        return self.parser.filter_by_bounds(self.overlays, south, north, west, east)

    def get_statistics(self) -> dict:
        """Get statistical information of loaded overlays
        
        Uses cached statistical information to avoid repeated calculations.
        
        Returns:
            Dictionary of statistical information
        """
        if self._cached_stats is None:
            return {'count': 0}
        
        return self._cached_stats
    
    def reload_overlays(self) -> None:
        """Reload GroundOverlay data
        
        This method can be called to reload data when the KML file changes.
        Also clears cached statistical information.
        """
        self._cached_stats = None
        self._load_overlays()