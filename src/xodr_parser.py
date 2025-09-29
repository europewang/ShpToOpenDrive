#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenDRIVE文件解析器
用于解析和提取OpenDRIVE文件中的几何信息

作者: ShpToOpenDrive项目组
版本: 1.3.0
"""

import xml.etree.ElementTree as ET
import numpy as np
from typing import List, Dict, Tuple, Optional
import math


class XODRParser:
    """
    OpenDRIVE文件解析器
    解析XODR文件并提取道路几何信息
    """
    
    def __init__(self):
        """
        初始化解析器
        """
        self.roads = []
        self.junctions = []
        self.header = {}
        
    def parse_file(self, file_path: str) -> Dict:
        """
        解析OpenDRIVE文件
        
        Args:
            file_path: XODR文件路径
            
        Returns:
            解析后的数据字典
        """
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # 解析头部信息
            self._parse_header(root)
            
            # 解析道路信息
            self._parse_roads(root)
            
            # 解析交叉口信息
            self._parse_junctions(root)
            
            return {
                'header': self.header,
                'roads': self.roads,
                'junctions': self.junctions
            }
            
        except ET.ParseError as e:
            raise ValueError(f"XML解析错误: {str(e)}")
        except Exception as e:
            raise ValueError(f"文件解析失败: {str(e)}")
    
    def _parse_header(self, root: ET.Element):
        """
        解析头部信息
        
        Args:
            root: XML根元素
        """
        header_elem = root.find('header')
        if header_elem is not None:
            self.header = {
                'revMajor': header_elem.get('revMajor', '1'),
                'revMinor': header_elem.get('revMinor', '4'),
                'name': header_elem.get('name', ''),
                'version': header_elem.get('version', '1.0'),
                'date': header_elem.get('date', ''),
                'north': float(header_elem.get('north', '0')),
                'south': float(header_elem.get('south', '0')),
                'east': float(header_elem.get('east', '0')),
                'west': float(header_elem.get('west', '0'))
            }
    
    def _parse_roads(self, root: ET.Element):
        """
        解析道路信息
        
        Args:
            root: XML根元素
        """
        self.roads = []
        
        for road_elem in root.findall('road'):
            road_data = {
                'id': road_elem.get('id'),
                'name': road_elem.get('name', ''),
                'length': float(road_elem.get('length', '0')),
                'junction': road_elem.get('junction', '-1'),
                'planView': [],
                'elevationProfile': [],
                'lateralProfile': [],
                'lanes': []
            }
            
            # 解析平面视图
            self._parse_plan_view(road_elem, road_data)
            
            # 解析高程剖面
            self._parse_elevation_profile(road_elem, road_data)
            
            # 解析车道信息
            self._parse_lanes(road_elem, road_data)
            
            self.roads.append(road_data)
    
    def _parse_plan_view(self, road_elem: ET.Element, road_data: Dict):
        """
        解析平面视图几何
        
        Args:
            road_elem: 道路XML元素
            road_data: 道路数据字典
        """
        plan_view = road_elem.find('planView')
        if plan_view is not None:
            for geometry_elem in plan_view.findall('geometry'):
                geom_data = {
                    's': float(geometry_elem.get('s', '0')),
                    'x': float(geometry_elem.get('x', '0')),
                    'y': float(geometry_elem.get('y', '0')),
                    'hdg': float(geometry_elem.get('hdg', '0')),
                    'length': float(geometry_elem.get('length', '0')),
                    'type': None,
                    'params': {}
                }
                
                # 检查几何类型
                line_elem = geometry_elem.find('line')
                arc_elem = geometry_elem.find('arc')
                spiral_elem = geometry_elem.find('spiral')
                poly3_elem = geometry_elem.find('poly3')
                
                if line_elem is not None:
                    geom_data['type'] = 'line'
                elif arc_elem is not None:
                    geom_data['type'] = 'arc'
                    geom_data['params']['curvature'] = float(arc_elem.get('curvature', '0'))
                elif spiral_elem is not None:
                    geom_data['type'] = 'spiral'
                    geom_data['params']['curvStart'] = float(spiral_elem.get('curvStart', '0'))
                    geom_data['params']['curvEnd'] = float(spiral_elem.get('curvEnd', '0'))
                elif poly3_elem is not None:
                    geom_data['type'] = 'poly3'
                    geom_data['params']['a'] = float(poly3_elem.get('a', '0'))
                    geom_data['params']['b'] = float(poly3_elem.get('b', '0'))
                    geom_data['params']['c'] = float(poly3_elem.get('c', '0'))
                    geom_data['params']['d'] = float(poly3_elem.get('d', '0'))
                
                road_data['planView'].append(geom_data)
    
    def _parse_elevation_profile(self, road_elem: ET.Element, road_data: Dict):
        """
        解析高程剖面
        
        Args:
            road_elem: 道路XML元素
            road_data: 道路数据字典
        """
        elevation_profile = road_elem.find('elevationProfile')
        if elevation_profile is not None:
            for elevation_elem in elevation_profile.findall('elevation'):
                elev_data = {
                    's': float(elevation_elem.get('s', '0')),
                    'a': float(elevation_elem.get('a', '0')),
                    'b': float(elevation_elem.get('b', '0')),
                    'c': float(elevation_elem.get('c', '0')),
                    'd': float(elevation_elem.get('d', '0'))
                }
                road_data['elevationProfile'].append(elev_data)
    
    def _parse_lanes(self, road_elem: ET.Element, road_data: Dict):
        """
        解析车道信息
        
        Args:
            road_elem: 道路XML元素
            road_data: 道路数据字典
        """
        lanes_elem = road_elem.find('lanes')
        if lanes_elem is not None:
            for lane_section in lanes_elem.findall('laneSection'):
                section_data = {
                    's': float(lane_section.get('s', '0')),
                    'left': [],
                    'center': [],
                    'right': []
                }
                
                # 解析左侧车道
                left_elem = lane_section.find('left')
                if left_elem is not None:
                    for lane in left_elem.findall('lane'):
                        section_data['left'].append(self._parse_lane(lane))
                
                # 解析中心车道
                center_elem = lane_section.find('center')
                if center_elem is not None:
                    for lane in center_elem.findall('lane'):
                        section_data['center'].append(self._parse_lane(lane))
                
                # 解析右侧车道
                right_elem = lane_section.find('right')
                if right_elem is not None:
                    for lane in right_elem.findall('lane'):
                        section_data['right'].append(self._parse_lane(lane))
                
                road_data['lanes'].append(section_data)
    
    def _parse_lane(self, lane_elem: ET.Element) -> Dict:
        """
        解析单个车道信息
        
        Args:
            lane_elem: 车道XML元素
            
        Returns:
            车道数据字典
        """
        lane_data = {
            'id': int(lane_elem.get('id', '0')),
            'type': lane_elem.get('type', 'driving'),
            'level': lane_elem.get('level', 'false') == 'true',
            'width': []
        }
        
        # 解析车道宽度
        for width_elem in lane_elem.findall('width'):
            width_data = {
                'sOffset': float(width_elem.get('sOffset', '0')),
                'a': float(width_elem.get('a', '0')),
                'b': float(width_elem.get('b', '0')),
                'c': float(width_elem.get('c', '0')),
                'd': float(width_elem.get('d', '0'))
            }
            lane_data['width'].append(width_data)
        
        return lane_data
    
    def _parse_junctions(self, root: ET.Element):
        """
        解析交叉口信息
        
        Args:
            root: XML根元素
        """
        self.junctions = []
        
        for junction_elem in root.findall('junction'):
            junction_data = {
                'id': junction_elem.get('id'),
                'name': junction_elem.get('name', ''),
                'connections': []
            }
            
            # 解析连接信息
            for connection_elem in junction_elem.findall('connection'):
                connection_data = {
                    'id': connection_elem.get('id'),
                    'incomingRoad': connection_elem.get('incomingRoad'),
                    'connectingRoad': connection_elem.get('connectingRoad'),
                    'contactPoint': connection_elem.get('contactPoint'),
                    'laneLinks': []
                }
                
                # 解析车道链接
                for lane_link in connection_elem.findall('laneLink'):
                    link_data = {
                        'from': int(lane_link.get('from', '0')),
                        'to': int(lane_link.get('to', '0'))
                    }
                    connection_data['laneLinks'].append(link_data)
                
                junction_data['connections'].append(connection_data)
            
            self.junctions.append(junction_data)
    
    def generate_road_points(self, road_data: Dict, resolution: float = 1.0) -> List[Tuple[float, float, float]]:
        """
        根据道路几何生成3D点序列
        
        Args:
            road_data: 道路数据
            resolution: 采样分辨率（米）
            
        Returns:
            3D点列表 [(x, y, z), ...]
        """
        points = []
        
        for geometry in road_data['planView']:
            geom_points = self._generate_geometry_points(geometry, resolution)
            points.extend(geom_points)
        
        return points
    
    def _generate_geometry_points(self, geometry: Dict, resolution: float) -> List[Tuple[float, float, float]]:
        """
        根据几何类型生成点序列
        
        Args:
            geometry: 几何数据
            resolution: 采样分辨率
            
        Returns:
            3D点列表
        """
        points = []
        length = geometry['length']
        num_points = max(2, int(length / resolution) + 1)
        
        x0, y0 = geometry['x'], geometry['y']
        hdg = geometry['hdg']
        
        for i in range(num_points):
            s = (i / (num_points - 1)) * length
            
            if geometry['type'] == 'line':
                x = x0 + s * math.cos(hdg)
                y = y0 + s * math.sin(hdg)
            elif geometry['type'] == 'arc':
                curvature = geometry['params']['curvature']
                if abs(curvature) > 1e-10:
                    radius = 1.0 / curvature
                    angle = s * curvature
                    x = x0 + radius * (math.sin(hdg + angle) - math.sin(hdg))
                    y = y0 - radius * (math.cos(hdg + angle) - math.cos(hdg))
                else:
                    x = x0 + s * math.cos(hdg)
                    y = y0 + s * math.sin(hdg)
            else:
                # 对于复杂几何类型，使用线性近似
                x = x0 + s * math.cos(hdg)
                y = y0 + s * math.sin(hdg)
            
            # 计算高程（简化处理）
            z = 0.0
            
            points.append((x, y, z))
        
        return points
    
    def get_road_center_lines(self, resolution: float = 1.0) -> Dict[str, Dict]:
        """
        获取所有道路的中心线点序列
        
        Args:
            resolution: 采样分辨率（米）
            
        Returns:
            道路中心线字典，键为道路ID，值包含坐标和长度信息
        """
        center_lines = {}
        
        for road in self.roads:
            if road['planView']:  # 确保有几何数据
                points = self.generate_road_points(road, resolution)
                if points:
                    center_lines[road['id']] = {
                        'coordinates': points,
                        'length': road['length']
                    }
        
        return center_lines
    
    def get_statistics(self) -> Dict:
        """
        获取解析统计信息
        
        Returns:
            统计信息字典
        """
        total_length = sum(road['length'] for road in self.roads)
        
        geometry_types = {}
        for road in self.roads:
            for geom in road['planView']:
                geom_type = geom['type']
                geometry_types[geom_type] = geometry_types.get(geom_type, 0) + 1
        
        return {
            'roads_count': len(self.roads),
            'junctions_count': len(self.junctions),
            'total_length': total_length,
            'geometry_types': geometry_types,
            'header': self.header
        }


def main():
    """
    测试函数
    """
    import sys
    
    if len(sys.argv) != 2:
        print("用法: python xodr_parser.py <xodr_file>")
        return
    
    parser = XODRParser()
    try:
        data = parser.parse_file(sys.argv[1])
        stats = parser.get_statistics()
        
        print("OpenDRIVE文件解析完成:")
        print(f"道路数量: {stats['roads_count']}")
        print(f"交叉口数量: {stats['junctions_count']}")
        print(f"总长度: {stats['total_length']:.2f}米")
        print(f"几何类型: {stats['geometry_types']}")
        
        # 生成中心线
        center_lines = parser.get_road_center_lines()
        print(f"生成中心线数量: {len(center_lines)}")
        
    except Exception as e:
        print(f"解析失败: {str(e)}")


if __name__ == "__main__":
    main()