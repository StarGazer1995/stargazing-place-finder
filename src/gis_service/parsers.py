# -*- coding: utf-8 -*-
"""
GIS data parsing and transformation utilities.

Pure functions extracted from StarGazingPlaceFinder for extracting coordinates,
calculating distances, finding nearest towns, processing location data,
and sorting by light pollution.
"""

import math
from typing import TYPE_CHECKING, Callable, Dict, List, Optional

from models import GeoPoint, Observatory, Peak, TownInfo, Viewpoint

# ═══════════════════════════════════════════════════════════════════════
#  Shared conversion utilities (single source of truth)
# ═══════════════════════════════════════════════════════════════════════


def brightness_to_bortle(brightness: int) -> int:
    """
    Map a 0-255 brightness value to the Bortle scale (1-9).

    Args:
        brightness: Brightness value (0-255). Lower = darker sky.

    Returns:
        Bortle class (1 = pristine dark sky, 9 = inner-city sky).
    """
    if brightness <= 28:
        return 1
    elif brightness <= 56:
        return 2
    elif brightness <= 84:
        return 3
    elif brightness <= 112:
        return 4
    elif brightness <= 140:
        return 5
    elif brightness <= 168:
        return 6
    elif brightness <= 196:
        return 7
    elif brightness <= 224:
        return 8
    else:
        return 9


def bortle_to_sqm(bortle: int) -> float:
    """
    Convert a Bortle class to SQM (magnitudes per square arcsecond).

    Args:
        bortle: Bortle class (1-9).

    Returns:
        Approximate SQM value.
    """
    sqm_values = {
        1: 21.9,
        2: 21.6,
        3: 21.3,
        4: 20.4,
        5: 19.5,
        6: 18.5,
        7: 17.5,
        8: 16.5,
        9: 15.5,
    }
    return float(sqm_values.get(bortle, 20.0))


def get_pollution_level_description(bortle: int) -> str:
    """
    Return a human-readable Chinese description for a Bortle class.

    Args:
        bortle: Bortle class (1-9).

    Returns:
        Description string.
    """
    descriptions = {
        1: "优秀暗空",
        2: "典型暗空",
        3: "乡村天空",
        4: "乡村/郊区过渡",
        5: "郊区天空",
        6: "明亮郊区",
        7: "郊区/城市过渡",
        8: "城市天空",
        9: "内城天空",
    }
    return descriptions.get(bortle, "未知等级")


if TYPE_CHECKING:
    from light_pollution.light_pollution_analyzer import LightPollutionAnalyzer


def extract_coordinates(data: Dict) -> Optional[GeoPoint]:
    """
    Extract coordinates from location data dict (Overpass API format).

    Args:
        data: Location data dictionary with 'type', 'lat', 'lon' or 'center' keys.

    Returns:
        A GeoPoint, or None if extraction fails.
    """
    try:
        if data["type"] == "node":
            return GeoPoint(lat=data["lat"], lon=data["lon"])
        elif "center" in data:
            return GeoPoint(lat=data["center"]["lat"], lon=data["center"]["lon"])
        else:
            return None
    except KeyError:
        return None


def calculate_distance(p1: GeoPoint, p2: GeoPoint) -> float:
    """
    Calculate distance between two geographic coordinates using Haversine formula.

    Args:
        p1: First point coordinate.
        p2: Second point coordinate.

    Returns:
        Distance in kilometers.
    """
    R = 6371  # Earth radius (kilometers)
    lat1, lon1 = p1.lat, p1.lon
    lat2, lon2 = p2.lat, p2.lon

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
    point: GeoPoint,
    towns: List[Dict],
    elevation_func: Optional[Callable[[float, float], Optional[float]]] = None,
) -> TownInfo:
    """
    Find the nearest town to a given coordinate.

    Args:
        point: The geographic point to search from.
        towns: List of town data dicts (Overpass API format).
        elevation_func: Optional callable (lat, lon) -> elevation_m for
                        looking up town elevation.

    Returns:
        TownInfo with name, distance_km and elevation_m.
    """
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

        distance = calculate_distance(point, GeoPoint(lat=town_lat, lon=town_lon))

        if distance < min_distance:
            min_distance = distance
            nearest_town = town.get("tags", {}).get("name", "Unknown town")
            nearest_town_elevation = None

    return TownInfo(name=nearest_town, distance_km=min_distance, elevation_m=nearest_town_elevation)


def sort_places_by_lightpollution(
    places: List[Dict],
    light_pollution_analyzer: "LightPollutionAnalyzer",
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
        key=lambda x: x["pollution_info"].brightness if x["pollution_info"] else float("inf"),
        reverse=False,
    )
    sorted_places = [valid_places[p["index"]] for p in sorted_pollutions]
    for place, poll in zip(sorted_places, sorted_pollutions):
        place["light_pollution"] = poll["pollution_info"]

    return sorted_places


# ── Location object builders ──────────────────────────────────────────


def process_peak_data(
    name: str,
    point: GeoPoint,
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
    lat, lon = point.lat, point.lon
    height_difference = None
    if town_elevation is not None:
        height_difference = elevation - town_elevation
        if height_difference < min_height_difference:
            return None

    return Peak(
        name=name,
        lat=lat,
        lon=lon,
        elevation=elevation,
        nearest_town_name=nearest_town,
        distance_to_nearest_town=distance_to_town,
        location_type="mountain_peak",
        height_difference=height_difference,
        light_pollution_level=light_pollution_level,
    )


def process_observatory_data(
    name: str,
    point: GeoPoint,
    elevation: float,
    tags: Dict,
    nearest_town: str,
    distance_to_town: float,
    town_elevation: Optional[float],
    light_pollution_level: Optional[str],
    index: int,
) -> Observatory:
    """Build an Observatory object from raw data."""
    lat, lon = point.lat, point.lon
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
        lat=lat,
        lon=lon,
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
    point: GeoPoint,
    elevation: float,
    tags: Dict,
    nearest_town: str,
    distance_to_town: float,
    town_elevation: Optional[float],
    light_pollution_level: Optional[str],
    index: int,
) -> Viewpoint:
    """Build a Viewpoint object from raw data."""
    lat, lon = point.lat, point.lon
    viewpoint_type = "Viewpoint"
    if tags.get("tourism") == "viewpoint":
        viewpoint_type = "Viewpoint"
    elif tags.get("natural") == "peak":
        viewpoint_type = "Peak viewpoint"

    description = tags.get("description", "") or tags.get("note", "")
    scenic_value = "High" if elevation > 1000 else ("Medium" if elevation > 500 else "Low")

    return Viewpoint(
        name=name,
        lat=lat,
        lon=lon,
        elevation=elevation,
        nearest_town_name=nearest_town,
        distance_to_nearest_town=distance_to_town,
        location_type="viewpoint",
        viewpoint_type=viewpoint_type,
        description=description,
        scenic_value=scenic_value,
        light_pollution_level=light_pollution_level,
    )
