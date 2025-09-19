"""Shapefile读取模块

用于读取和解析ArcGIS shapefile格式的道路数据，提取几何信息和属性数据。
"""

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point, MultiLineString
from typing import Dict, List, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ShapefileReader:
    """Shapefile读取器
    
    负责读取shapefile文件，解析道路几何和属性信息。
    """
    
    def __init__(self, shapefile_path: str):
        """初始化读取器
        
        Args:
            shapefile_path: shapefile文件路径
        """
        self.shapefile_path = shapefile_path
        self.gdf = None
        self.roads_data = []
        
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
        """提取道路几何信息
        
        Returns:
            List[Dict]: 每条道路的几何和属性信息
        """
        if self.gdf is None:
            logger.error("请先加载shapefile")
            return []
        
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