import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class LatLonBox:
    """表示地理边界框的数据类"""
    north: float
    south: float
    east: float
    west: float
    rotation: float = 0.0


@dataclass
class Icon:
    """表示图标的数据类"""
    href: str


@dataclass
class GroundOverlay:
    """表示地面覆盖层的数据类"""
    name: str
    draw_order: int
    color: str
    description: str
    icon: Icon
    lat_lon_box: LatLonBox


class KMLParser:
    """KML文件解析器"""
    
    def __init__(self, file_path: str):
        """初始化解析器
        
        Args:
            file_path: KML文件路径
        """
        self.file_path = file_path
        self.root = None
        self.namespaces = {
            'kml': 'http://www.opengis.net/kml/2.2',
            'gx': 'http://www.google.com/kml/ext/2.2',
            'atom': 'http://www.w3.org/2005/Atom'
        }
    
    def parse(self) -> List[GroundOverlay]:
        """解析KML文件并返回GroundOverlay列表
        
        Returns:
            GroundOverlay对象列表
        """
        try:
            tree = ET.parse(self.file_path)
            self.root = tree.getroot()
            return self._extract_ground_overlays()
        except ET.ParseError as e:
            raise ValueError(f"解析KML文件失败: {e}")
        except FileNotFoundError:
            raise FileNotFoundError(f"找不到文件: {self.file_path}")
    
    def _extract_ground_overlays(self) -> List[GroundOverlay]:
        """提取所有GroundOverlay元素
        
        Returns:
            GroundOverlay对象列表
        """
        ground_overlays = []
        
        # 查找所有GroundOverlay元素
        for overlay_elem in self.root.findall('.//kml:GroundOverlay', self.namespaces):
            overlay = self._parse_ground_overlay(overlay_elem)
            if overlay:
                ground_overlays.append(overlay)
        
        return ground_overlays
    
    def _parse_ground_overlay(self, overlay_elem) -> Optional[GroundOverlay]:
        """解析单个GroundOverlay元素
        
        Args:
            overlay_elem: GroundOverlay XML元素
            
        Returns:
            GroundOverlay对象或None
        """
        try:
            # 提取基本信息
            name = self._get_text(overlay_elem, 'kml:name', '')
            draw_order = int(self._get_text(overlay_elem, 'kml:drawOrder', '0'))
            color = self._get_text(overlay_elem, 'kml:color', 'ffffffff')
            description = self._get_text(overlay_elem, 'kml:Description', '')
            
            # 提取图标信息
            icon_elem = overlay_elem.find('kml:Icon', self.namespaces)
            if icon_elem is None:
                return None
            
            icon_href = self._get_text(icon_elem, 'kml:href', '')
            icon = Icon(href=icon_href)
            
            # 提取地理边界框信息
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
            print(f"解析GroundOverlay时出错: {e}")
            return None
    
    def _parse_lat_lon_box(self, lat_lon_box_elem) -> Optional[LatLonBox]:
        """解析LatLonBox元素
        
        Args:
            lat_lon_box_elem: LatLonBox XML元素
            
        Returns:
            LatLonBox对象或None
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
            print(f"解析LatLonBox时出错: {e}")
            return None
    
    def _get_text(self, parent_elem, xpath: str, default: str = '') -> str:
        """安全地获取XML元素的文本内容
        
        Args:
            parent_elem: 父元素
            xpath: XPath表达式
            default: 默认值
            
        Returns:
            元素文本内容或默认值
        """
        elem = parent_elem.find(xpath, self.namespaces)
        return elem.text if elem is not None and elem.text is not None else default
    
    def get_document_name(self) -> str:
        """获取文档名称
        
        Returns:
            文档名称
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
        """根据名称模式过滤GroundOverlay
        
        Args:
            overlays: GroundOverlay列表
            pattern: 名称模式（支持通配符）
            
        Returns:
            过滤后的GroundOverlay列表
        """
        import fnmatch
        return [overlay for overlay in overlays if fnmatch.fnmatch(overlay.name, pattern)]
    
    def filter_by_bounds(self, overlays: List[GroundOverlay], 
                        min_lat: float, max_lat: float, 
                        min_lon: float, max_lon: float) -> List[GroundOverlay]:
        """根据地理边界过滤GroundOverlay
        
        Args:
            overlays: GroundOverlay列表
            min_lat: 最小纬度
            max_lat: 最大纬度
            min_lon: 最小经度
            max_lon: 最大经度
            
        Returns:
            过滤后的GroundOverlay列表
        """
        filtered = []
        for overlay in overlays:
            box = overlay.lat_lon_box
            
            # 检查纬度范围是否有重叠
            lat_overlap = box.south <= max_lat and box.north >= min_lat
            
            if not lat_overlap:
                continue
            
            # 检查经度范围是否有重叠（需要处理跨越180度经线的情况）
            lon_overlap = False
            
            # 查询区域是否跨越180度经线
            if min_lon <= max_lon:
                # 查询区域不跨越180度经线
                if box.west <= box.east:
                    # 覆盖层也不跨越180度经线
                    lon_overlap = box.west <= max_lon and box.east >= min_lon
                else:
                    # 覆盖层跨越180度经线
                    lon_overlap = (box.west <= max_lon or box.east >= min_lon)
            else:
                # 查询区域跨越180度经线
                if box.west <= box.east:
                    # 覆盖层不跨越180度经线
                    lon_overlap = (box.west >= min_lon or box.east <= max_lon)
                else:
                    # 覆盖层也跨越180度经线
                    lon_overlap = True  # 两个都跨越180度经线，必然有重叠
            
            if lon_overlap:
                filtered.append(overlay)
        
        return filtered
    
    def get_statistics(self, overlays: List[GroundOverlay]) -> Dict[str, any]:
        """获取GroundOverlay统计信息
        
        Args:
            overlays: GroundOverlay列表
            
        Returns:
            统计信息字典
        """
        if not overlays:
            return {'count': 0}
        
        # 计算边界范围
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