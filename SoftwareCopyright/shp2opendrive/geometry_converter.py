import numpy as np
from scipy.optimize import minimize
from scipy.interpolate import splprep, splev
from shapely.geometry import LineString, Point
from typing import List, Tuple, Dict, Optional, Any
import math
import logging
from scipy import interpolate
from scipy.optimize import minimize_scalar
from abc import ABC, abstractmethod
logger = logging.getLogger(__name__)
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
class GeometryConversionHandler(ConversionHandler):
    def __init__(self, tolerance: float = 3.0, smooth_curves: bool = True, preserve_detail: bool = False, 
                 curve_fitting_mode: str = "parampoly3", polynomial_degree: int = 3, curve_smoothness: float = 0.5,
                 coordinate_precision: int = 3):
        super().__init__()
        self.geometry_converter = GeometryConverter(tolerance, smooth_curves, preserve_detail, 
                                                   curve_fitting_mode, polynomial_degree, curve_smoothness, coordinate_precision)
    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        if request.get('stage') != 'geometry_conversion':
            return self._handle_next(request)
        roads_data = request.get('roads_data', [])
        converted_roads = []
        for road_data in roads_data:
            if road_data.get('type') == 'lane_based':
                converted_road = self._convert_lane_based_geometry(road_data)
            else:
                converted_road = self._convert_traditional_geometry(road_data)
            if converted_road:
                converted_roads.append(converted_road)
        request['converted_roads'] = converted_roads
        request['stage'] = 'opendrive_generation'
        return self._handle_next(request)
    def _convert_lane_based_geometry(self, road_data: Dict) -> Dict:
        try:
            lane_surfaces = road_data.get('lane_surfaces', [])
            if not lane_surfaces:
                return None
            converted_surfaces = self.geometry_converter.convert_lane_surface_geometry(lane_surfaces)
            if not converted_surfaces:
                return None
            converted_road = {
                'id': road_data['id'],
                'type': 'lane_based',
                'lane_surfaces': converted_surfaces,
                'attributes': road_data.get('attributes', {})
            }
            return converted_road
        except Exception as e:
            logger.error(f"Lane格式道路 {road_data.get('id', 'unknown')} 几何转换失败: {e}")
            return None
    def _convert_traditional_geometry(self, road_data: Dict) -> Dict:
        try:
            coordinates = road_data['coordinates']
            segments = self.geometry_converter.convert_road_geometry(coordinates)
            if not segments:
                return None
            total_length = self.geometry_converter.calculate_road_length(segments)
            converted_road = {
                'id': road_data['id'],
                'type': 'traditional',
                'segments': segments,
                'attributes': road_data['attributes'],
                'total_length': total_length
            }
            return converted_road
        except Exception as e:
            logger.error(f"传统格式道路 {road_data.get('id', 'unknown')} 几何转换失败: {e}")
            return None
class GeometryConverter:
    def __init__(self, tolerance: float = 3.0, smooth_curves: bool = True, preserve_detail: bool = False, 
                 curve_fitting_mode: str = "parampoly3", polynomial_degree: int = 3, curve_smoothness: float = 0.5,
                 coordinate_precision: int = 3):
        self.tolerance = tolerance
        self.smooth_curves = smooth_curves
        self.preserve_detail = preserve_detail
        self.curve_fitting_mode = curve_fitting_mode
        self.polynomial_degree = max(2, min(5, polynomial_degree))
        self.curve_smoothness = max(0.0, min(1.0, curve_smoothness))
        self.coordinate_precision = max(1, min(10, coordinate_precision))
        if preserve_detail:
            self.effective_tolerance = tolerance * 0.8
        else:
            self.effective_tolerance = tolerance * 1.5
        self.road_segments = []
        self.max_segments_per_road = 50
        logger.info(f"几何转换器初始化，容差: {tolerance}m, 有效容差: {self.effective_tolerance}m, 平滑曲线: {smooth_curves}, 保留细节: {preserve_detail}")
    def convert_road_geometry(self, coordinates: List[Tuple[float, float]]) -> List[Dict]:
        if len(coordinates) < 2:
            logger.warning("坐标点数量不足，无法转换")
            return []
        if self.curve_fitting_mode == "polyline":
            if len(coordinates) > 50:
                logger.debug(f"检测到高密度坐标（{len(coordinates)}个点），使用保形转换")
                return self._fit_adaptive_line_segments(coordinates)
            elif self.smooth_curves and len(coordinates) >= 3:
                return self.fit_smooth_curve_segments(coordinates)
            else:
                return self.fit_line_segments(coordinates)
        elif self.curve_fitting_mode == "polynomial":
            logger.debug(f"使用多项式曲线拟合，阶数: {self.polynomial_degree}, 平滑度: {self.curve_smoothness}")
            return self._fit_polynomial_curves(coordinates)
        elif self.curve_fitting_mode == "spline":
            logger.debug(f"使用样条曲线拟合，平滑度: {self.curve_smoothness}")
            return self._fit_spline_curves(coordinates)
        elif self.curve_fitting_mode == "parampoly3":
            logger.debug(f"使用ParamPoly3曲线拟合，阶数: {self.polynomial_degree}, 平滑度: {self.curve_smoothness}")
            return self._fit_polynomial_curves(coordinates)
        else:
            logger.warning(f"未知的曲线拟合模式: {self.curve_fitting_mode}，使用默认折线拟合")
            return self.fit_line_segments(coordinates)
    def fit_smooth_curve_segments(self, coordinates: List[Tuple[float, float]]) -> List[Dict]:
        if len(coordinates) < 3:
            return self.fit_line_segments(coordinates)
        segments = []
        current_s = 0.0
        if self.preserve_detail:
            simplified_coords = self._adaptive_simplify(coordinates)
        else:
            simplified_coords = self._douglas_peucker(coordinates, self.effective_tolerance)
        if self.smooth_curves and len(simplified_coords) >= 4:
            smooth_coords = self._spline_interpolation(simplified_coords)
            segments = self._fit_curve_segments_from_smooth(smooth_coords, current_s)
        else:
            segments = self._fit_adaptive_line_segments(simplified_coords, current_s)
        return segments
    def _calculate_arc_lengths(self, coordinates: List[Tuple[float, float]]) -> np.ndarray:
        arc_lengths = np.zeros(len(coordinates))
        for i in range(1, len(coordinates)):
            dx = coordinates[i][0] - coordinates[i-1][0]
            dy = coordinates[i][1] - coordinates[i-1][1]
            arc_lengths[i] = arc_lengths[i-1] + np.sqrt(dx*dx + dy*dy)
        return arc_lengths
    def _calculate_precise_heading(self, coordinates: List[Tuple[float, float]]) -> float:
        if len(coordinates) < 2:
            return 0.0
        if len(coordinates) == 2:
            dx = coordinates[1][0] - coordinates[0][0]
            dy = coordinates[1][1] - coordinates[0][1]
            return math.atan2(dy, dx)
        total_dx = 0.0
        total_dy = 0.0
        weight_sum = 0.0
        for i in range(1, min(len(coordinates), 4)):
            dx = coordinates[i][0] - coordinates[0][0]
            dy = coordinates[i][1] - coordinates[0][1]
            distance = np.sqrt(dx*dx + dy*dy)
            if distance > 1e-6:
                weight = 1.0 / (i * i)
                total_dx += dx * weight
                total_dy += dy * weight
                weight_sum += weight
        if weight_sum > 0:
            avg_dx = total_dx / weight_sum
            avg_dy = total_dy / weight_sum
            return math.atan2(avg_dy, avg_dx)
        return 0.0
    def _select_optimal_polynomial_degree(self, t_params: np.ndarray, 
                                         local_u: np.ndarray, 
                                         local_v: np.ndarray) -> int:
        max_degree = min(self.polynomial_degree, len(t_params) - 1, 3)
        min_degree = 1
        if len(t_params) <= 3:
            return min_degree
        best_degree = min_degree
        best_score = float('inf')
        for degree in range(min_degree, max_degree + 1):
            try:
                # 计算拟合误差
                poly_u = np.polyfit(t_params, local_u, degree)
                poly_v = np.polyfit(t_params, local_v, degree)
                # 计算残差
                u_fitted = np.polyval(poly_u, t_params)
                v_fitted = np.polyval(poly_v, t_params)
                u_residuals = local_u - u_fitted
                v_residuals = local_v - v_fitted
                # 计算均方根误差
                rmse = np.sqrt(np.mean(u_residuals**2 + v_residuals**2))
                # 添加复杂度惩罚（避免过拟合）
                complexity_penalty = degree * 0.01
                score = rmse + complexity_penalty
                if score < best_score:
                    best_score = score
                    best_degree = degree
            except Exception:
                continue
        return best_degree
    def _calculate_fitting_weights(self, num_points: int) -> np.ndarray:
        weights = np.ones(num_points)
        weights[0] = 2.0
        weights[-1] = 2.0
        if num_points > 4:
            weights[1] = 1.5
            weights[-2] = 1.5
        return weights
    def _evaluate_fitting_quality(self, t_params: np.ndarray, 
                                 local_u: np.ndarray, 
                                 local_v: np.ndarray,
                                 poly_u: np.ndarray, 
                                 poly_v: np.ndarray) -> float:
        try:
            u_fitted = np.polyval(poly_u, t_params)
            v_fitted = np.polyval(poly_v, t_params)
            u_residuals = local_u - u_fitted
            v_residuals = local_v - v_fitted
            max_error = np.max(np.sqrt(u_residuals**2 + v_residuals**2))
            rmse = np.sqrt(np.mean(u_residuals**2 + v_residuals**2))
            return 0.7 * max_error + 0.3 * rmse
        except Exception:
            return float('inf')
    def _optimize_boundary_conditions(self, local_u: np.ndarray, local_v: np.ndarray,
                                    au: float, bu: float, cu: float, du: float,
                                    av: float, bv: float, cv: float, dv: float,
                                    degree: int) -> Tuple[float, float, float, float, float, float, float, float]:
        au = 0.0
        av = 0.0
        end_u = local_u[-1]
        end_v = local_v[-1]
        if degree == 1:
            bu = end_u
            bv = end_v
            cu = du = cv = dv = 0.0
        else:
            current_sum_u = bu + cu + du
            current_sum_v = bv + cv + dv
            if abs(current_sum_u) < 1e-10:
                bu = end_u
            else:
                scale_u = end_u / current_sum_u
                bu *= scale_u
                cu *= scale_u
                du *= scale_u
            if abs(current_sum_v) < 1e-10:
                bv = end_v
            else:
                scale_v = end_v / current_sum_v
                bv *= scale_v
                cv *= scale_v
                dv *= scale_v
        return au, bu, cu, du, av, bv, cv, dv
    def _fit_segmented_polynomial_curves(self, coordinates: List[Tuple[float, float]]) -> List[Dict]:
        if len(coordinates) < 6:
            return self._fit_polynomial_curves(coordinates)
        segments = []
        current_s = 0.0
        curvature_changes = self._detect_curvature_changes(coordinates)
        segment_points = self._determine_segment_points(coordinates, curvature_changes)
        for i in range(len(segment_points) - 1):
            start_idx = segment_points[i]
            end_idx = segment_points[i + 1] + 1  # 包含端点
            segment_coords = coordinates[start_idx:end_idx]
            if len(segment_coords) >= 3:
                segment_geometries = self._fit_polynomial_curves(segment_coords)
                for geom in segment_geometries:
                    geom['s'] = current_s
                    current_s += geom['length']
                    segments.append(geom)
            else:
                line_segments = self.fit_line_segments(segment_coords)
                for geom in line_segments:
                    geom['s'] = current_s
                    current_s += geom['length']
                    segments.append(geom)
        logger.debug(f"分段拟合完成，总段数: {len(segments)}, 原始点数: {len(coordinates)}")
        return segments
    def _detect_curvature_changes(self, coordinates: List[Tuple[float, float]]) -> List[int]:
        if len(coordinates) < 5:
            return []
        curvatures = []
        for i in range(2, len(coordinates) - 2):
            p1 = coordinates[i-2]
            p2 = coordinates[i-1]
            p3 = coordinates[i]
            p4 = coordinates[i+1]
            p5 = coordinates[i+2]
            curvature = self._calculate_point_curvature([p1, p2, p3, p4, p5])
            curvatures.append(curvature)
        change_points = []
        threshold = np.std(curvatures) * 1.5  # 动态阈值
        for i in range(1, len(curvatures) - 1):
            if abs(curvatures[i] - curvatures[i-1]) > threshold:
                change_points.append(i + 2)  # 调整索引
        return change_points
    def _calculate_point_curvature(self, points: List[Tuple[float, float]]) -> float:
        if len(points) < 3:
            return 0.0
        p1, p2, p3 = points[0], points[2], points[4]
        v1 = (p2[0] - p1[0], p2[1] - p1[1])
        v2 = (p3[0] - p2[0], p3[1] - p2[1])
        cross = v1[0] * v2[1] - v1[1] * v2[0]
        norm1 = np.sqrt(v1[0]**2 + v1[1]**2)
        norm2 = np.sqrt(v2[0]**2 + v2[1]**2)
        if norm1 * norm2 > 1e-10:
            return abs(cross) / (norm1 * norm2)
        return 0.0
    def _determine_segment_points(self, coordinates: List[Tuple[float, float]], 
                                curvature_changes: List[int]) -> List[int]:
        segment_points = [0]
        max_segment_length = 15
        min_segment_length = 5
        current_start = 0
        for change_point in curvature_changes:
            if (change_point - current_start >= min_segment_length and 
                change_point - current_start <= max_segment_length):
                segment_points.append(change_point)
                current_start = change_point
            elif change_point - current_start > max_segment_length:
                forced_point = current_start + max_segment_length
                segment_points.append(forced_point)
                current_start = forced_point
        remaining_length = len(coordinates) - 1 - current_start
        if remaining_length > max_segment_length:
            while current_start + max_segment_length < len(coordinates) - 1:
                current_start += max_segment_length
                segment_points.append(current_start)
        if segment_points[-1] != len(coordinates) - 1:
            segment_points.append(len(coordinates) - 1)
        return segment_points
    def _adaptive_simplify(self, coordinates: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        if len(coordinates) <= 3:
            return coordinates
        result = [coordinates[0]]
        for i in range(1, len(coordinates) - 1):
            curvature = self._calculate_curvature(coordinates[i-1], coordinates[i], coordinates[i+1])
            adaptive_tolerance = self.effective_tolerance
            if curvature > 0.2:
                adaptive_tolerance *= 0.7
            elif curvature < 0.05:
                adaptive_tolerance *= 4.0
            else:
                adaptive_tolerance *= 2.0
            if len(result) >= 2:
                distance = self._point_to_line_distance(coordinates[i], result[-2], coordinates[-1])
                if distance > adaptive_tolerance:
                    result.append(coordinates[i])
            else:
                result.append(coordinates[i])
        result.append(coordinates[-1])
        return result
    def _calculate_curvature(self, p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float]) -> float:
        v1 = (p2[0] - p1[0], p2[1] - p1[1])
        v2 = (p3[0] - p2[0], p3[1] - p2[1])
        len1 = math.sqrt(v1[0]**2 + v1[1]**2)
        len2 = math.sqrt(v2[0]**2 + v2[1]**2)
        if len1 == 0 or len2 == 0:
            return 0.0
        dot_product = v1[0] * v2[0] + v1[1] * v2[1]
        cross_product = v1[0] * v2[1] - v1[1] * v2[0]
        angle = math.atan2(abs(cross_product), dot_product)
        avg_length = (len1 + len2) / 2
        return angle / avg_length if avg_length > 0 else 0.0
    def _spline_interpolation(self, coordinates: List[Tuple[float, float]], num_points: int = None) -> List[Tuple[float, float]]:
        if len(coordinates) < 4:
            return coordinates
        try:
            x_coords = [p[0] for p in coordinates]
            y_coords = [p[1] for p in coordinates]
            distances = [0]
            for i in range(1, len(coordinates)):
                dist = math.sqrt((x_coords[i] - x_coords[i-1])**2 + (y_coords[i] - y_coords[i-1])**2)
                distances.append(distances[-1] + dist)
            if num_points is None:
                num_points = len(coordinates) * 2
            t_new = np.linspace(0, distances[-1], num_points)
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
        segments = []
        current_s = start_s
        i = 0
        while i < len(smooth_coords) - 1:
            curve_end = self._detect_smooth_curve_segment(smooth_coords, i)
            if curve_end > i + 2:  # 找到曲线段
                curve_coords = smooth_coords[i:curve_end + 1]
                arc_segment = self._fit_smooth_arc(curve_coords, current_s)
                if arc_segment:
                    segments.append(arc_segment)
                    current_s += arc_segment['length']
                    i = curve_end
                else:
                    line_segment = self._create_line_segment(smooth_coords[i], smooth_coords[i + 1], current_s, i == 0)
                    segments.append(line_segment)
                    current_s += line_segment['length']
                    i += 1
            else:
                line_segment = self._create_line_segment(smooth_coords[i], smooth_coords[i + 1], current_s, i == 0)
                segments.append(line_segment)
                current_s += line_segment['length']
                i += 1
        return segments
    def _detect_smooth_curve_segment(self, coordinates: List[Tuple[float, float]], start_idx: int) -> int:
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
                    if curve_points >= min_curve_points:
                        return i
                    curve_points = 0
        if curve_points >= min_curve_points:
            return min(start_idx + max_curve_points - 1, len(coordinates) - 1)
        return start_idx + 1
    def _fit_smooth_arc(self, coordinates: List[Tuple[float, float]], start_s: float) -> Optional[Dict]:
        if len(coordinates) < 3:
            return None
        try:
            center, radius = self._fit_circle(coordinates)
            if radius < 10 or radius > 10000:
                return None
            start_point = coordinates[0]
            end_point = coordinates[-1]
            start_angle = math.atan2(start_point[1] - center[1], start_point[0] - center[0])
            end_angle = math.atan2(end_point[1] - center[1], end_point[0] - center[0])
            angle_diff = end_angle - start_angle
            while angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            while angle_diff < -math.pi:
                angle_diff += 2 * math.pi
            arc_length = abs(angle_diff) * radius
            curvature = angle_diff / arc_length if arc_length > 0 else 0
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
            if start_s == 0:
                segment['x'] = start_point[0]
                segment['y'] = start_point[1]
            return segment
        except Exception as e:
            logger.debug(f"圆弧拟合失败: {e}")
            return None
    def _fit_adaptive_line_segments(self, coordinates: List[Tuple[float, float]], start_s: float = 0.0) -> List[Dict]:
        segments = []
        current_s = start_s
        for i in range(len(coordinates) - 1):
            segment = self._create_line_segment(coordinates[i], coordinates[i + 1], current_s, i == 0)
            segments.append(segment)
            current_s += segment['length']
        return segments
    def _create_line_segment(self, start_point: Tuple[float, float], end_point: Tuple[float, float], 
                           s_coord: float, include_xy: bool = False) -> Dict:
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
        segments = []
        current_s = 0.0
        simplified_coords = self._douglas_peucker(coordinates, self.tolerance)
        if len(simplified_coords) > self.max_segments_per_road:
            logger.warning(f"简化后仍有{len(simplified_coords)}个点，超过限制{self.max_segments_per_road}，进一步简化")
            simplified_coords = self._limit_segments(simplified_coords, self.max_segments_per_road)
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
            if len(segments) == 0:
                segment['x'] = start[0]
                segment['y'] = start[1]
            segments.append(segment)
            current_s += length
        return segments
    def fit_arc_segments(self, coordinates: List[Tuple[float, float]]) -> List[Dict]:
        segments = []
        current_s = 0.0
        i = 0
        while i < len(coordinates) - 1:
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
                if len(segments) == 0:
                    segment['x'] = start[0]
                    segment['y'] = start[1]
                segments.append(segment)
                current_s += length
                i += 1
        return segments
    def _douglas_peucker(self, coordinates: List[Tuple[float, float]], tolerance: float) -> List[Tuple[float, float]]:
        if len(coordinates) <= 2:
            return coordinates
        start = coordinates[0]
        end = coordinates[-1]
        max_distance = 0
        max_index = 0
        for i in range(1, len(coordinates) - 1):
            distance = self._point_to_line_distance(coordinates[i], start, end)
            if distance > max_distance:
                max_distance = distance
                max_index = i
        if max_distance < tolerance:
            return [start, end]
        left_part = self._douglas_peucker(coordinates[:max_index + 1], tolerance)
        right_part = self._douglas_peucker(coordinates[max_index:], tolerance)
        return left_part[:-1] + right_part
    def _point_to_line_distance(self, point: Tuple[float, float], 
                               line_start: Tuple[float, float], 
                               line_end: Tuple[float, float]) -> float:
        x0, y0 = point
        x1, y1 = line_start
        x2, y2 = line_end
        line_length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        if line_length == 0:
            return math.sqrt((x0 - x1)**2 + (y0 - y1)**2)
        distance = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1) / line_length
        return distance
    def _limit_segments(self, coordinates: List[Tuple[float, float]], max_segments: int) -> List[Tuple[float, float]]:
        if len(coordinates) <= max_segments:
            return coordinates
        result = [coordinates[0]]
        step = (len(coordinates) - 1) / (max_segments - 1)
        for i in range(1, max_segments - 1):
            idx = int(round(i * step))
            if idx < len(coordinates) and coordinates[idx] not in result:
                result.append(coordinates[idx])
        result.append(coordinates[-1])
        logger.info(f"几何段数量从{len(coordinates)}限制到{len(result)}")
        return result
    def _detect_curve_segment(self, coordinates: List[Tuple[float, float]], start_idx: int) -> int:
        if start_idx >= len(coordinates) - 2:
            return start_idx + 1
        angle_threshold = math.radians(10)  # 10度阈值
        for i in range(start_idx + 2, len(coordinates)):
            if i >= len(coordinates) - 1:
                break
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
        if len(coordinates) < 3:
            return None
        try:
            center, radius = self._fit_circle(coordinates)
            if radius is None or radius < 1.0:  # 半径太小，当作直线处理
                return None
            start_point = coordinates[0]
            end_point = coordinates[-1]
            start_angle = math.atan2(start_point[1] - center[1], start_point[0] - center[0])
            end_angle = math.atan2(end_point[1] - center[1], end_point[0] - center[0])
            angle_diff = end_angle - start_angle
            if angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            elif angle_diff < -math.pi:
                angle_diff += 2 * math.pi
            arc_length = abs(angle_diff * radius)
            curvature = 1.0 / radius if radius > 0 else 0
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
        points = np.array(coordinates)
        if len(points) >= 3:
            x1, y1 = points[0]
            x2, y2 = points[len(points)//2]
            x3, y3 = points[-1]
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
        return sum(segment['length'] for segment in segments)
    def validate_geometry_continuity(self, segments: List[Dict]) -> bool:
        if len(segments) < 2:
            return True
        tolerance = 0.1  # 1cm容差
        current_x = segments[0].get('x', 0.0)
        current_y = segments[0].get('y', 0.0)
        for i in range(len(segments) - 1):
            current = segments[i]
            if current['type'] == 'line':
                end_x = current_x + current['length'] * math.cos(current['hdg'])
                end_y = current_y + current['length'] * math.sin(current['hdg'])
            else:  # arc
                end_x = current_x + current['length'] * math.cos(current['hdg'])
                end_y = current_y + current['length'] * math.sin(current['hdg'])
            next_start_x = end_x
            next_start_y = end_y
            current_x = next_start_x
            current_y = next_start_y
        return True
    def convert_lane_surface_geometry(self, lane_surfaces: List[Dict]) -> List[Dict]:
        converted_surfaces = []
        for surface in lane_surfaces:
            try:
                left_coords = surface['left_boundary']['coordinates']
                right_coords = surface['right_boundary']['coordinates']
                center_coords, width_data = self._calculate_center_line(left_coords, right_coords)
                center_segments = self.convert_road_geometry(center_coords)
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
                              right_coords: List[Tuple[float, float]]) -> Tuple[List[Tuple[float, float]], List[Dict]]:
        max_points = max(len(left_coords), len(right_coords))
        if max_points <= 10:
            target_points = max(max_points * 10, 50)  # 少点数时增加10倍采样
        else:
            target_points = max(max_points * 2, 100)  # 多点数时增加2倍采样
        logger.debug(f"车道面中心线计算：原始点数 {max_points}，目标点数 {target_points}")
        left_interpolated = self._interpolate_coordinates(left_coords, target_points)
        right_interpolated = self._interpolate_coordinates(right_coords, target_points)
        center_coords = []
        width_data = []
        current_s = 0.0
        for i, (left_pt, right_pt) in enumerate(zip(left_interpolated, right_interpolated)):
            center_x = (left_pt[0] + right_pt[0]) / 2
            center_y = (left_pt[1] + right_pt[1]) / 2
            center_coords.append((center_x, center_y))
            width = math.sqrt((left_pt[0] - right_pt[0])**2 + (left_pt[1] - right_pt[1])**2)
            width = round(width, self.coordinate_precision)
            width_info = {
                's': current_s,
                'width': width,
                'left_point': left_pt,
                'right_point': right_pt,
                'center_point': (center_x, center_y)
            }
            width_data.append(width_info)
            if i < len(left_interpolated) - 1:
                next_left, next_right = left_interpolated[i + 1], right_interpolated[i + 1]
                next_center_x = (next_left[0] + next_right[0]) / 2
                next_center_y = (next_left[1] + next_right[1]) / 2
                segment_length = math.sqrt((next_center_x - center_x)**2 + (next_center_y - center_y)**2)
                current_s += segment_length
        if self.preserve_detail and len(center_coords) > 10:
            original_center_coords = center_coords.copy()
            simplified_coords = self._adaptive_simplify(center_coords)
            logger.debug(f"中心线计算：原始点数 {len(center_coords)}，简化后 {len(simplified_coords)}")
            simplified_width_data = self._simplify_width_data(width_data, original_center_coords, simplified_coords)
            return simplified_coords, simplified_width_data
        return center_coords, width_data
    def _simplify_width_data(self, width_data: List[Dict], 
                           original_coords: List[Tuple[float, float]], 
                           simplified_coords: List[Tuple[float, float]]) -> List[Dict]:
        if not width_data or not simplified_coords:
            return width_data
    def _smooth_width_profile_bezier(self, width_profile: List[Dict]) -> List[Dict]:
        if len(width_profile) < 4:
            return width_profile
        try:
            s_values = [item['s'] for item in width_profile]
            width_values = [item['width'] for item in width_profile]
            smoothed_widths = self._bezier_smooth(s_values, width_values)
            for i, item in enumerate(width_profile):
                if i < len(smoothed_widths):
                    item['width'] = max(0.1, smoothed_widths[i])  # 确保宽度不为负
            return width_profile
        except Exception as e:
            logger.warning(f"贝塞尔曲线平滑失败: {e}，使用原始数据")
            return width_profile
    def _calculate_cubic_polynomial_coefficients(self, width_profile: List[Dict]) -> List[Dict]:
        if len(width_profile) < 2:
            return []
        simplified_profile = self._simplify_width_profile(width_profile)
        polynomial_segments = []
        for i in range(len(simplified_profile) - 1):
            current_point = simplified_profile[i]
            next_point = simplified_profile[i + 1]
            s0 = current_point['s']
            s1 = next_point['s']
            w0 = current_point['width']
            w1 = next_point['width']
            ds = s1 - s0
            if ds <= 0:
                continue
            if i == 0:
                if len(simplified_profile) > 2:
                    dw0 = (simplified_profile[i + 1]['width'] - w0) / (simplified_profile[i + 1]['s'] - s0)
                else:
                    dw0 = 0
            else:
                dw0 = (w1 - simplified_profile[i - 1]['width']) / (s1 - simplified_profile[i - 1]['s'])
            if i == len(simplified_profile) - 2:
                if len(simplified_profile) > 2:
                    dw1 = (w1 - simplified_profile[i]['width']) / (s1 - simplified_profile[i]['s'])
                else:
                    dw1 = 0
            else:
                dw1 = (simplified_profile[i + 2]['width'] - w0) / (simplified_profile[i + 2]['s'] - s0)
            a = w0
            b = dw0
            c = (3 * (w1 - w0) / ds - 2 * dw0 - dw1) / ds
            d = (2 * (w0 - w1) / ds + dw0 + dw1) / (ds * ds)
            segment = {
                's': s0,
                'length': ds,
                'a': a,
                'b': b,
                'c': c,
                'd': d,
                'end_s': s1,
                'start_width': w0,
                'end_width': w1
            }
            polynomial_segments.append(segment)
        return polynomial_segments
    def _bezier_smooth(self, s_values: List[float], width_values: List[float]) -> List[float]:
        if len(width_values) < 4:
            return width_values
        smoothed = []
        for i in range(len(width_values)):
            if i == 0:
                smoothed.append(width_values[i])
            elif i == len(width_values) - 1:
                smoothed.append(width_values[i])
            else:
                p0_idx = max(0, i - 1)
                p1_idx = i
                p2_idx = min(len(width_values) - 1, i + 1)
                p3_idx = min(len(width_values) - 1, i + 2)
                p0 = width_values[p0_idx]
                p1 = width_values[p1_idx]
                p2 = width_values[p2_idx]
                p3 = width_values[p3_idx]
                tension = 0.5  # 张力参数，控制平滑程度
                if i > 0 and i < len(width_values) - 1:
                    # 前向差分和后向差分的平均
                    tangent_in = (p2 - p0) * tension
                    tangent_out = (p3 - p1) * tension
                    t = 0.5  # 插值参数
                    h1 = 2*t**3 - 3*t**2 + 1
                    h2 = -2*t**3 + 3*t**2
                    h3 = t**3 - 2*t**2 + t
                    h4 = t**3 - t**2
                    smoothed_value = h1*p1 + h2*p2 + h3*tangent_in + h4*tangent_out
                    min_val = min(p0, p1, p2, p3) * 0.8
                    max_val = max(p0, p1, p2, p3) * 1.2
                    smoothed_value = max(min_val, min(max_val, smoothed_value))
                    smoothed.append(smoothed_value)
                else:
                    smoothed.append(p1)
        return smoothed
    def _simplify_width_data(self, width_data: List[Dict], original_coords: List[Tuple[float, float]], 
                            simplified_coords: List[Tuple[float, float]]) -> List[Dict]:
        if not width_data or not simplified_coords:
            return width_data
        simplified_width_data = []
        for simplified_pt in simplified_coords:
            min_distance = float('inf')
            closest_index = 0
            for i, original_pt in enumerate(original_coords):
                distance = math.sqrt((simplified_pt[0] - original_pt[0])**2 + 
                                   (simplified_pt[1] - original_pt[1])**2)
                if distance < min_distance:
                    min_distance = distance
                    closest_index = i
            if closest_index < len(width_data):
                width_info = width_data[closest_index].copy()
                width_info['center_point'] = tuple(simplified_pt) if not isinstance(simplified_pt, tuple) else simplified_pt
                simplified_width_data.append(width_info)
        # 重新计算s坐标以保持连续性
        current_s = 0.0
        for i, width_info in enumerate(simplified_width_data):
            width_info['s'] = current_s
            if i < len(simplified_width_data) - 1:
                current_pt = width_info['center_point']
                next_pt = simplified_width_data[i + 1]['center_point']
                if isinstance(current_pt, (list, tuple)) and isinstance(next_pt, (list, tuple)):
                    segment_length = math.sqrt((next_pt[0] - current_pt[0])**2 + 
                                             (next_pt[1] - current_pt[1])**2)
                    current_s += segment_length
        logger.debug(f"宽度数据简化：原始 {len(width_data)} 个点，简化后 {len(simplified_width_data)} 个点")
        return simplified_width_data
    def _interpolate_coordinates(self, coords: List[Tuple[float, float]], 
                                target_points: int) -> List[Tuple[float, float]]:
        if len(coords) == target_points:
            return coords
        distances = [0]
        for i in range(1, len(coords)):
            dist = math.sqrt((coords[i][0] - coords[i-1][0])**2 + 
                           (coords[i][1] - coords[i-1][1])**2)
            distances.append(distances[-1] + dist)
        
        total_length = distances[-1]
        interpolated_coords = []
        for i in range(target_points):
            target_dist = (i / (target_points - 1)) * total_length
            for j in range(len(distances) - 1):
                if distances[j] <= target_dist <= distances[j + 1]:
                    ratio = (target_dist - distances[j]) / (distances[j + 1] - distances[j])
                    x = coords[j][0] + ratio * (coords[j + 1][0] - coords[j][0])
                    y = coords[j][1] + ratio * (coords[j + 1][1] - coords[j][1])
                    interpolated_coords.append((x, y))
                    break
        return interpolated_coords
    def _calculate_width_profile(self, left_coords: List[Tuple[float, float]], 
                                right_coords: List[Tuple[float, float]], 
                                center_segments: List[Dict]) -> List[Dict]:
        width_profile = []
        if len(left_coords) != len(right_coords):
            target_points = max(len(left_coords), len(right_coords))
            left_coords = self._interpolate_coordinates(left_coords, target_points)
            right_coords = self._interpolate_coordinates(right_coords, target_points)
        reference_line = self._reconstruct_reference_line(center_segments)
        if not reference_line:
            logger.warning("无法从几何段重建参考线，使用简化计算")
            return self._calculate_width_profile_simple(left_coords, right_coords)
        total_length = sum(segment['length'] for segment in center_segments)
        base_samples = min(len(left_coords), len(right_coords))  # 使用较少的边界点数作为基准
        if total_length <= 50:  # 短道路：每20-25米一个采样点
            samples_by_length = max(int(total_length / 25), 3)
        elif total_length <= 200:  # 中等道路：每30-40米一个采样点
            samples_by_length = max(int(total_length / 35), 6)
        else:  # 长道路：每50米一个采样点
            samples_by_length = max(int(total_length / 50), 8)
        max_samples = min(20, base_samples)  # 最多20个采样点
        num_samples = min(max(samples_by_length, 3), max_samples)  # 至少3个点，最多max_samples个点
        sample_interval = total_length / (num_samples - 1) if num_samples > 1 else 0
        for i in range(num_samples):
            current_s = i * sample_interval
            ref_point, ref_heading = self._get_reference_point_at_s(center_segments, current_s)
            if ref_point is None:
                logger.warning(f"无法在s={current_s:.2f}处找到参考点")
                continue
            left_pts = self._find_closest_two_points(left_coords, ref_point)
            right_pts = self._find_closest_two_points(right_coords, ref_point)
            width = self._calculate_line_intersection_width(left_pts, right_pts, ref_point, ref_heading)
            logger.debug(f"宽度计算 - s={current_s:.2f}: 左边界{left_pts}, 右边界{right_pts}, 参考点{ref_point}, 宽度={width:.3f}")
            if width <= 0.001:  # 小于1mm认为是异常
                logger.warning(f"检测到异常宽度 - s={current_s:.2f}: 宽度={width:.6f}, 左边界{left_pts}, 右边界{right_pts}, 参考点{ref_point}, 航向角={ref_heading:.3f}")
            width_data = {
                's': current_s,
                'width': width,
                'left_point': left_pts[0] if left_pts else ref_point,
                'right_point': right_pts[0] if right_pts else ref_point,
                'reference_point': ref_point,
                'reference_heading': ref_heading
            }
            width_profile.append(width_data)
        if len(width_profile) > 3:
            width_profile = self._smooth_width_profile_bezier(width_profile)
        polynomial_segments = self._calculate_cubic_polynomial_coefficients(width_profile)
        for i, segment in enumerate(polynomial_segments):
            if i < len(width_profile):
                width_profile[i]['polynomial'] = {
                    'a': segment['a'],
                    'b': segment['b'], 
                    'c': segment['c'],
                    'd': segment['d'],
                    'length': segment['length']
                }
        logger.info(f"计算车道宽度变化：{len(width_profile)}个采样点，{len(polynomial_segments)}个多项式段，总长度{total_length:.2f}m")
        return width_profile
    def _simplify_width_profile(self, width_profile: List[Dict], width_threshold: float = 0.02) -> List[Dict]:
        if len(width_profile) <= 2:
            return width_profile
        simplified = [width_profile[0]]  # 保留第一个点
        for i in range(1, len(width_profile) - 1):
            current_width = width_profile[i]['width']
            prev_width = simplified[-1]['width']
            next_width = width_profile[i + 1]['width']
            width_change_prev = abs(current_width - prev_width)
            width_change_next = abs(next_width - current_width)
            if (width_change_prev > width_threshold or 
                width_change_next > width_threshold or
                self._is_local_extremum(width_profile, i)):
                simplified.append(width_profile[i])
        simplified.append(width_profile[-1])  # 保留最后一个点
        if len(simplified) < len(width_profile):
            logger.info(f"宽度数据简化: {len(width_profile)} -> {len(simplified)} 点 (阈值: {width_threshold}m)")
        return simplified
    def _is_local_extremum(self, width_profile: List[Dict], index: int) -> bool:
        if index <= 0 or index >= len(width_profile) - 1:
            return False
        current_width = width_profile[index]['width']
        prev_width = width_profile[index - 1]['width']
        next_width = width_profile[index + 1]['width']
        is_max = current_width > prev_width and current_width > next_width
        is_min = current_width < prev_width and current_width < next_width
        return is_max or is_min
    def _calculate_width_profile_simple(self, left_coords: List[Tuple[float, float]], 
                                       right_coords: List[Tuple[float, float]]) -> List[Dict]:
        width_profile = []
        current_s = 0.0
        for i, (left_pt, right_pt) in enumerate(zip(left_coords, right_coords)):
            width = math.sqrt((left_pt[0] - right_pt[0])**2 + (left_pt[1] - right_pt[1])**2)
            width = round(width, self.coordinate_precision)
            width_data = {
                's': current_s,
                'width': width,
                'left_point': left_pt,
                'right_point': right_pt
            }
            width_profile.append(width_data)
            if i < len(left_coords) - 1:
                center_current = ((left_pt[0] + right_pt[0]) / 2, (left_pt[1] + right_pt[1]) / 2)
                left_next, right_next = left_coords[i + 1], right_coords[i + 1]
                center_next = ((left_next[0] + right_next[0]) / 2, (left_next[1] + right_next[1]) / 2)
                segment_length = math.sqrt((center_next[0] - center_current[0])**2 + 
                                         (center_next[1] - center_current[1])**2)
                current_s += segment_length
        return width_profile
    def _reconstruct_reference_line(self, center_segments: List[Dict]) -> List[Tuple[float, float]]:
        reference_line = []
        current_x = 0.0
        current_y = 0.0
        current_hdg = 0.0
        for segment in center_segments:
            if 'x' in segment and 'y' in segment:
                current_x = segment['x']
                current_y = segment['y']
            if 'hdg' in segment:
                current_hdg = segment['hdg']
            reference_line.append((current_x, current_y))
            if segment['type'] == 'line':
                length = segment['length']
                end_x = current_x + length * math.cos(current_hdg)
                end_y = current_y + length * math.sin(current_hdg)
                reference_line.append((end_x, end_y))
                current_x = end_x
                current_y = end_y
            elif segment['type'] == 'arc':
                length = segment['length']
                curvature = segment.get('curvature', 0.0)
                if abs(curvature) > 1e-10:  # 避免除零
                    radius = 1.0 / curvature
                    num_points = max(int(length / 2.0), 5)  # 每2米一个点，最少5个点
                    for i in range(1, num_points + 1):
                        s = (i / num_points) * length
                        angle = s / radius
                        if curvature > 0:  # 左转
                            center_x = current_x - radius * math.sin(current_hdg)
                            center_y = current_y + radius * math.cos(current_hdg)
                            point_angle = current_hdg - math.pi/2 + angle
                        else:  # 右转
                            center_x = current_x + radius * math.sin(current_hdg)
                            center_y = current_y - radius * math.cos(current_hdg)
                            point_angle = current_hdg + math.pi/2 - angle
                        point_x = center_x + abs(radius) * math.cos(point_angle)
                        point_y = center_y + abs(radius) * math.sin(point_angle)
                        reference_line.append((point_x, point_y))
                    current_x = reference_line[-1][0]
                    current_y = reference_line[-1][1]
                    current_hdg += length * curvature
                else:
                    end_x = current_x + length * math.cos(current_hdg)
                    end_y = current_y + length * math.sin(current_hdg)
                    reference_line.append((end_x, end_y))
                    current_x = end_x
                    current_y = end_y
        return reference_line
    def _get_reference_point_at_s(self, center_segments: List[Dict], s: float) -> Tuple[Tuple[float, float], float]:
        current_s = 0.0
        current_x = 0.0
        current_y = 0.0
        current_hdg = 0.0
        for segment in center_segments:
            if 'x' in segment and 'y' in segment:
                current_x = segment['x']
                current_y = segment['y']
            if 'hdg' in segment:
                current_hdg = segment['hdg']
            segment_length = segment['length']
            if current_s + segment_length >= s:
                local_s = s - current_s
                if segment['type'] == 'line':
                    point_x = current_x + local_s * math.cos(current_hdg)
                    point_y = current_y + local_s * math.sin(current_hdg)
                    heading = current_hdg
                elif segment['type'] == 'arc':
                    curvature = segment.get('curvature', 0.0)
                    if abs(curvature) > 1e-10:
                        radius = 1.0 / curvature
                        angle = local_s / radius
                        if curvature > 0:  # 左转
                            center_x = current_x - radius * math.sin(current_hdg)
                            center_y = current_y + radius * math.cos(current_hdg)
                            point_angle = current_hdg - math.pi/2 + angle
                        else:  # 右转
                            center_x = current_x + radius * math.sin(current_hdg)
                            center_y = current_y - radius * math.cos(current_hdg)
                            point_angle = current_hdg + math.pi/2 - angle
                        point_x = center_x + abs(radius) * math.cos(point_angle)
                        point_y = center_y + abs(radius) * math.sin(point_angle)
                        heading = current_hdg + local_s * curvature
                    else:
                        point_x = current_x + local_s * math.cos(current_hdg)
                        point_y = current_y + local_s * math.sin(current_hdg)
                        heading = current_hdg
                else:
                    point_x = current_x + local_s * math.cos(current_hdg)
                    point_y = current_y + local_s * math.sin(current_hdg)
                    heading = current_hdg
                return (point_x, point_y), heading
            current_s += segment_length
            if segment['type'] == 'line':
                current_x += segment_length * math.cos(current_hdg)
                current_y += segment_length * math.sin(current_hdg)
            elif segment['type'] == 'arc':
                curvature = segment.get('curvature', 0.0)
                if abs(curvature) > 1e-10:
                    current_hdg += segment_length * curvature
                current_x += segment_length * math.cos(current_hdg)
                current_y += segment_length * math.sin(current_hdg)
        return (current_x, current_y), current_hdg
    def _find_closest_point(self, coords: List[Tuple[float, float]], 
                           target: Tuple[float, float]) -> Tuple[float, float]:
        if not coords:
            return target
        min_dist = float('inf')
        closest_point = coords[0]
        for point in coords:
            dist = math.sqrt((point[0] - target[0])**2 + (point[1] - target[1])**2)
            if dist < min_dist:
                min_dist = dist
                closest_point = point
        return closest_point
    def _find_closest_two_points(self, coords: List[Tuple[float, float]], 
                                target: Tuple[float, float]) -> List[Tuple[float, float]]:
        if not coords:
            return [target, target]
        if len(coords) == 1:
            return [coords[0], coords[0]]
        distances = []
        for i, point in enumerate(coords):
            dist = math.sqrt((point[0] - target[0])**2 + (point[1] - target[1])**2)
            distances.append((dist, i, point))
        distances.sort(key=lambda x: x[0])
        return [distances[0][2], distances[1][2]]
    def _calculate_perpendicular_width(self, left_pt: Tuple[float, float], 
                                     right_pt: Tuple[float, float],
                                     ref_pt: Tuple[float, float], 
                                     ref_heading: float) -> float:
        perp_x = -math.sin(ref_heading)
        perp_y = math.cos(ref_heading)
        left_vec_x = left_pt[0] - ref_pt[0]
        left_vec_y = left_pt[1] - ref_pt[1]
        right_vec_x = right_pt[0] - ref_pt[0]
        right_vec_y = right_pt[1] - ref_pt[1]
        left_proj = left_vec_x * perp_x + left_vec_y * perp_y
        right_proj = right_vec_x * perp_x + right_vec_y * perp_y
        width = abs(left_proj - right_proj)
        logger.debug(f"垂直宽度计算详情: 航向角={ref_heading:.3f}, 垂直向量=({perp_x:.3f},{perp_y:.3f}), "
                    f"左投影={left_proj:.3f}, 右投影={right_proj:.3f}, 原始宽度={width:.6f}")
        if width <= 0.001:
            direct_width = math.sqrt((left_pt[0] - right_pt[0])**2 + (left_pt[1] - right_pt[1])**2)
            logger.warning(f"垂直宽度异常小({width:.6f})，直线距离={direct_width:.3f}，"
                          f"左边界{left_pt}, 右边界{right_pt}, 参考点{ref_pt}")
            if direct_width > 0.1:  # 直线距离大于10cm
                logger.info(f"使用直线距离替代垂直宽度: {direct_width:.3f}")
                width = direct_width
        return round(width, self.coordinate_precision)
    def _calculate_line_intersection_width(self, left_pts: List[Tuple[float, float]], 
                                         right_pts: List[Tuple[float, float]],
                                         ref_pt: Tuple[float, float], 
                                         ref_heading: float) -> float:
        if len(left_pts) < 2 or len(right_pts) < 2:
            left_pt = left_pts[0] if left_pts else ref_pt
            right_pt = right_pts[0] if right_pts else ref_pt
            return self._calculate_perpendicular_width(left_pt, right_pt, ref_pt, ref_heading)
        perp_x = -math.sin(ref_heading)
        perp_y = math.cos(ref_heading)
        left_intersection = self._line_intersection(
            left_pts[0], left_pts[1],  # 左边界直线的两个点
            ref_pt, (ref_pt[0] + perp_x, ref_pt[1] + perp_y)  # 垂线的两个点
        )
        right_intersection = self._line_intersection(
            right_pts[0], right_pts[1],  # 右边界直线的两个点
            ref_pt, (ref_pt[0] + perp_x, ref_pt[1] + perp_y)  # 垂线的两个点
        )
        if left_intersection is None or right_intersection is None:
            logger.warning(f"无法计算直线交点，回退到投影方法")
            left_pt = left_pts[0]
            right_pt = right_pts[0]
            return self._calculate_perpendicular_width(left_pt, right_pt, ref_pt, ref_heading)
        width = math.sqrt((left_intersection[0] - right_intersection[0])**2 + 
                         (left_intersection[1] - right_intersection[1])**2)
        logger.debug(f"直线交点宽度计算: 左交点{left_intersection}, 右交点{right_intersection}, 宽度={width:.6f}")
        if width <= 0.001:
            logger.warning(f"交点宽度异常小({width:.6f})，回退到投影方法")
            left_pt = left_pts[0]
            right_pt = right_pts[0]
            return self._calculate_perpendicular_width(left_pt, right_pt, ref_pt, ref_heading)
        return round(width, self.coordinate_precision)
    def _line_intersection(self, p1: Tuple[float, float], p2: Tuple[float, float],
                          p3: Tuple[float, float], p4: Tuple[float, float]) -> Optional[Tuple[float, float]]:
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-10:
            return None
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        intersection_x = x1 + t * (x2 - x1)
        intersection_y = y1 + t * (y2 - y1)
        return (intersection_x, intersection_y)
    def _fit_polynomial_curves(self, coordinates: List[Tuple[float, float]]) -> List[Dict]:
        if len(coordinates) < 3:
            return self.fit_line_segments(coordinates)
        if len(coordinates) > 20:  # 对于复杂曲线使用分段拟合
            return self._fit_segmented_polynomial_curves(coordinates)
        segments = []
        current_s = 0.0
        coords_array = np.array(coordinates)
        x_coords = coords_array[:, 0]
        y_coords = coords_array[:, 1]
        arc_lengths = self._calculate_arc_lengths(coordinates)
        total_length = arc_lengths[-1]
        if total_length <= 0:
            return self.fit_line_segments(coordinates)
        t_params = arc_lengths / total_length
        try:
            start_heading = self._calculate_precise_heading(coordinates[:min(3, len(coordinates))])
            start_x, start_y = x_coords[0], y_coords[0]
            cos_hdg = math.cos(start_heading)
            sin_hdg = math.sin(start_heading)
            local_u = np.zeros(len(coordinates))
            local_v = np.zeros(len(coordinates))
            for i in range(len(coordinates)):
                dx = x_coords[i] - start_x
                dy = y_coords[i] - start_y
                local_u[i] = dx * cos_hdg + dy * sin_hdg
                local_v[i] = -dx * sin_hdg + dy * cos_hdg
            optimal_degree = self._select_optimal_polynomial_degree(t_params, local_u, local_v)
            weights = self._calculate_fitting_weights(len(coordinates))
            poly_u = np.polyfit(t_params, local_u, optimal_degree, w=weights)
            poly_v = np.polyfit(t_params, local_v, optimal_degree, w=weights)
            fitting_error = self._evaluate_fitting_quality(t_params, local_u, local_v, poly_u, poly_v)
            if fitting_error > self.tolerance and optimal_degree > 2:
                logger.debug(f"拟合误差过大({fitting_error:.3f}m)，降低多项式阶数重新拟合")
                optimal_degree = max(2, optimal_degree - 1)
                poly_u = np.polyfit(t_params, local_u, optimal_degree, w=weights)
                poly_v = np.polyfit(t_params, local_v, optimal_degree, w=weights)
                fitting_error = self._evaluate_fitting_quality(t_params, local_u, local_v, poly_u, poly_v)
            poly_u_padded = np.pad(poly_u[::-1], (0, max(0, 4 - len(poly_u))), 'constant')
            poly_v_padded = np.pad(poly_v[::-1], (0, max(0, 4 - len(poly_v))), 'constant')
            au = float(poly_u_padded[0]) if len(poly_u_padded) > 0 else 0.0
            bu = float(poly_u_padded[1]) if len(poly_u_padded) > 1 else 0.0
            cu = float(poly_u_padded[2]) if len(poly_u_padded) > 2 else 0.0
            du = float(poly_u_padded[3]) if len(poly_u_padded) > 3 else 0.0
            av = float(poly_v_padded[0]) if len(poly_v_padded) > 0 else 0.0
            bv = float(poly_v_padded[1]) if len(poly_v_padded) > 1 else 0.0
            cv = float(poly_v_padded[2]) if len(poly_v_padded) > 2 else 0.0
            dv = float(poly_v_padded[3]) if len(poly_v_padded) > 3 else 0.0
            au, bu, cu, du, av, bv, cv, dv = self._optimize_boundary_conditions(
                local_u, local_v, au, bu, cu, du, av, bv, cv, dv, optimal_degree
            )
            segment = {
                'type': 'parampoly3',
                's': current_s,
                'x': float(x_coords[0]),
                'y': float(y_coords[0]),
                'hdg': start_heading,
                'length': total_length,
                'au': au,
                'bu': bu,
                'cu': cu,
                'du': du,
                'av': av,
                'bv': bv,
                'cv': cv,
                'dv': dv,
                'fitting_error': fitting_error,
                'polynomial_degree': optimal_degree
            }
            segments.append(segment)
            logger.debug(f"高精度ParamPoly3拟合完成，点数: {len(coordinates)}, 长度: {total_length:.2f}m, 阶数: {optimal_degree}, 误差: {fitting_error:.4f}m")
            logger.debug(f"多项式系数 - au:{au:.8f}, bu:{bu:.8f}, cu:{cu:.8f}, du:{du:.8f}")
            logger.debug(f"多项式系数 - av:{av:.8f}, bv:{bv:.8f}, cv:{cv:.8f}, dv:{dv:.8f}")
        except Exception as e:
            logger.warning(f"高精度ParamPoly3拟合失败: {e}，回退到直线拟合")
            segments = self.fit_line_segments(coordinates)
        return segments
    def _fit_spline_curves(self, coordinates: List[Tuple[float, float]]) -> List[Dict]:
        if len(coordinates) < 4:
            return self.fit_line_segments(coordinates)
        segments = []
        current_s = 0.0
        try:
            coords_array = np.array(coordinates)
            smoothing_factor = self.curve_smoothness * len(coordinates) * self.tolerance
            tck, u = splprep([coords_array[:, 0], coords_array[:, 1]], 
                           s=smoothing_factor, k=min(3, len(coordinates)-1))
            num_points = max(len(coordinates), int(len(coordinates) * (2.0 - self.curve_smoothness)))
            u_new = np.linspace(0, 1, num_points)
            spline_coords = splev(u_new, tck)
            spline_x = spline_coords[0]
            spline_y = spline_coords[1]
            spline_x[0] = coords_array[0, 0]  # 固定起点X坐标
            spline_y[0] = coords_array[0, 1]  # 固定起点Y坐标
            spline_x[-1] = coords_array[-1, 0]  # 固定终点X坐标
            spline_y[-1] = coords_array[-1, 1]  # 固定终点Y坐标
            fitted_coords = list(zip(spline_x, spline_y))
            segments = self._fit_adaptive_line_segments(fitted_coords, current_s)
            logger.debug(f"样条拟合完成，原始点数: {len(coordinates)}, 拟合点数: {num_points}, 几何段数: {len(segments)}")
        except Exception as e:
            logger.warning(f"样条拟合失败: {e}，回退到直线拟合")
            segments = self.fit_line_segments(coordinates)
        return segments