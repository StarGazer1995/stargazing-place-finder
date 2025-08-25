"""观星地点查找器 - KML解析模块

这个模块提供了解析KML文件的功能，特别是用于处理包含地面覆盖层(GroundOverlay)的KML文件。
主要用于解析暗光地图数据，帮助寻找适合观星的地点。
"""

from .kml_parser import KMLParser, GroundOverlay, LatLonBox, Icon
from .location_finder import LocationFinder
from .light_pollution_analyzer import LightPollutionAnalyzer
from .light_pollution_visualizer import LightPollutionVisualizer
from .light_pollution_map import LightPollutionMap

__version__ = "1.0.0"
__author__ = "Stargazing Place Finder Team"

__all__ = [
    'KMLParser',
    'GroundOverlay', 
    'LatLonBox',
    'Icon',
    'LocationFinder',
    'LightPollutionAnalyzer',
    'LightPollutionVisualizer',
    'LightPollutionMap'
]