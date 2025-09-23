"""Shapefile读取模块

用于读取和解析ArcGIS shapefile格式的道路数据，提取几何信息和属性数据。
"""

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point, MultiLineString
from typing import Dict, List, Tuple, Optional
import logging
import os

# 配置日志输出到文件
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'shp_to_opendrive.log')

# 只在没有配置过的情况下配置日志
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            # 如果需要同时在控制台显示，可以取消下面这行的注释
            # logging.StreamHandler()
        ]
    )

logger = logging.getLogger(__name__)


class ShapefileReader:
    """Shapefile读取器
    
    负责读取shapefile文件，解析道路几何和属性信息。
    专门处理Lane.shp格式，支持RoadID和Index属性的车道面构建。
    """
    
    def __init__(self, shapefile_path: str):
        """初始化读取器
        
        Args:
            shapefile_path: shapefile文件路径
        """
        self.shapefile_path = shapefile_path
        self.gdf = None
        self.roads_data = []
        self.lane_data = {}  # 存储按RoadID分组的车道数据
        
    def load_shapefile(self) -> bool:
        """加载shapefile文件
        
        Returns:
            bool: 加载是否成功
        """
        try:
            self.gdf = gpd.read_file(self.shapefile_path)
            logger.info(f"成功加载shapefile: {self.shapefile_path}")
            logger.info(f"包含 {len(self.gdf)} 条道路记录")
            logger.info(f"坐标系统: {self.gdf.crs}")
            return True
        except Exception as e:
            logger.error(f"加载shapefile失败: {e}")
            return False
    
    def get_road_info(self) -> Dict:
        """获取道路基本信息
        
        Returns:
            Dict: 包含道路数量、坐标系等基本信息
        """
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
        """提取道路几何信息（兼容旧版本）
        
        Returns:
            List[Dict]: 每条道路的几何和属性信息
        """
        if self.gdf is None:
            logger.error("请先加载shapefile")
            return []
        
        # 检查是否为Lane.shp格式
        if self._is_lane_shapefile():
            return self.extract_lane_geometries()
        
        # 原有的道路几何提取逻辑
        roads = []
        
        for idx, row in self.gdf.iterrows():
            geometry = row.geometry
            
            # 只处理线性几何
            if not isinstance(geometry, LineString):
                logger.warning(f"跳过非线性几何 (索引: {idx})")
                continue
            
            # 提取坐标点（确保只有X,Y坐标，忽略Z值）
            coords = [(coord[0], coord[1]) for coord in geometry.coords]
            
            # 构建道路信息
            road_info = {
                'id': idx,
                'geometry': geometry,
                'coordinates': coords,
                'length': geometry.length,
                'start_point': coords[0],
                'end_point': coords[-1],
                'attributes': {}
            }
            
            # 提取属性信息（排除几何列）
            for col in self.gdf.columns:
                if col != 'geometry':
                    road_info['attributes'][col] = row[col]
            
            roads.append(road_info)
        
        self.roads_data = roads
        logger.info(f"提取了 {len(roads)} 条有效道路")
        return roads
    
    def _is_lane_shapefile(self) -> bool:
        """检查是否为Lane.shp格式
        
        Returns:
            bool: 是否包含RoadID和Index字段
        """
        if self.gdf is None:
            return False
        
        columns = [col.upper() for col in self.gdf.columns]
        return 'ROADID' in columns and 'INDEX' in columns
    
    def extract_lane_geometries(self) -> List[Dict]:
        """提取Lane.shp格式的车道几何信息
        
        Returns:
            List[Dict]: 按RoadID分组的车道数据
        """
        if self.gdf is None:
            logger.error("请先加载shapefile")
            return []
        
        logger.info("检测到Lane.shp格式，开始提取车道数据")
        
        # 按RoadID分组
        grouped = self.gdf.groupby('RoadID')
        roads = []
        
        logger.info(f"开始处理 {len(grouped)} 个RoadID分组")
        
        for road_id, group in grouped:
            logger.info(f"\n=== 处理RoadID: {road_id} ===")
            logger.info(f"该RoadID包含 {len(group)} 条边界线记录")
            
            # 显示原始Index值
            original_indices = group['Index'].tolist()
            logger.info(f"原始Index值: {original_indices}")
            
            # 按Index排序（将字符串转换为整数进行排序）
            try:
                # 尝试将Index转换为整数进行排序
                group_sorted = group.sort_values('Index', key=lambda x: x.astype(int))
            except (ValueError, TypeError):
                # 如果转换失败，使用字符串排序
                logger.warning(f"RoadID {road_id} 的Index无法转换为整数，使用字符串排序")
                group_sorted = group.sort_values('Index')
            
            sorted_indices = group_sorted['Index'].tolist()
            logger.info(f"排序后Index值: {sorted_indices}")
            
            # 处理车道边界线
            boundary_lines = []
            for idx, row in group_sorted.iterrows():
                geometry = row.geometry
                
                # 处理线性几何（车道边界线）
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
                    
                    # 提取所有属性
                    for col in self.gdf.columns:
                        if col != 'geometry':
                            boundary_info['attributes'][col] = row[col]
                    
                    boundary_lines.append(boundary_info)
                    logger.info(f"  添加边界线 Index={row['Index']}, 长度={geometry.length:.2f}m, 坐标点数={len(coords)}")
                else:
                    logger.warning(f"跳过非线性几何 (RoadID: {road_id}, Index: {row['Index']})")
            
            logger.info(f"RoadID {road_id} 共处理了 {len(boundary_lines)} 条边界线")
            
            # 构建车道面（从边界线组合）
            lanes = self._build_lanes_from_boundaries(boundary_lines)
            logger.info(f"RoadID {road_id} 构建了 {len(lanes)} 个车道面")
            
            # 构建道路信息
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
        """从边界线构建车道面
        
        Args:
            boundary_lines: 边界线列表
            
        Returns:
            List[Dict]: 车道面列表
        """
        lanes = []
        
        logger.info(f"  开始构建车道面，输入边界线数量: {len(boundary_lines)}")
        
        # 按Index排序确保正确的相邻关系
        boundaries_sorted = sorted(boundary_lines, key=lambda x: x['index'])
        sorted_indices = [b['index'] for b in boundaries_sorted]
        logger.info(f"  边界线排序后Index顺序: {sorted_indices}")
        
        # 相邻的边界线组合成车道面
        for i in range(len(boundaries_sorted) - 1):
            left_boundary = boundaries_sorted[i]
            right_boundary = boundaries_sorted[i + 1]
            
            surface_id = f"{left_boundary['index']}_{right_boundary['index']}"
            logger.info(f"    构建车道面 {surface_id}: 左边界Index={left_boundary['index']}, 右边界Index={right_boundary['index']}")
            
            # 构建车道面
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
        """构建车道面（兼容旧接口）
        
        Args:
            lanes: 车道列表
            
        Returns:
            List[Dict]: 车道面列表
        """
        # 直接返回lanes，因为现在lanes就是车道面
        return lanes
    
    def get_road_attributes_mapping(self) -> Dict[str, str]:
        """获取道路属性字段映射建议
        
        Returns:
            Dict: 属性字段到OpenDrive属性的映射建议
        """
        if self.gdf is None:
            return {}
        
        # 常见的属性字段映射
        mapping_suggestions = {}
        columns = [col.lower() for col in self.gdf.columns if col != 'geometry']
        
        # 道路类型相关
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
        """计算两条边界线之间的中心线
        
        Args:
            left_coords: 左边界坐标
            right_coords: 右边界坐标
            
        Returns:
            List[tuple]: 中心线坐标
        """
        # 确保两条线有相同的点数，如果不同则插值
        if len(left_coords) != len(right_coords):
            # 简单处理：取较少的点数
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
        """计算车道宽度轮廓
        
        Args:
            left_coords: 左边界坐标
            right_coords: 右边界坐标
            
        Returns:
            List[float]: 各点处的车道宽度
        """
        import math
        
        # 确保两条线有相同的点数
        if len(left_coords) != len(right_coords):
            min_len = min(len(left_coords), len(right_coords))
            left_coords = left_coords[:min_len]
            right_coords = right_coords[:min_len]
        
        widths = []
        for left_pt, right_pt in zip(left_coords, right_coords):
            width = math.sqrt((left_pt[0] - right_pt[0])**2 + (left_pt[1] - right_pt[1])**2)
            widths.append(width)
        
        return widths
    
    def _merge_boundary_attributes(self, left_attrs: Dict, right_attrs: Dict) -> Dict:
        """合并边界线属性
        
        Args:
            left_attrs: 左边界属性
            right_attrs: 右边界属性
            
        Returns:
            Dict: 合并后的属性
        """
        merged = {}
        
        # 优先使用左边界的属性
        merged.update(left_attrs)
        
        # 如果右边界有而左边界没有的属性，则添加
        for key, value in right_attrs.items():
            if key not in merged:
                merged[key] = value
        
        return merged
    
    def convert_to_utm(self) -> bool:
        """转换坐标系到UTM（如果需要）
        
        Returns:
            bool: 转换是否成功
        """
        if self.gdf is None:
            return False
        
        try:
            # 如果不是投影坐标系，转换为UTM
            if self.gdf.crs.is_geographic:
                # 根据数据范围自动选择UTM区域
                bounds = self.gdf.total_bounds
                center_lon = (bounds[0] + bounds[2]) / 2
                
                # 计算UTM区域
                utm_zone = int((center_lon + 180) / 6) + 1
                
                # 判断南北半球
                center_lat = (bounds[1] + bounds[3]) / 2
                hemisphere = 'north' if center_lat >= 0 else 'south'
                
                # 构建UTM CRS
                utm_crs = f"EPSG:{32600 + utm_zone if hemisphere == 'north' else 32700 + utm_zone}"
                
                # 保存原始坐标系信息
                original_crs = self.gdf.crs
                logger.info(f"原始坐标系: {original_crs}")
                
                # 转换坐标系
                self.gdf = self.gdf.to_crs(utm_crs)
                logger.info(f"坐标系已转换为: {utm_crs}")
                
                # 记录转换后的坐标范围
                new_bounds = self.gdf.total_bounds
                logger.info(f"转换后坐标范围: X[{new_bounds[0]:.2f}, {new_bounds[2]:.2f}], Y[{new_bounds[1]:.2f}, {new_bounds[3]:.2f}]")
            else:
                logger.info(f"当前坐标系已是投影坐标系: {self.gdf.crs}")
            
            return True
        except Exception as e:
            logger.error(f"坐标系转换失败: {e}")
            return False
    
    def convert_to_local_coordinates(self) -> bool:
        """将坐标转换为局部坐标系（以数据范围的最小点为原点）
        
        Returns:
            bool: 转换是否成功
        """
        if self.gdf is None:
            return False
        
        try:
            # 获取数据边界
            bounds = self.gdf.total_bounds
            min_x, min_y = bounds[0], bounds[1]
            
            logger.info(f"原点设置为: ({min_x:.2f}, {min_y:.2f})")
            
            # 转换几何体坐标
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
            
            # 应用坐标转换
            self.gdf['geometry'] = self.gdf['geometry'].apply(translate_geometry)
            
            # 记录转换后的坐标范围
            new_bounds = self.gdf.total_bounds
            logger.info(f"局部坐标系范围: X[{new_bounds[0]:.2f}, {new_bounds[2]:.2f}], Y[{new_bounds[1]:.2f}, {new_bounds[3]:.2f}]")
            
            return True
        except Exception as e:
            logger.error(f"局部坐标系转换失败: {e}")
            return False
    
    def filter_roads_by_length(self, min_length: float = 1.0) -> int:
        """根据长度过滤道路
        
        Args:
            min_length: 最小道路长度（米），默认1.0米以保留更多短线段
            
        Returns:
            int: 过滤后剩余的道路数量
        """
        if self.gdf is None:
            return 0
        
        original_count = len(self.gdf)
        self.gdf = self.gdf[self.gdf.geometry.length >= min_length]
        filtered_count = len(self.gdf)
        
        logger.info(f"长度过滤: {original_count} -> {filtered_count} 条道路")
        return filtered_count
    
    def extract_roads_data(self) -> List[Dict]:
        """提取道路数据（兼容性方法）
        
        Returns:
            List[Dict]: 道路数据列表
        """
        return self.extract_road_geometries()
    
    def get_sample_data(self, n: int = 5) -> List[Dict]:
        """获取样本数据用于调试
        
        Args:
            n: 样本数量
            
        Returns:
            List[Dict]: 样本道路数据
        """
        if not self.roads_data:
            self.extract_road_geometries()
        
        return self.roads_data[:n]
    
    def read_features(self) -> List[Dict]:
        """读取所有道路特征
        
        Returns:
            List[Dict]: 道路特征列表，每个特征包含几何和属性信息
        """
        if not self.load_shapefile():
            logger.error("无法加载shapefile文件")
            return []
        
        # 转换坐标系（如果需要）
        self.convert_to_utm()
        
        # 提取道路几何
        roads = self.extract_road_geometries()
        
        logger.info(f"成功读取 {len(roads)} 个道路特征")
        return roads