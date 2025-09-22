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
from scipy import interpolate
from scipy.optimize import minimize_scalar

logger = logging.getLogger(__name__)


class GeometryConverter:
    """几何转换器
    
    将shapefile的线性几何转换为OpenDrive的参数化几何描述。
    支持单一道路中心线和变宽车道面的转换。
    """
    
    def __init__(self, tolerance: float = 1.0, smooth_curves: bool = True, preserve_detail: bool = True):
        """初始化转换器
        
        Args:
            tolerance: 几何拟合容差（米）
            smooth_curves: 是否启用平滑曲线拟合
            preserve_detail: 是否保留更多细节（减少简化）
        """
        self.tolerance = tolerance
        self.smooth_curves = smooth_curves
        self.preserve_detail = preserve_detail
        # 如果启用细节保留，使用更小的容差
        if preserve_detail:
            self.effective_tolerance = tolerance * 0.3
        else:
            self.effective_tolerance = tolerance
        self.road_segments = []
        logger.info(f"几何转换器初始化，容差: {tolerance}m, 平滑曲线: {smooth_curves}, 保留细节: {preserve_detail}")
    
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
        
        # 根据配置选择转换方法
        if self.smooth_curves and len(coordinates) >= 3:
            # 使用平滑曲线拟合
            return self.fit_smooth_curve_segments(coordinates)
        else:
            # 使用传统的直线段拟合
            return self.fit_line_segments(coordinates)
    
    def fit_smooth_curve_segments(self, coordinates: List[Tuple[float, float]]) -> List[Dict]:
        """使用样条插值拟合平滑曲线段
        
        Args:
            coordinates: 坐标点列表
            
        Returns:
            List[Dict]: 平滑曲线段列表
        """
        if len(coordinates) < 3:
            return self.fit_line_segments(coordinates)
        
        segments = []
        current_s = 0.0
        
        # 使用改进的Douglas-Peucker算法，保留更多细节
        if self.preserve_detail:
            simplified_coords = self._adaptive_simplify(coordinates)
        else:
            simplified_coords = self._douglas_peucker(coordinates, self.effective_tolerance)
        
        # 如果启用平滑曲线，使用样条插值
        if self.smooth_curves and len(simplified_coords) >= 4:
            smooth_coords = self._spline_interpolation(simplified_coords)
            segments = self._fit_curve_segments_from_smooth(smooth_coords, current_s)
        else:
            # 使用改进的直线段拟合
            segments = self._fit_adaptive_line_segments(simplified_coords, current_s)
        
        return segments
    
    def _adaptive_simplify(self, coordinates: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """自适应简化算法，根据曲率变化调整简化程度
        
        Args:
            coordinates: 原始坐标点
            
        Returns:
            List[Tuple[float, float]]: 简化后的坐标点
        """
        if len(coordinates) <= 3:
            return coordinates
        
        result = [coordinates[0]]
        
        for i in range(1, len(coordinates) - 1):
            # 计算当前点的曲率
            curvature = self._calculate_curvature(coordinates[i-1], coordinates[i], coordinates[i+1])
            
            # 根据曲率调整容差
            adaptive_tolerance = self.effective_tolerance
            if curvature > 0.1:  # 高曲率区域
                adaptive_tolerance *= 0.5
            elif curvature < 0.01:  # 低曲率区域
                adaptive_tolerance *= 2.0
            
            # 检查是否需要保留此点
            if len(result) >= 2:
                distance = self._point_to_line_distance(coordinates[i], result[-2], coordinates[-1])
                if distance > adaptive_tolerance:
                    result.append(coordinates[i])
            else:
                result.append(coordinates[i])
        
        result.append(coordinates[-1])
        return result
    
    def _calculate_curvature(self, p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float]) -> float:
        """计算三点间的曲率
        
        Args:
            p1, p2, p3: 三个连续点
            
        Returns:
            float: 曲率值
        """
        # 计算向量
        v1 = (p2[0] - p1[0], p2[1] - p1[1])
        v2 = (p3[0] - p2[0], p3[1] - p2[1])
        
        # 计算长度
        len1 = math.sqrt(v1[0]**2 + v1[1]**2)
        len2 = math.sqrt(v2[0]**2 + v2[1]**2)
        
        if len1 == 0 or len2 == 0:
            return 0.0
        
        # 计算角度变化
        dot_product = v1[0] * v2[0] + v1[1] * v2[1]
        cross_product = v1[0] * v2[1] - v1[1] * v2[0]
        
        angle = math.atan2(abs(cross_product), dot_product)
        
        # 曲率 = 角度变化 / 平均弧长
        avg_length = (len1 + len2) / 2
        return angle / avg_length if avg_length > 0 else 0.0
    
    def _spline_interpolation(self, coordinates: List[Tuple[float, float]], num_points: int = None) -> List[Tuple[float, float]]:
        """使用样条插值生成平滑曲线
        
        Args:
            coordinates: 控制点坐标
            num_points: 插值点数量，默认为原点数的2倍
            
        Returns:
            List[Tuple[float, float]]: 插值后的平滑坐标点
        """
        if len(coordinates) < 4:
            return coordinates
        
        try:
            # 提取x和y坐标
            x_coords = [p[0] for p in coordinates]
            y_coords = [p[1] for p in coordinates]
            
            # 计算累积距离作为参数
            distances = [0]
            for i in range(1, len(coordinates)):
                dist = math.sqrt((x_coords[i] - x_coords[i-1])**2 + (y_coords[i] - y_coords[i-1])**2)
                distances.append(distances[-1] + dist)
            
            # 创建样条插值
            if num_points is None:
                num_points = len(coordinates) * 2
            
            # 使用三次样条插值
            t_new = np.linspace(0, distances[-1], num_points)
            
            # 确保有足够的点进行三次样条插值
            if len(coordinates) >= 4:
                spline_x = interpolate.interp1d(distances, x_coords, kind='cubic', bounds_error=False, fill_value='extrapolate')
                spline_y = interpolate.interp1d(distances, y_coords, kind='cubic', bounds_error=False, fill_value='extrapolate')
            else:
                spline_x = interpolate.interp1d(distances, x_coords, kind='linear')
                spline_y = interpolate.interp1d(distances, y_coords, kind='linear')
            
            x_smooth = spline_x(t_new)
            y_smooth = spline_y(t_new)
            
            return list(zip(x_smooth, y_smooth))
            
        except Exception as e:
            logger.warning(f"样条插值失败，使用原始坐标: {e}")
            return coordinates
    
    def _fit_curve_segments_from_smooth(self, smooth_coords: List[Tuple[float, float]], start_s: float = 0.0) -> List[Dict]:
        """从平滑坐标生成曲线段
        
        Args:
            smooth_coords: 平滑后的坐标点
            start_s: 起始s坐标
            
        Returns:
            List[Dict]: 曲线段列表
        """
        segments = []
        current_s = start_s
        
        # 检测曲线段和直线段
        i = 0
        while i < len(smooth_coords) - 1:
            # 检测当前段是否为曲线
            curve_end = self._detect_smooth_curve_segment(smooth_coords, i)
            
            if curve_end > i + 2:  # 找到曲线段
                curve_coords = smooth_coords[i:curve_end + 1]
                arc_segment = self._fit_smooth_arc(curve_coords, current_s)
                
                if arc_segment:
                    segments.append(arc_segment)
                    current_s += arc_segment['length']
                    i = curve_end
                else:
                    # 曲线拟合失败，使用直线段
                    line_segment = self._create_line_segment(smooth_coords[i], smooth_coords[i + 1], current_s, i == 0)
                    segments.append(line_segment)
                    current_s += line_segment['length']
                    i += 1
            else:
                # 直线段
                line_segment = self._create_line_segment(smooth_coords[i], smooth_coords[i + 1], current_s, i == 0)
                segments.append(line_segment)
                current_s += line_segment['length']
                i += 1
        
        return segments
    
    def _detect_smooth_curve_segment(self, coordinates: List[Tuple[float, float]], start_idx: int) -> int:
        """检测平滑曲线段的结束位置
        
        Args:
            coordinates: 坐标点列表
            start_idx: 起始索引
            
        Returns:
            int: 曲线段结束索引
        """
        if start_idx >= len(coordinates) - 2:
            return start_idx + 1
        
        curve_threshold = 0.05  # 曲率阈值
        min_curve_points = 3
        max_curve_points = min(20, len(coordinates) - start_idx)
        
        curve_points = 0
        
        for i in range(start_idx + 1, min(start_idx + max_curve_points, len(coordinates) - 1)):
            if i + 1 < len(coordinates):
                curvature = self._calculate_curvature(coordinates[i-1], coordinates[i], coordinates[i+1])
                
                if curvature > curve_threshold:
                    curve_points += 1
                else:
                    # 如果已经有足够的曲线点，结束检测
                    if curve_points >= min_curve_points:
                        return i
                    # 否则重置计数
                    curve_points = 0
        
        # 如果到达末尾且有足够的曲线点
        if curve_points >= min_curve_points:
            return min(start_idx + max_curve_points - 1, len(coordinates) - 1)
        
        return start_idx + 1
    
    def _fit_smooth_arc(self, coordinates: List[Tuple[float, float]], start_s: float) -> Optional[Dict]:
        """拟合平滑圆弧段
        
        Args:
            coordinates: 曲线坐标点
            start_s: 起始s坐标
            
        Returns:
            Optional[Dict]: 圆弧段信息或None
        """
        if len(coordinates) < 3:
            return None
        
        try:
            # 使用最小二乘法拟合圆
            center, radius = self._fit_circle(coordinates)
            
            if radius < 10 or radius > 10000:  # 半径合理性检查
                return None
            
            # 计算起始和结束角度
            start_point = coordinates[0]
            end_point = coordinates[-1]
            
            start_angle = math.atan2(start_point[1] - center[1], start_point[0] - center[0])
            end_angle = math.atan2(end_point[1] - center[1], end_point[0] - center[0])
            
            # 计算角度差（考虑方向）
            angle_diff = end_angle - start_angle
            
            # 标准化角度差到[-π, π]
            while angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            while angle_diff < -math.pi:
                angle_diff += 2 * math.pi
            
            # 计算弧长
            arc_length = abs(angle_diff) * radius
            
            # 计算曲率（带符号）
            curvature = angle_diff / arc_length if arc_length > 0 else 0
            
            # 计算起始方向
            dx = coordinates[1][0] - coordinates[0][0]
            dy = coordinates[1][1] - coordinates[0][1]
            heading = math.atan2(dy, dx)
            
            segment = {
                'type': 'arc',
                's': start_s,
                'hdg': heading,
                'length': arc_length,
                'curvature': curvature
            }
            
            # 只有第一个几何段需要绝对坐标
            if start_s == 0:
                segment['x'] = start_point[0]
                segment['y'] = start_point[1]
            
            return segment
            
        except Exception as e:
            logger.debug(f"圆弧拟合失败: {e}")
            return None
    
    def _fit_adaptive_line_segments(self, coordinates: List[Tuple[float, float]], start_s: float = 0.0) -> List[Dict]:
        """自适应直线段拟合
        
        Args:
            coordinates: 坐标点列表
            start_s: 起始s坐标
            
        Returns:
            List[Dict]: 直线段列表
        """
        segments = []
        current_s = start_s
        
        for i in range(len(coordinates) - 1):
            segment = self._create_line_segment(coordinates[i], coordinates[i + 1], current_s, i == 0)
            segments.append(segment)
            current_s += segment['length']
        
        return segments
    
    def _create_line_segment(self, start_point: Tuple[float, float], end_point: Tuple[float, float], 
                           s_coord: float, include_xy: bool = False) -> Dict:
        """创建直线段
        
        Args:
            start_point: 起始点
            end_point: 结束点
            s_coord: s坐标
            include_xy: 是否包含绝对坐标
            
        Returns:
            Dict: 直线段信息
        """
        dx = end_point[0] - start_point[0]
        dy = end_point[1] - start_point[1]
        length = math.sqrt(dx**2 + dy**2)
        heading = math.atan2(dy, dx)
        
        segment = {
            'type': 'line',
            's': s_coord,
            'hdg': heading,
            'length': length
        }
        
        if include_xy:
            segment['x'] = start_point[0]
            segment['y'] = start_point[1]
        
        return segment
    
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
    
    def convert_lane_surface_geometry(self, lane_surfaces: List[Dict]) -> List[Dict]:
        """转换车道面几何为OpenDrive格式
        
        Args:
            lane_surfaces: 车道面数据列表，每个包含left_boundary和right_boundary
            
        Returns:
            List[Dict]: 转换后的车道面几何数据
        """
        converted_surfaces = []
        
        for surface in lane_surfaces:
            try:
                # 获取左右边界坐标
                left_coords = surface['left_boundary']['coordinates']
                right_coords = surface['right_boundary']['coordinates']
                
                # 计算中心线坐标
                center_coords = self._calculate_center_line(left_coords, right_coords)
                
                # 转换中心线几何
                center_segments = self.convert_road_geometry(center_coords)
                
                # 计算车道宽度变化
                width_profile = self._calculate_width_profile(left_coords, right_coords, center_segments)
                
                surface_data = {
                    'surface_id': surface['surface_id'],
                    'center_segments': center_segments,
                    'width_profile': width_profile,
                    'left_boundary': surface['left_boundary'],
                    'right_boundary': surface['right_boundary']
                }
                
                converted_surfaces.append(surface_data)
                
            except Exception as e:
                logger.error(f"车道面 {surface.get('surface_id', 'unknown')} 几何转换失败: {e}")
                continue
        
        logger.info(f"成功转换 {len(converted_surfaces)} 个车道面的几何")
        return converted_surfaces
    
    def _calculate_center_line(self, left_coords: List[Tuple[float, float]], 
                              right_coords: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """计算两条边界线的中心线
        
        Args:
            left_coords: 左边界坐标点
            right_coords: 右边界坐标点
            
        Returns:
            List[Tuple[float, float]]: 中心线坐标点
        """
        # 确保两条线有相同的点数，如果不同则进行插值
        if len(left_coords) != len(right_coords):
            # 使用较多点数的线作为参考
            target_points = max(len(left_coords), len(right_coords))
            left_coords = self._interpolate_coordinates(left_coords, target_points)
            right_coords = self._interpolate_coordinates(right_coords, target_points)
        
        center_coords = []
        for left_pt, right_pt in zip(left_coords, right_coords):
            center_x = (left_pt[0] + right_pt[0]) / 2
            center_y = (left_pt[1] + right_pt[1]) / 2
            center_coords.append((center_x, center_y))
        
        return center_coords
    
    def _interpolate_coordinates(self, coords: List[Tuple[float, float]], 
                                target_points: int) -> List[Tuple[float, float]]:
        """对坐标序列进行插值以获得指定数量的点
        
        Args:
            coords: 原始坐标点
            target_points: 目标点数
            
        Returns:
            List[Tuple[float, float]]: 插值后的坐标点
        """
        if len(coords) == target_points:
            return coords
        
        # 计算累积距离
        distances = [0]
        for i in range(1, len(coords)):
            dist = math.sqrt((coords[i][0] - coords[i-1][0])**2 + 
                           (coords[i][1] - coords[i-1][1])**2)
            distances.append(distances[-1] + dist)
        
        total_length = distances[-1]
        
        # 生成等间距的插值点
        interpolated_coords = []
        for i in range(target_points):
            target_dist = (i / (target_points - 1)) * total_length
            
            # 找到对应的线段
            for j in range(len(distances) - 1):
                if distances[j] <= target_dist <= distances[j + 1]:
                    # 在线段内插值
                    ratio = (target_dist - distances[j]) / (distances[j + 1] - distances[j])
                    x = coords[j][0] + ratio * (coords[j + 1][0] - coords[j][0])
                    y = coords[j][1] + ratio * (coords[j + 1][1] - coords[j][1])
                    interpolated_coords.append((x, y))
                    break
        
        return interpolated_coords
    
    def _calculate_width_profile(self, left_coords: List[Tuple[float, float]], 
                                right_coords: List[Tuple[float, float]], 
                                center_segments: List[Dict]) -> List[Dict]:
        """计算车道宽度变化曲线
        
        Args:
            left_coords: 左边界坐标
            right_coords: 右边界坐标
            center_segments: 中心线几何段
            
        Returns:
            List[Dict]: 宽度变化数据
        """
        width_profile = []
        
        # 确保坐标点数相同
        if len(left_coords) != len(right_coords):
            target_points = max(len(left_coords), len(right_coords))
            left_coords = self._interpolate_coordinates(left_coords, target_points)
            right_coords = self._interpolate_coordinates(right_coords, target_points)
        
        # 计算每个点的宽度
        current_s = 0.0
        for i, (left_pt, right_pt) in enumerate(zip(left_coords, right_coords)):
            width = math.sqrt((left_pt[0] - right_pt[0])**2 + (left_pt[1] - right_pt[1])**2)
            
            width_data = {
                's': current_s,
                'width': width,
                'left_point': left_pt,
                'right_point': right_pt
            }
            
            width_profile.append(width_data)
            
            # 计算到下一个点的距离
            if i < len(left_coords) - 1:
                center_current = ((left_pt[0] + right_pt[0]) / 2, (left_pt[1] + right_pt[1]) / 2)
                left_next, right_next = left_coords[i + 1], right_coords[i + 1]
                center_next = ((left_next[0] + right_next[0]) / 2, (left_next[1] + right_next[1]) / 2)
                
                segment_length = math.sqrt((center_next[0] - center_current[0])**2 + 
                                         (center_next[1] - center_current[1])**2)
                current_s += segment_length
        
        return width_profile