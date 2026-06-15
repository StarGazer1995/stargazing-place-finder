# -*- coding: utf-8 -*-
"""
GIS data parsing and transformation utilities.

Pure functions extracted from StarGazingPlaceFinder for extracting coordinates,
calculating distances, finding nearest towns, processing location data,
and sorting by light pollution.
"""

import math
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from models import GeoCoordinate, Observatory, Peak, Viewpoint


def extract_coordinates(data: Dict) -> Tuple[Optional[float], Optional[float]]:
    """
    Extract coordinates from location data dict (Overpass API format).

    Args:
        data: Location data dictionary with 'type', 'lat', 'lon' or 'center' keys.

    Returns:
        (latitude, longitude) or (None, None) if extraction fails.
    """
    try:
        if data["type"] == "node":
            return data["lat"], data["lon"]
        elif "center" in data:
            return data["center"]["lat"], data["center"]["lon"]
        else:
            return None, None
    except KeyError:
        return None, None


def calculate_distance(p1: GeoCoordinate, p2: GeoCoordinate) -> float:
    """
    Calculate distance between two geographic coordinates using Haversine formula.

    Args:
        p1: First point coordinate.
        p2: Second point coordinate.

    Returns:
        Distance in kilometers.
    """
    R = 6371  # Earth radius (kilometers)
    lat1, lon1 = p1.latitude, p1.longitude
    lat2, lon2 = p2.latitude, p2.longitude

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat / 2) * math.sin(delta_lat / 2) + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(
        delta_lon / 2
    ) * math.sin(delta_lon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def find_nearest_town(
    point: GeoCoordinate,
    towns: List[Dict],
    elevation_func: Optional[Callable[[float, float], Optional[float]]] = None,
) -> Tuple[Optional[str], float, Optional[float]]:
    """
    Find the nearest town to a given coordinate.

    Args:
        point: The geographic point to search from.
        towns: List of town data dicts (Overpass API format).
        elevation_func: Optional callable (lat, lon) -> elevation_m for
                        looking up town elevation.

    Returns:
        (nearest_town_name, distance_km, town_elevation_m).
    """
    lat, lon = point.latitude, point.longitude
    min_distance = float("inf")
    nearest_town = None
    nearest_town_elevation = None

    for town in towns:
        try:
            if town["type"] == "node":
                town_lat = town["lat"]
                town_lon = town["lon"]
            elif "center" in town:
                town_lat = town["center"]["lat"]
                town_lon = town["center"]["lon"]
            else:
                continue
        except KeyError:
            continue

        distance = calculate_distance(point, GeoCoordinate(latitude=town_lat, longitude=town_lon))

        if distance < min_distance:
            min_distance = distance
            nearest_town = town.get("tags", {}).get("name", "Unknown town")
            if elevation_func:
                nearest_town_elevation = elevation_func(town_lat, town_lon)
                time.sleep(0.1)

    return nearest_town, min_distance, nearest_town_elevation


def sort_places_by_lightpollution(
    places: List[Dict],
    light_pollution_analyzer: Any,
) -> List[Dict]:
    """
    Sort places by light pollution level (ascending brightness).

    Args:
        places: List of place dicts with lat/lon or center/geom.
        light_pollution_analyzer: Analyzer instance with
                                  batch_analyze_coordinates() method.

    Returns:
        Places sorted by light pollution (lowest first), with
        ``light_pollution`` key attached to each dict.
    """
    if not light_pollution_analyzer or not places:
        return places

    places_coord = []
    valid_places = []
    for place in places:
        try:
            if place["type"] == "node":
                lat = place["lat"]
                lon = place["lon"]
            elif "center" in place:
                lat = place["center"]["lat"]
                lon = place["center"]["lon"]
            else:
                continue
            places_coord.append([lat, lon])
            valid_places.append(place)
        except KeyError:
            continue

    if not places_coord:
        return []

    sorted_pollutions = sorted(
        light_pollution_analyzer.batch_analyze_coordinates(places_coord),
        key=lambda x: x["pollution_info"].brightness,
        reverse=False,
    )
    sorted_places = [valid_places[p["index"]] for p in sorted_pollutions]
    for place, poll in zip(sorted_places, sorted_pollutions):
        place["light_pollution"] = poll["pollution_info"]

    return sorted_places


# ── Location object builders ──────────────────────────────────────────


def process_peak_data(
    name: str,
    point: GeoCoordinate,
    elevation: float,
    tags: Dict,
    nearest_town: str,
    distance_to_town: float,
    town_elevation: Optional[float],
    light_pollution_level: Optional[str],
    index: int,
    min_height_difference: float = 100.0,
) -> Optional[Peak]:
    """
    Build a Peak object, applying height-difference filtering.

    Args:
        min_height_difference: Minimum height difference (m) from nearest
                               town; peaks below this threshold are skipped.
    """
    lat, lon = point.latitude, point.longitude
    height_difference = None
    if town_elevation is not None:
        height_difference = elevation - town_elevation
        if height_difference < min_height_difference:
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
        light_pollution_level=light_pollution_level,
    )


def process_observatory_data(
    name: str,
    point: GeoCoordinate,
    elevation: float,
    tags: Dict,
    nearest_town: str,
    distance_to_town: float,
    town_elevation: Optional[float],
    light_pollution_level: Optional[str],
    index: int,
) -> Observatory:
    """Build an Observatory object from raw data."""
    lat, lon = point.latitude, point.longitude
    observatory_type = "Unknown type"
    if tags.get("man_made") == "observatory":
        observatory_type = "Astronomical observatory"
    elif tags.get("amenity") == "planetarium":
        observatory_type = "Planetarium"
    elif tags.get("building") == "observatory":
        observatory_type = "Observatory building"
    elif tags.get("man_made") == "telescope":
        observatory_type = "Telescope"

    description = tags.get("description", "") or tags.get("note", "")

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
        light_pollution_level=light_pollution_level,
    )


def process_viewpoint_data(
    name: str,
    point: GeoCoordinate,
    elevation: float,
    tags: Dict,
    nearest_town: str,
    distance_to_town: float,
    town_elevation: Optional[float],
    light_pollution_level: Optional[str],
    index: int,
) -> Viewpoint:
    """Build a Viewpoint object from raw data."""
    lat, lon = point.latitude, point.longitude
    viewpoint_type = "Viewpoint"
    if tags.get("tourism") == "viewpoint":
        viewpoint_type = "Viewpoint"
    elif tags.get("natural") == "peak":
        viewpoint_type = "Peak viewpoint"

    description = tags.get("description", "") or tags.get("note", "")
    scenic_value = "High" if elevation > 1000 else ("Medium" if elevation > 500 else "Low")

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
        light_pollution_level=light_pollution_level,
    )
