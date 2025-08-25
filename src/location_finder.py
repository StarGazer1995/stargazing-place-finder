from typing import List, Optional, Tuple
try:
    from .kml_parser import KMLParser, GroundOverlay
except ImportError:
    from kml_parser import KMLParser, GroundOverlay


class LocationFinder:
    """地理位置查找器
    
    这个类使用KMLParser来解析KML文件，并提供根据地理坐标查找对应GroundOverlay的功能。
    主要用于根据经纬度坐标找到包含该位置的暗光地图覆盖层。
    """
    
    def __init__(self, kml_file_path: str):
        """初始化地理位置查找器
        
        Args:
            kml_file_path: KML文件路径
            
        Raises:
            FileNotFoundError: 当KML文件不存在时
            ValueError: 当KML文件格式错误时
        """
        self.kml_file_path = kml_file_path
        self.parser = KMLParser(kml_file_path)
        self.overlays = None
        self._cached_stats = None
        self._load_overlays()
    
    def _load_overlays(self) -> None:
        """加载并缓存所有GroundOverlay数据
        
        这个方法在初始化时调用，将所有GroundOverlay数据加载到内存中以提高查询性能。
        同时预计算统计信息以避免重复计算。
        """
        self.overlays = self.parser.parse()
        # 预计算统计信息，避免重复计算
        self._cached_stats = self.parser.get_statistics(self.overlays)
        print(f"已加载 {len(self.overlays)} 个地面覆盖层")
    
    def find_overlay_by_coordinates(self, latitude: float, longitude: float) -> Optional[GroundOverlay]:
        """根据地理坐标查找对应的GroundOverlay
        
        Args:
            latitude: 纬度（-90到90之间）
            longitude: 经度（-180到180之间）
            
        Returns:
            包含该坐标的GroundOverlay对象，如果没有找到则返回None
            
        Raises:
            ValueError: 当坐标值超出有效范围时
        """
        # 验证坐标有效性
        if not (-90 <= latitude <= 90):
            raise ValueError(f"纬度必须在-90到90之间，当前值: {latitude}")
        if not (-180 <= longitude <= 180):
            raise ValueError(f"经度必须在-180到180之间，当前值: {longitude}")
        
        if self.overlays is None:
            return None
        
        # 查找包含该坐标的GroundOverlay
        for overlay in self.overlays:
            if self._is_point_in_overlay(latitude, longitude, overlay):
                return overlay
        
        return None
    
    def find_all_overlays_by_coordinates(self, latitude: float, longitude: float) -> List[GroundOverlay]:
        """根据地理坐标查找所有包含该点的GroundOverlay
        
        由于可能存在重叠的覆盖层，这个方法返回所有包含指定坐标的GroundOverlay。
        
        Args:
            latitude: 纬度（-90到90之间）
            longitude: 经度（-180到180之间）
            
        Returns:
            包含该坐标的所有GroundOverlay对象列表
            
        Raises:
            ValueError: 当坐标值超出有效范围时
        """
        # 验证坐标有效性
        if not (-90 <= latitude <= 90):
            raise ValueError(f"纬度必须在-90到90之间，当前值: {latitude}")
        if not (-180 <= longitude <= 180):
            raise ValueError(f"经度必须在-180到180之间，当前值: {longitude}")
        
        if self.overlays is None:
            return []
        
        # 查找所有包含该坐标的GroundOverlay
        matching_overlays = []
        for overlay in self.overlays:
            if self._is_point_in_overlay(latitude, longitude, overlay):
                matching_overlays.append(overlay)
        
        return matching_overlays
    
    def _is_point_in_overlay(self, latitude: float, longitude: float, overlay: GroundOverlay) -> bool:
        """判断点是否在GroundOverlay的边界框内
        
        Args:
            latitude: 纬度
            longitude: 经度
            overlay: GroundOverlay对象
            
        Returns:
            如果点在边界框内返回True，否则返回False
        """
        box = overlay.lat_lon_box
        
        # 检查纬度范围
        lat_in_range = box.south <= latitude <= box.north
        
        # 检查经度范围（需要处理跨越180度经线的情况）
        if box.west <= box.east:
            # 正常情况：西经度小于东经度
            lon_in_range = box.west <= longitude <= box.east
        else:
            # 跨越180度经线的情况：西经度大于东经度
            lon_in_range = longitude >= box.west or longitude <= box.east
        
        return lat_in_range and lon_in_range
    
    def get_overlay_info(self, latitude: float, longitude: float) -> dict:
        """获取指定坐标位置的详细覆盖层信息
        
        Args:
            latitude: 纬度
            longitude: 经度
            
        Returns:
            包含位置信息和覆盖层详情的字典
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
        """查找指定坐标附近的GroundOverlay
        
        使用KMLParser的filter_by_bounds方法来减少重复的边界检查计算。
        
        Args:
            latitude: 中心点纬度
            longitude: 中心点经度
            radius_degrees: 搜索半径（度数）
            
        Returns:
            附近的GroundOverlay列表
        """
        if self.overlays is None:
            return []
        
        # 计算搜索边界
        min_lat = latitude - radius_degrees
        max_lat = latitude + radius_degrees
        min_lon = longitude - radius_degrees
        max_lon = longitude + radius_degrees
        
        # 使用parser的filter_by_bounds方法，避免重复实现边界检查逻辑
        return self.parser.filter_by_bounds(self.overlays, min_lat, max_lat, min_lon, max_lon)
    
    def find_overlays_in_bounds(self, north: float, south: float, 
                               east: float, west: float) -> List[GroundOverlay]:
        """查找指定地理边界内的所有GroundOverlay
        
        Args:
            north: 北边界纬度
            south: 南边界纬度
            east: 东边界经度
            west: 西边界经度
            
        Returns:
            在指定边界内的GroundOverlay列表
        """
        if self.overlays is None:
            return []
        
        # 使用parser的filter_by_bounds方法来过滤覆盖层
        return self.parser.filter_by_bounds(self.overlays, south, north, west, east)

    def get_statistics(self) -> dict:
        """获取加载的覆盖层统计信息
        
        使用缓存的统计信息，避免重复计算。
        
        Returns:
            统计信息字典
        """
        if self._cached_stats is None:
            return {'count': 0}
        
        return self._cached_stats
    
    def reload_overlays(self) -> None:
        """重新加载GroundOverlay数据
        
        当KML文件发生变化时，可以调用此方法重新加载数据。
        同时清除缓存的统计信息。
        """
        self._cached_stats = None
        self._load_overlays()