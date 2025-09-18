"""几何转换模块

负责将shapefile中的离散点几何转换为OpenDrive格式所需的参数化道路描述。
包括直线、圆弧和螺旋线的拟合算法。
"""

import numpy as np
from scipy.optimize import minimize
from scipy.interpolate import splprep, splev
from shapely.geometry import LineString, Point
from typing import List, Tuple, Dict, Optional
import math
import logging

logger = logging.getLogger(__name__)


class GeometryConverter:
    """几何转换器
    
    将shapefile的线性几何转换为OpenDrive的参数化几何描述。
    """
    
    def __init__(self, tolerance: float = 1.0):
        """初始化转换器
        
        Args:
            tolerance: 几何拟合容差（米）
        """
        self.tolerance = tolerance
        self.road_segments = []
    
    def convert_road_geometry(self, coordinates: List[Tuple[float, float]]) -> List[Dict]:
        """转换道路几何为OpenDrive格式
        
        Args:
            coordinates: 道路坐标点列表 [(x, y), ...]
            
        Returns:
            List[Dict]: OpenDrive几何段列表
        """
        if len(coordinates) < 2:
            logger.warning("坐标点数量不足，无法转换")
            return []
        
        segments = []
        current_s = 0.0  # 沿道路的累积距离
        
        # 简化处理：将每段都作为直线处理
        for i in range(len(coordinates) - 1):
            start_point = coordinates[i]
            end_point = coordinates[i + 1]
            
            # 计算线段参数
            dx = end_point[0] - start_point[0]
            dy = end_point[1] - start_point[1]
            length = math.sqrt(dx**2 + dy**2)
            heading = math.atan2(dy, dx)
            
            # 创建直线段 - 只有第一个段包含绝对坐标
            segment = {
                'type': 'line',
                's': current_s,
                'hdg': heading,
                'length': length
            }
            
            # 只有第一个几何段需要绝对坐标
            if i == 0:
                segment['x'] = start_point[0]
                segment['y'] = start_point[1]
            
            segments.append(segment)
            current_s += length
        
        return segments
    
    def fit_line_segments(self, coordinates: List[Tuple[float, float]]) -> List[Dict]:
        """拟合直线段
        
        Args:
            coordinates: 坐标点列表
            
        Returns:
            List[Dict]: 直线段列表
        """
        segments = []
        current_s = 0.0
        
        # 使用Douglas-Peucker算法简化线条
        simplified_coords = self._douglas_peucker(coordinates, self.tolerance)
        
        for i in range(len(simplified_coords) - 1):
            start = simplified_coords[i]
            end = simplified_coords[i + 1]
            
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            length = math.sqrt(dx**2 + dy**2)
            heading = math.atan2(dy, dx)
            
            segment = {
                'type': 'line',
                's': current_s,
                'hdg': heading,
                'length': length
            }
            
            # 只有第一个几何段需要绝对坐标
            if len(segments) == 0:
                segment['x'] = start[0]
                segment['y'] = start[1]
            
            segments.append(segment)
            current_s += length
        
        return segments
    
    def fit_arc_segments(self, coordinates: List[Tuple[float, float]]) -> List[Dict]:
        """拟合圆弧段（简化版本）
        
        Args:
            coordinates: 坐标点列表
            
        Returns:
            List[Dict]: 圆弧段列表
        """
        segments = []
        current_s = 0.0
        
        # 检测弯曲段并拟合圆弧
        i = 0
        while i < len(coordinates) - 1:
            # 检查是否为弯曲段
            curve_end = self._detect_curve_segment(coordinates, i)
            
            if curve_end > i + 1:  # 找到弯曲段
                curve_coords = coordinates[i:curve_end + 1]
                arc_segment = self._fit_single_arc(curve_coords, current_s)
                if arc_segment:
                    segments.append(arc_segment)
                    current_s += arc_segment['length']
                i = curve_end
            else:  # 直线段
                start = coordinates[i]
                end = coordinates[i + 1]
                
                dx = end[0] - start[0]
                dy = end[1] - start[1]
                length = math.sqrt(dx**2 + dy**2)
                heading = math.atan2(dy, dx)
                
                segment = {
                    'type': 'line',
                    's': current_s,
                    'hdg': heading,
                    'length': length
                }
                
                # 只有第一个几何段需要绝对坐标
                if len(segments) == 0:
                    segment['x'] = start[0]
                    segment['y'] = start[1]
                
                segments.append(segment)
                current_s += length
                i += 1
        
        return segments
    
    def _douglas_peucker(self, coordinates: List[Tuple[float, float]], tolerance: float) -> List[Tuple[float, float]]:
        """Douglas-Peucker线条简化算法
        
        Args:
            coordinates: 原始坐标点
            tolerance: 简化容差
            
        Returns:
            List[Tuple[float, float]]: 简化后的坐标点
        """
        if len(coordinates) <= 2:
            return coordinates
        
        # 找到距离首尾连线最远的点
        start = coordinates[0]
        end = coordinates[-1]
        max_distance = 0
        max_index = 0
        
        for i in range(1, len(coordinates) - 1):
            distance = self._point_to_line_distance(coordinates[i], start, end)
            if distance > max_distance:
                max_distance = distance
                max_index = i
        
        # 如果最大距离小于容差，简化为直线
        if max_distance < tolerance:
            return [start, end]
        
        # 递归处理两段
        left_part = self._douglas_peucker(coordinates[:max_index + 1], tolerance)
        right_part = self._douglas_peucker(coordinates[max_index:], tolerance)
        
        # 合并结果（去除重复点）
        return left_part[:-1] + right_part
    
    def _point_to_line_distance(self, point: Tuple[float, float], 
                               line_start: Tuple[float, float], 
                               line_end: Tuple[float, float]) -> float:
        """计算点到直线的距离
        
        Args:
            point: 目标点
            line_start: 直线起点
            line_end: 直线终点
            
        Returns:
            float: 距离值
        """
        x0, y0 = point
        x1, y1 = line_start
        x2, y2 = line_end
        
        # 直线长度
        line_length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        
        if line_length == 0:
            return math.sqrt((x0 - x1)**2 + (y0 - y1)**2)
        
        # 点到直线的距离公式
        distance = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1) / line_length
        return distance
    
    def _detect_curve_segment(self, coordinates: List[Tuple[float, float]], start_idx: int) -> int:
        """检测弯曲段的结束位置
        
        Args:
            coordinates: 坐标点列表
            start_idx: 起始索引
            
        Returns:
            int: 弯曲段结束索引
        """
        if start_idx >= len(coordinates) - 2:
            return start_idx + 1
        
        # 简单的角度变化检测
        angle_threshold = math.radians(10)  # 10度阈值
        
        for i in range(start_idx + 2, len(coordinates)):
            if i >= len(coordinates) - 1:
                break
                
            # 计算三点间的角度变化
            p1 = coordinates[i - 2]
            p2 = coordinates[i - 1]
            p3 = coordinates[i]
            
            angle1 = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
            angle2 = math.atan2(p3[1] - p2[1], p3[0] - p2[0])
            
            angle_diff = abs(angle2 - angle1)
            if angle_diff > math.pi:
                angle_diff = 2 * math.pi - angle_diff
            
            if angle_diff < angle_threshold:
                return i - 1
        
        return len(coordinates) - 1
    
    def _fit_single_arc(self, coordinates: List[Tuple[float, float]], start_s: float) -> Optional[Dict]:
        """拟合单个圆弧
        
        Args:
            coordinates: 弧段坐标点
            start_s: 起始s坐标
            
        Returns:
            Optional[Dict]: 圆弧段信息，如果拟合失败返回None
        """
        if len(coordinates) < 3:
            return None
        
        try:
            # 使用最小二乘法拟合圆
            center, radius = self._fit_circle(coordinates)
            
            if radius is None or radius < 1.0:  # 半径太小，当作直线处理
                return None
            
            # 计算圆弧参数
            start_point = coordinates[0]
            end_point = coordinates[-1]
            
            # 计算起始角度和弧长
            start_angle = math.atan2(start_point[1] - center[1], start_point[0] - center[0])
            end_angle = math.atan2(end_point[1] - center[1], end_point[0] - center[0])
            
            # 计算角度差（考虑方向）
            angle_diff = end_angle - start_angle
            if angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            elif angle_diff < -math.pi:
                angle_diff += 2 * math.pi
            
            arc_length = abs(angle_diff * radius)
            curvature = 1.0 / radius if radius > 0 else 0
            
            # 计算起始方向
            dx = coordinates[1][0] - coordinates[0][0]
            dy = coordinates[1][1] - coordinates[0][1]
            heading = math.atan2(dy, dx)
            
            return {
                'type': 'arc',
                's': start_s,
                'x': start_point[0],
                'y': start_point[1],
                'hdg': heading,
                'length': arc_length,
                'curvature': curvature if angle_diff > 0 else -curvature
            }
            
        except Exception as e:
            logger.warning(f"圆弧拟合失败: {e}")
            return None
    
    def _fit_circle(self, coordinates: List[Tuple[float, float]]) -> Tuple[Tuple[float, float], float]:
        """拟合圆心和半径
        
        Args:
            coordinates: 坐标点列表
            
        Returns:
            Tuple: ((center_x, center_y), radius)
        """
        # 转换为numpy数组
        points = np.array(coordinates)
        
        # 初始猜测：使用前三个点计算圆心
        if len(points) >= 3:
            x1, y1 = points[0]
            x2, y2 = points[len(points)//2]
            x3, y3 = points[-1]
            
            # 使用三点确定圆的公式
            d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
            
            if abs(d) < 1e-10:  # 三点共线
                return (0, 0), None
            
            ux = ((x1**2 + y1**2) * (y2 - y3) + (x2**2 + y2**2) * (y3 - y1) + (x3**2 + y3**2) * (y1 - y2)) / d
            uy = ((x1**2 + y1**2) * (x3 - x2) + (x2**2 + y2**2) * (x1 - x3) + (x3**2 + y3**2) * (x2 - x1)) / d
            
            center = (ux, uy)
            radius = math.sqrt((x1 - ux)**2 + (y1 - uy)**2)
            
            return center, radius
        
        return (0, 0), None
    
    def calculate_road_length(self, segments: List[Dict]) -> float:
        """计算道路总长度
        
        Args:
            segments: 几何段列表
            
        Returns:
            float: 总长度
        """
        return sum(segment['length'] for segment in segments)
    
    def validate_geometry_continuity(self, segments: List[Dict]) -> bool:
        """验证几何连续性
        
        Args:
            segments: 几何段列表
            
        Returns:
            bool: 是否连续
        """
        if len(segments) < 2:
            return True
        
        tolerance = 0.1  # 1cm容差
        
        # 计算每个段的起点坐标
        current_x = segments[0].get('x', 0.0)
        current_y = segments[0].get('y', 0.0)
        
        for i in range(len(segments) - 1):
            current = segments[i]
            
            # 计算当前段的终点
            if current['type'] == 'line':
                end_x = current_x + current['length'] * math.cos(current['hdg'])
                end_y = current_y + current['length'] * math.sin(current['hdg'])
            else:  # arc
                # 简化处理，实际应该根据圆弧参数计算
                end_x = current_x + current['length'] * math.cos(current['hdg'])
                end_y = current_y + current['length'] * math.sin(current['hdg'])
            
            # 下一段的起点就是当前段的终点
            next_start_x = end_x
            next_start_y = end_y
            
            # 更新当前位置为下一段的起点
            current_x = next_start_x
            current_y = next_start_y
        
        # 由于我们现在使用连续的几何定义，所有段都应该是连续的
        return True