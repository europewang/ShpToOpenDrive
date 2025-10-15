import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point, MultiLineString
from typing import Dict, List, Tuple, Optional, Any
import logging
import os
from abc import ABC, abstractmethod
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'shp_to_opendrive.log')
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
        ]
    )
logger = logging.getLogger(__name__)
try:
    from geometry_converter import ConversionHandler
except ImportError:
    class ConversionHandler(ABC):
        def __init__(self):
            self._next_handler = None
        def set_next(self, handler: 'ConversionHandler') -> 'ConversionHandler':
            self._next_handler = handler
            return handler
        @abstractmethod
        def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
            pass
        def _handle_next(self, request: Dict[str, Any]) -> Dict[str, Any]:
            if self._next_handler:
                return self._next_handler.handle(request)
            return request
class ShapefileReadingHandler(ConversionHandler):
    def __init__(self, coordinate_precision: int = 3):
        super().__init__()
        self.coordinate_precision = coordinate_precision
        self.shp_reader = None
    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        if request.get('stage') != 'shapefile_loading':
            return self._handle_next(request)
        shapefile_path = request.get('shapefile_path', '')
        attribute_mapping = request.get('attribute_mapping', {})
        config = request.get('config', {})
        if not shapefile_path:
            request['success'] = False
            request['error'] = '未提供shapefile路径'
            return self._handle_next(request)
        self.shp_reader = ShapefileReader(shapefile_path, self.coordinate_precision)
        if not self.shp_reader.load_shapefile():
            request['success'] = False
            request['error'] = 'shapefile加载失败'
            return self._handle_next(request)
        if not self.shp_reader.convert_to_utm():
            logger.warning("坐标系转换失败，继续使用原坐标系")
        if not self.shp_reader.convert_to_local_coordinates():
            logger.warning("局部坐标系转换失败，继续使用当前坐标系")
        filtered_count = self.shp_reader.filter_roads_by_length(
            config.get('min_road_length', 1.0)
        )
        if filtered_count == 0:
            request['success'] = False
            request['error'] = '过滤后没有剩余道路'
            return self._handle_next(request)
        roads_geometries = self.shp_reader.extract_road_geometries()
        if not roads_geometries:
            request['success'] = False
            request['error'] = '提取道路数据失败'
            return self._handle_next(request)
        if self._is_lane_format(roads_geometries):
            roads_data = self._process_lane_data(roads_geometries, attribute_mapping)
        else:
            roads_data = self._process_traditional_data(roads_geometries, attribute_mapping)
        request['roads_data'] = roads_data
        request['stage'] = 'geometry_conversion'
        return self._handle_next(request)
    def _is_lane_format(self, roads_geometries: List[Dict]) -> bool:
        if not roads_geometries:
            return False
        first_road = roads_geometries[0]
        return all(key in first_road for key in ['road_id', 'lanes', 'lane_surfaces'])
    def _process_lane_data(self, roads_geometries: List[Dict], attribute_mapping: Dict = None) -> List[Dict]:
        roads_data = []
        for road_geom in roads_geometries:
            road_data = {
                'id': road_geom['road_id'],
                'type': 'lane_based',
                'lane_surfaces': road_geom.get('lane_surfaces', []),
                'attributes': self._extract_lane_attributes(road_geom.get('lanes', []), attribute_mapping)
            }
            roads_data.append(road_data)
        return roads_data
    def _process_traditional_data(self, roads_geometries: List[Dict], attribute_mapping: Dict = None) -> List[Dict]:
        roads_data = []
        for road_geom in roads_geometries:
            road_data = {
                'id': road_geom['id'],
                'type': 'traditional',
                'coordinates': road_geom['coordinates'],
                'attributes': self._map_attributes(road_geom.get('attributes', {}), attribute_mapping or {})
            }
            roads_data.append(road_data)
        return roads_data
    def _extract_lane_attributes(self, lanes: List[Dict], attribute_mapping: Dict = None) -> Dict:
        if not lanes:
            return {}
        first_lane = lanes[0]
        return self._map_attributes(first_lane.get('attributes', {}), attribute_mapping or {})
    def _map_attributes(self, original_attrs: Dict, mapping: Dict) -> Dict:
        mapped_attrs = {}
        for key, value in original_attrs.items():
            mapped_key = mapping.get(key, key)
            mapped_attrs[mapped_key] = value
        return mapped_attrs
class ShapefileReader:
    def __init__(self, shapefile_path: str, coordinate_precision: int = 3):
        self.shapefile_path = shapefile_path
        self.coordinate_precision = max(1, min(10, coordinate_precision))  # 限制在1-10之间
        self.gdf = None
        self.roads_data = []
        self.lane_data = {}  # 存储按RoadID分组的车道数据
        self.coordinate_offset = {'x': 0.0, 'y': 0.0}  # 存储坐标偏移量
    def load_shapefile(self) -> bool:
        try:
            self.gdf = gpd.read_file(self.shapefile_path)
            logger.info(f"成功加载shapefile: {self.shapefile_path}")
            logger.info(f"包含 {len(self.gdf)} 条道路记录")
            logger.info(f"坐标系统: {self.gdf.crs}")
            return True
        except Exception as e:
            logger.error(f"加载shapefile失败: {e}")
            return False
    def get_coordinate_offset(self) -> Dict:
        return self.coordinate_offset.copy()
    def get_road_info(self) -> Dict:
        if self.gdf is None:
            return {}
        return {
            'road_count': len(self.gdf),
            'crs': str(self.gdf.crs),
            'bounds': self.gdf.total_bounds.tolist(),
            'columns': self.gdf.columns.tolist(),
            'geometry_types': self.gdf.geometry.geom_type.unique().tolist()
        }
    def extract_road_geometries(self) -> List[Dict]:
        if self.gdf is None:
            logger.error("请先加载shapefile")
            return []
        if self._is_lane_shapefile():
            return self.extract_lane_geometries()
        roads = []
        for idx, row in self.gdf.iterrows():
            geometry = row.geometry
            if not isinstance(geometry, LineString):
                logger.warning(f"跳过非线性几何 (索引: {idx})")
                continue
            coords = [(coord[0], coord[1]) for coord in geometry.coords]
            road_info = {
                'id': idx,
                'geometry': geometry,
                'coordinates': coords,
                'length': geometry.length,
                'start_point': coords[0],
                'end_point': coords[-1],
                'attributes': {}
            }
            for col in self.gdf.columns:
                if col != 'geometry':
                    road_info['attributes'][col] = row[col]
            roads.append(road_info)
        self.roads_data = roads
        logger.info(f"提取了 {len(roads)} 条有效道路")
        return roads
    def _is_lane_shapefile(self) -> bool:
        if self.gdf is None:
            return False
        columns = [col.upper() for col in self.gdf.columns]
        return 'ROADID' in columns and 'INDEX' in columns
    def extract_lane_geometries(self) -> List[Dict]:
        if self.gdf is None:
            logger.error("请先加载shapefile")
            return []
        logger.info("检测到Lane.shp格式，开始提取车道数据")
        grouped = self.gdf.groupby('RoadID')
        roads = []
        logger.info(f"开始处理 {len(grouped)} 个RoadID分组")
        for road_id, group in grouped:
            logger.info(f"\n=== 处理RoadID: {road_id} ===")
            logger.info(f"该RoadID包含 {len(group)} 条边界线记录")
            original_indices = group['Index'].tolist()
            logger.info(f"原始Index值: {original_indices}")
            try:
                group_sorted = group.sort_values('Index', key=lambda x: x.astype(int))
            except (ValueError, TypeError):
                logger.warning(f"RoadID {road_id} 的Index无法转换为整数，使用字符串排序")
                group_sorted = group.sort_values('Index')
            sorted_indices = group_sorted['Index'].tolist()
            logger.info(f"排序后Index值: {sorted_indices}")
            boundary_lines = []
            for idx, row in group_sorted.iterrows():
                geometry = row.geometry
                if isinstance(geometry, LineString):
                    coords = [(coord[0], coord[1]) for coord in geometry.coords]
                    boundary_info = {
                        'index': str(row['Index']),  # 保持为字符串，如"01", "12", "23"
                        'geometry': geometry,
                        'coordinates': coords,
                        'length': geometry.length,
                        'start_point': coords[0],
                        'end_point': coords[-1],
                        'attributes': {}
                    }
                    for col in self.gdf.columns:
                        if col != 'geometry':
                            boundary_info['attributes'][col] = row[col]
                    boundary_lines.append(boundary_info)
                    logger.info(f"  添加边界线 Index={row['Index']}, 长度={geometry.length:.2f}m, 坐标点数={len(coords)}")
                else:
                    logger.warning(f"跳过非线性几何 (RoadID: {road_id}, Index: {row['Index']})")
            logger.info(f"RoadID {road_id} 共处理了 {len(boundary_lines)} 条边界线")
            lanes = self._build_lanes_from_boundaries(boundary_lines)
            logger.info(f"RoadID {road_id} 构建了 {len(lanes)} 个车道面")
            road_info = {
                'road_id': str(road_id),
                'lanes': lanes,
                'lane_count': len(lanes),
                'lane_surfaces': self._build_lane_surfaces(lanes)
            }
            roads.append(road_info)
        self.roads_data = roads
        logger.info(f"提取了 {len(roads)} 条道路，共 {sum(len(road['lanes']) for road in roads)} 条车道")
        return roads
    def _build_lanes_from_boundaries(self, boundary_lines: List[Dict]) -> List[Dict]:
        lanes = []
        logger.info(f"  开始构建车道面，输入边界线数量: {len(boundary_lines)}")
        boundaries_sorted = sorted(boundary_lines, key=lambda x: x['index'])
        sorted_indices = [b['index'] for b in boundaries_sorted]
        logger.info(f"  边界线排序后Index顺序: {sorted_indices}")
        for i in range(len(boundaries_sorted) - 1):
            left_boundary = boundaries_sorted[i]
            right_boundary = boundaries_sorted[i + 1]
            surface_id = f"{left_boundary['index']}_{right_boundary['index']}"
            logger.info(f"    构建车道面 {surface_id}: 左边界Index={left_boundary['index']}, 右边界Index={right_boundary['index']}")
            lane_surface = {
                'surface_id': surface_id,
                'left_boundary': {
                    'index': left_boundary['index'],
                    'coordinates': left_boundary['coordinates'],
                    'geometry': left_boundary['geometry']
                },
                'right_boundary': {
                    'index': right_boundary['index'],
                    'coordinates': right_boundary['coordinates'],
                    'geometry': right_boundary['geometry']
                },
                'center_line': self._calculate_center_line(
                    left_boundary['coordinates'], 
                    right_boundary['coordinates']
                ),
                'width_profile': self._calculate_width_profile(
                    left_boundary['coordinates'], 
                    right_boundary['coordinates']
                ),
                'attributes': self._merge_boundary_attributes(
                    left_boundary['attributes'], 
                    right_boundary['attributes']
                )
            }
            lanes.append(lane_surface)
            logger.info(f"    车道面 {surface_id} 构建完成，中心线点数={len(lane_surface['center_line'])}，宽度变化点数={len(lane_surface['width_profile'])}")
        return lanes
    def _build_lane_surfaces(self, lanes: List[Dict]) -> List[Dict]:
        return lanes
    def get_road_attributes_mapping(self) -> Dict[str, str]:
        if self.gdf is None:
            return {}
        mapping_suggestions = {}
        columns = [col.lower() for col in self.gdf.columns if col != 'geometry']
        for col in columns:
            if any(keyword in col for keyword in ['type', 'class', 'category']):
                mapping_suggestions[col] = 'road_type'
            elif any(keyword in col for keyword in ['width', 'lane']):
                mapping_suggestions[col] = 'lane_width'
            elif any(keyword in col for keyword in ['speed', 'limit']):
                mapping_suggestions[col] = 'speed_limit'
            elif any(keyword in col for keyword in ['name', 'id']):
                mapping_suggestions[col] = 'road_name'
        return mapping_suggestions
    def _calculate_center_line(self, left_coords: List[tuple], right_coords: List[tuple]) -> List[tuple]:
        if len(left_coords) != len(right_coords):
            min_len = min(len(left_coords), len(right_coords))
            left_coords = left_coords[:min_len]
            right_coords = right_coords[:min_len]
        center_coords = []
        for left_pt, right_pt in zip(left_coords, right_coords):
            center_x = (left_pt[0] + right_pt[0]) / 2
            center_y = (left_pt[1] + right_pt[1]) / 2
            center_coords.append((center_x, center_y))
        return center_coords
    def _calculate_width_profile(self, left_coords: List[tuple], right_coords: List[tuple]) -> List[float]:
        import math
        if len(left_coords) != len(right_coords):
            min_len = min(len(left_coords), len(right_coords))
            left_coords = left_coords[:min_len]
            right_coords = right_coords[:min_len]
        widths = []
        for left_pt, right_pt in zip(left_coords, right_coords):
            width = math.sqrt((left_pt[0] - right_pt[0])**2 + (left_pt[1] - right_pt[1])**2)
            width = round(width, self.coordinate_precision)
            widths.append(width)
        return widths
    def _merge_boundary_attributes(self, left_attrs: Dict, right_attrs: Dict) -> Dict:
        merged = {}
        merged.update(left_attrs)
        for key, value in right_attrs.items():
            if key not in merged:
                merged[key] = value
        return merged
    def convert_to_utm(self) -> bool:
        if self.gdf is None:
            return False
        try:
            if self.gdf.crs.is_geographic:
                bounds = self.gdf.total_bounds
                center_lon = (bounds[0] + bounds[2]) / 2
                utm_zone = int((center_lon + 180) / 6) + 1
                center_lat = (bounds[1] + bounds[3]) / 2
                hemisphere = 'north' if center_lat >= 0 else 'south'
                utm_crs = f"EPSG:{32600 + utm_zone if hemisphere == 'north' else 32700 + utm_zone}"
                original_crs = self.gdf.crs
                logger.info(f"原始坐标系: {original_crs}")
                self.gdf = self.gdf.to_crs(utm_crs)
                logger.info(f"坐标系已转换为: {utm_crs}")
                new_bounds = self.gdf.total_bounds
                logger.info(f"转换后坐标范围: X[{new_bounds[0]:.2f}, {new_bounds[2]:.2f}], Y[{new_bounds[1]:.2f}, {new_bounds[3]:.2f}]")
            else:
                logger.info(f"当前坐标系已是投影坐标系: {self.gdf.crs}")
            return True
        except Exception as e:
            logger.error(f"坐标系转换失败: {e}")
            return False
    def convert_to_local_coordinates(self) -> bool:
        if self.gdf is None:
            return False
        try:
            bounds = self.gdf.total_bounds
            min_x, min_y = bounds[0], bounds[1]
            self.coordinate_offset = {'x': min_x, 'y': min_y}
            logger.info(f"原点设置为: ({min_x:.2f}, {min_y:.2f})")
            def translate_geometry(geom):
                if geom.geom_type == 'LineString':
                    coords = [(x - min_x, y - min_y) for x, y in geom.coords]
                    return LineString(coords)
                elif geom.geom_type == 'MultiLineString':
                    lines = []
                    for line in geom.geoms:
                        coords = [(x - min_x, y - min_y) for x, y in line.coords]
                        lines.append(LineString(coords))
                    return MultiLineString(lines)
                else:
                    return geom
            self.gdf['geometry'] = self.gdf['geometry'].apply(translate_geometry)
            new_bounds = self.gdf.total_bounds
            logger.info(f"局部坐标系范围: X[{new_bounds[0]:.2f}, {new_bounds[2]:.2f}], Y[{new_bounds[1]:.2f}, {new_bounds[3]:.2f}]")
            return True
        except Exception as e:
            logger.error(f"局部坐标系转换失败: {e}")
            return False
    def filter_roads_by_length(self, min_length: float = 1.0) -> int:
        if self.gdf is None:
            return 0
        original_count = len(self.gdf)
        self.gdf = self.gdf[self.gdf.geometry.length >= min_length]
        filtered_count = len(self.gdf)
        logger.info(f"长度过滤: {original_count} -> {filtered_count} 条道路")
        return filtered_count
    def extract_roads_data(self) -> List[Dict]:
        return self.extract_road_geometries()
    def get_sample_data(self, n: int = 5) -> List[Dict]:
        if not self.roads_data:
            self.extract_road_geometries()
        return self.roads_data[:n]
    def read_features(self) -> List[Dict]:
        if not self.load_shapefile():
            logger.error("无法加载shapefile文件")
            return []
        self.convert_to_utm()
        roads = self.extract_road_geometries()
        logger.info(f"成功读取 {len(roads)} 个道路特征")
        return roads
    def get_bounds(self) -> Dict[str, float]:
        if self.gdf is None:
            if not self.load_shapefile():
                return {'minX': 0, 'minY': 0, 'maxX': 0, 'maxY': 0}
        bounds = self.gdf.total_bounds
        return {
            'minX': float(bounds[0]),
            'minY': float(bounds[1]),
            'maxX': float(bounds[2]),
            'maxY': float(bounds[3])
        }
    def get_center(self) -> Dict[str, float]:
        bounds = self.get_bounds()
        return {
            'x': (bounds['minX'] + bounds['maxX']) / 2,
            'y': (bounds['minY'] + bounds['maxY']) / 2
        }