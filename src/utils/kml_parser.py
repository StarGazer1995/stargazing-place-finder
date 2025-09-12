import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class LatLonBox:
    """Data class representing a geographic bounding box"""
    north: float
    south: float
    east: float
    west: float
    rotation: float = 0.0


@dataclass
class Icon:
    """Data class representing an icon"""
    href: str


@dataclass
class GroundOverlay:
    """Data class representing a ground overlay"""
    name: str
    draw_order: int
    color: str
    description: str
    icon: Icon
    lat_lon_box: LatLonBox


class KMLParser:
    """KML file parser"""
    
    def __init__(self, file_path: str):
        """Initialize the parser
        
        Args:
            file_path: Path to the KML file
        """
        self.file_path = file_path
        self.root = None
        self.namespaces = {
            'kml': 'http://www.opengis.net/kml/2.2',
            'gx': 'http://www.google.com/kml/ext/2.2',
            'atom': 'http://www.w3.org/2005/Atom'
        }
    
    def parse(self) -> List[GroundOverlay]:
        """Parse KML file and return list of GroundOverlay objects
        
        Returns:
            List of GroundOverlay objects
        """
        try:
            tree = ET.parse(self.file_path)
            self.root = tree.getroot()
            return self._extract_ground_overlays()
        except ET.ParseError as e:
            raise ValueError(f"Failed to parse KML file: {e}")
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {self.file_path}")
    
    def _extract_ground_overlays(self) -> List[GroundOverlay]:
        """Extract all GroundOverlay elements
        
        Returns:
            List of GroundOverlay objects
        """
        ground_overlays = []
        
        # Find all GroundOverlay elements
        for overlay_elem in self.root.findall('.//kml:GroundOverlay', self.namespaces):
            overlay = self._parse_ground_overlay(overlay_elem)
            if overlay:
                ground_overlays.append(overlay)
        
        return ground_overlays
    
    def _parse_ground_overlay(self, overlay_elem) -> Optional[GroundOverlay]:
        """Parse a single GroundOverlay element
        
        Args:
            overlay_elem: GroundOverlay XML element
            
        Returns:
            GroundOverlay object or None
        """
        try:
            # Extract basic information
            name = self._get_text(overlay_elem, 'kml:name', '')
            draw_order = int(self._get_text(overlay_elem, 'kml:drawOrder', '0'))
            color = self._get_text(overlay_elem, 'kml:color', 'ffffffff')
            description = self._get_text(overlay_elem, 'kml:Description', '')
            
            # Extract icon information
            icon_elem = overlay_elem.find('kml:Icon', self.namespaces)
            if icon_elem is None:
                return None
            
            icon_href = self._get_text(icon_elem, 'kml:href', '')
            icon = Icon(href=icon_href)
            
            # Extract geographic bounding box information
            lat_lon_box_elem = overlay_elem.find('kml:LatLonBox', self.namespaces)
            if lat_lon_box_elem is None:
                return None
            
            lat_lon_box = self._parse_lat_lon_box(lat_lon_box_elem)
            if lat_lon_box is None:
                return None
            
            return GroundOverlay(
                name=name,
                draw_order=draw_order,
                color=color,
                description=description,
                icon=icon,
                lat_lon_box=lat_lon_box
            )
            
        except (ValueError, AttributeError) as e:
            print(f"Error parsing GroundOverlay: {e}")
            return None
    
    def _parse_lat_lon_box(self, lat_lon_box_elem) -> Optional[LatLonBox]:
        """Parse LatLonBox element
        
        Args:
            lat_lon_box_elem: LatLonBox XML element
            
        Returns:
            LatLonBox object or None
        """
        try:
            north = float(self._get_text(lat_lon_box_elem, 'kml:north', '0'))
            south = float(self._get_text(lat_lon_box_elem, 'kml:south', '0'))
            east = float(self._get_text(lat_lon_box_elem, 'kml:east', '0'))
            west = float(self._get_text(lat_lon_box_elem, 'kml:west', '0'))
            rotation = float(self._get_text(lat_lon_box_elem, 'kml:rotation', '0'))
            
            return LatLonBox(
                north=north,
                south=south,
                east=east,
                west=west,
                rotation=rotation
            )
            
        except ValueError as e:
            print(f"Error parsing LatLonBox: {e}")
            return None
    
    def _get_text(self, parent_elem, xpath: str, default: str = '') -> str:
        """Safely get text content from XML element
        
        Args:
            parent_elem: Parent element
            xpath: XPath expression
            default: Default value
            
        Returns:
            Element text content or default value
        """
        elem = parent_elem.find(xpath, self.namespaces)
        return elem.text if elem is not None and elem.text is not None else default
    
    def get_document_name(self) -> str:
        """Get document name
        
        Returns:
            Document name
        """
        if self.root is None:
            return ''
        
        doc_elem = self.root.find('kml:Document', self.namespaces)
        if doc_elem is not None:
            name_elem = doc_elem.find('kml:Name', self.namespaces)
            if name_elem is not None and name_elem.text:
                return name_elem.text
        
        return ''
    
    def filter_by_name_pattern(self, overlays: List[GroundOverlay], pattern: str) -> List[GroundOverlay]:
        """Filter GroundOverlay by name pattern
        
        Args:
            overlays: List of GroundOverlay objects
            pattern: Name pattern (supports wildcards)
            
        Returns:
            Filtered list of GroundOverlay objects
        """
        import fnmatch
        return [overlay for overlay in overlays if fnmatch.fnmatch(overlay.name, pattern)]
    
    def filter_by_bounds(self, overlays: List[GroundOverlay], 
                        min_lat: float, max_lat: float, 
                        min_lon: float, max_lon: float) -> List[GroundOverlay]:
        """Filter GroundOverlay by geographic bounds
        
        Args:
            overlays: List of GroundOverlay objects
            min_lat: Minimum latitude
            max_lat: Maximum latitude
            min_lon: Minimum longitude
            max_lon: Maximum longitude
            
        Returns:
            Filtered list of GroundOverlay objects
        """
        filtered = []
        for overlay in overlays:
            box = overlay.lat_lon_box
            
            # Check if latitude ranges overlap
            lat_overlap = box.south <= max_lat and box.north >= min_lat
            
            if not lat_overlap:
                continue
            
            # Check if longitude ranges overlap (handle crossing 180° meridian)
            lon_overlap = False
            
            # Check if query region crosses 180° meridian
            if min_lon <= max_lon:
                # Query region does not cross 180° meridian
                if box.west <= box.east:
                    # Overlay also does not cross 180° meridian
                    lon_overlap = box.west <= max_lon and box.east >= min_lon
                else:
                    # Overlay crosses 180° meridian
                    lon_overlap = (box.west <= max_lon or box.east >= min_lon)
            else:
                # Query region crosses 180° meridian
                if box.west <= box.east:
                    # Overlay does not cross 180° meridian
                    lon_overlap = (box.west >= min_lon or box.east <= max_lon)
                else:
                    # Overlay also crosses 180° meridian
                    lon_overlap = True  # Both cross 180° meridian, must overlap
            
            if lon_overlap:
                filtered.append(overlay)
        
        return filtered
    
    def get_statistics(self, overlays: List[GroundOverlay]) -> Dict[str, any]:
        """Get GroundOverlay statistics
        
        Args:
            overlays: List of GroundOverlay objects
            
        Returns:
            Statistics dictionary
        """
        if not overlays:
            return {'count': 0}
        
        # Calculate boundary ranges
        min_north = min(overlay.lat_lon_box.north for overlay in overlays)
        max_north = max(overlay.lat_lon_box.north for overlay in overlays)
        min_south = min(overlay.lat_lon_box.south for overlay in overlays)
        max_south = max(overlay.lat_lon_box.south for overlay in overlays)
        min_east = min(overlay.lat_lon_box.east for overlay in overlays)
        max_east = max(overlay.lat_lon_box.east for overlay in overlays)
        min_west = min(overlay.lat_lon_box.west for overlay in overlays)
        max_west = max(overlay.lat_lon_box.west for overlay in overlays)
        
        return {
            'count': len(overlays),
            'bounds': {
                'north': {'min': min_north, 'max': max_north},
                'south': {'min': min_south, 'max': max_south},
                'east': {'min': min_east, 'max': max_east},
                'west': {'min': min_west, 'max': max_west}
            },
            'unique_names': len(set(overlay.name for overlay in overlays))
        }