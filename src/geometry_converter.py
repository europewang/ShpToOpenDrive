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
    
    def __init__(self, tolerance: float = 3.0, smooth_curves: bool = True, preserve_detail: bool = False, 
                 curve_fitting_mode: str = "parampoly3", polynomial_degree: int = 3, curve_smoothness: float = 0.5,
                 coordinate_precision: int = 3):
        """初始化转换器
        
        Args:
            tolerance: 几何拟合容差（米）
            smooth_curves: 是否启用平滑曲线拟合
            preserve_detail: 是否保留更多细节（减少简化）
            curve_fitting_mode: 曲线拟合模式 ("polyline", "polynomial", "spline", "parampoly3")
            polynomial_degree: 多项式拟合阶数 (2-5)
            curve_smoothness: 曲线平滑度 (0.0-1.0)
            coordinate_precision: 坐标精度（小数位数）
        """
        self.tolerance = tolerance
        self.smooth_curves = smooth_curves
        self.preserve_detail = preserve_detail
        self.curve_fitting_mode = curve_fitting_mode
        self.polynomial_degree = max(2, min(5, polynomial_degree))  # 限制在2-5之间
        self.curve_smoothness = max(0.0, min(1.0, curve_smoothness))  # 限制在0-1之间
        self.coordinate_precision = max(1, min(10, coordinate_precision))  # 限制在1-10之间
        
        # 调整有效容差，减少过拟合
        if preserve_detail:
            self.effective_tolerance = tolerance * 0.8  # 提高从0.3到0.8
        else:
            self.effective_tolerance = tolerance * 1.5  # 进一步增大容差
        self.road_segments = []
        # 添加几何段数量限制
        self.max_segments_per_road = 50
        logger.info(f"几何转换器初始化，容差: {tolerance}m, 有效容差: {self.effective_tolerance}m, 平滑曲线: {smooth_curves}, 保留细节: {preserve_detail}")
    
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
        
        # 根据曲线拟合模式选择转换方法
        if self.curve_fitting_mode == "polyline":
            # 纯折线拟合模式（原有逻辑）
            if len(coordinates) > 50:
                logger.debug(f"检测到高密度坐标（{len(coordinates)}个点），使用保形转换")
                return self._fit_adaptive_line_segments(coordinates)
            elif self.smooth_curves and len(coordinates) >= 3:
                return self.fit_smooth_curve_segments(coordinates)
            else:
                return self.fit_line_segments(coordinates)
        
        elif self.curve_fitting_mode == "polynomial":
            # 多项式曲线拟合模式
            logger.debug(f"使用多项式曲线拟合，阶数: {self.polynomial_degree}, 平滑度: {self.curve_smoothness}")
            return self._fit_polynomial_curves(coordinates)
        
        elif self.curve_fitting_mode == "spline":
            # 样条曲线拟合模式
            logger.debug(f"使用样条曲线拟合，平滑度: {self.curve_smoothness}")
            return self._fit_spline_curves(coordinates)
        
        elif self.curve_fitting_mode == "parampoly3":
            # ParamPoly3曲线拟合模式
            logger.debug(f"使用ParamPoly3曲线拟合，阶数: {self.polynomial_degree}, 平滑度: {self.curve_smoothness}")
            return self._fit_polynomial_curves(coordinates)
        
        else:
            # 默认使用折线拟合
            logger.warning(f"未知的曲线拟合模式: {self.curve_fitting_mode}，使用默认折线拟合")
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
    
    def _calculate_arc_lengths(self, coordinates: List[Tuple[float, float]]) -> np.ndarray:
        """计算弧长参数，提供更精确的参数化
        
        Args:
            coordinates: 坐标点列表
            
        Returns:
            np.ndarray: 累积弧长数组
        """
        arc_lengths = np.zeros(len(coordinates))
        for i in range(1, len(coordinates)):
            dx = coordinates[i][0] - coordinates[i-1][0]
            dy = coordinates[i][1] - coordinates[i-1][1]
            arc_lengths[i] = arc_lengths[i-1] + np.sqrt(dx*dx + dy*dy)
        return arc_lengths
    
    def _calculate_precise_heading(self, coordinates: List[Tuple[float, float]]) -> float:
        """计算精确的起始航向角，使用多个点提高精度
        
        Args:
            coordinates: 坐标点列表（至少2个点）
            
        Returns:
            float: 起始航向角（弧度）
        """
        if len(coordinates) < 2:
            return 0.0
        
        if len(coordinates) == 2:
            dx = coordinates[1][0] - coordinates[0][0]
            dy = coordinates[1][1] - coordinates[0][1]
            return math.atan2(dy, dx)
        
        # 使用前几个点的平均方向
        total_dx = 0.0
        total_dy = 0.0
        weight_sum = 0.0
        
        for i in range(1, min(len(coordinates), 4)):
            dx = coordinates[i][0] - coordinates[0][0]
            dy = coordinates[i][1] - coordinates[0][1]
            distance = np.sqrt(dx*dx + dy*dy)
            
            if distance > 1e-6:
                weight = 1.0 / (i * i)  # 距离越近权重越大
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
        """自适应选择最优多项式阶数
        
        Args:
            t_params: 参数数组
            local_u: 局部u坐标
            local_v: 局部v坐标
            
        Returns:
            int: 最优多项式阶数
        """
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
        """计算拟合权重，给端点更高权重
        
        Args:
            num_points: 点的数量
            
        Returns:
            np.ndarray: 权重数组
        """
        weights = np.ones(num_points)
        
        # 给起点和终点更高权重
        weights[0] = 2.0
        weights[-1] = 2.0
        
        # 给接近端点的点稍高权重
        if num_points > 4:
            weights[1] = 1.5
            weights[-2] = 1.5
        
        return weights
    
    def _evaluate_fitting_quality(self, t_params: np.ndarray, 
                                 local_u: np.ndarray, 
                                 local_v: np.ndarray,
                                 poly_u: np.ndarray, 
                                 poly_v: np.ndarray) -> float:
        """评估拟合质量
        
        Args:
            t_params: 参数数组
            local_u: 局部u坐标
            local_v: 局部v坐标
            poly_u: u方向多项式系数
            poly_v: v方向多项式系数
            
        Returns:
            float: 拟合误差（米）
        """
        try:
            # 计算拟合值
            u_fitted = np.polyval(poly_u, t_params)
            v_fitted = np.polyval(poly_v, t_params)
            
            # 计算残差
            u_residuals = local_u - u_fitted
            v_residuals = local_v - v_fitted
            
            # 计算最大误差和均方根误差
            max_error = np.max(np.sqrt(u_residuals**2 + v_residuals**2))
            rmse = np.sqrt(np.mean(u_residuals**2 + v_residuals**2))
            
            # 返回加权误差（更关注最大误差）
            return 0.7 * max_error + 0.3 * rmse
            
        except Exception:
            return float('inf')
    
    def _optimize_boundary_conditions(self, local_u: np.ndarray, local_v: np.ndarray,
                                    au: float, bu: float, cu: float, du: float,
                                    av: float, bv: float, cv: float, dv: float,
                                    degree: int) -> Tuple[float, float, float, float, float, float, float, float]:
        """优化边界条件处理
        
        Args:
            local_u, local_v: 局部坐标
            au, bu, cu, du: u方向多项式系数
            av, bv, cv, dv: v方向多项式系数
            degree: 多项式阶数
            
        Returns:
            Tuple: 优化后的多项式系数
        """
        # 强制起点为原点
        au = 0.0
        av = 0.0
        
        # 获取终点坐标
        end_u = local_u[-1]
        end_v = local_v[-1]
        
        if degree == 1:
            # 线性情况：直接设置线性系数
            bu = end_u
            bv = end_v
            cu = du = cv = dv = 0.0
        else:
            # 高次多项式：调整系数以确保终点正确
            # 在t=1时：u(1) = au + bu + cu + du = end_u
            #         v(1) = av + bv + cv + dv = end_v
            
            current_sum_u = bu + cu + du
            current_sum_v = bv + cv + dv
            
            # 如果当前和为零，直接设置线性项
            if abs(current_sum_u) < 1e-10:
                bu = end_u
            else:
                # 按比例调整所有非常数项
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
        """分段多项式拟合，用于处理复杂曲线
        
        Args:
            coordinates: 坐标点列表
            
        Returns:
            List[Dict]: ParamPoly3几何段列表
        """
        if len(coordinates) < 6:
            return self._fit_polynomial_curves(coordinates)
        
        segments = []
        current_s = 0.0
        
        # 计算曲率变化点，用于确定分段位置
        curvature_changes = self._detect_curvature_changes(coordinates)
        
        # 根据曲率变化和长度限制确定分段点
        segment_points = self._determine_segment_points(coordinates, curvature_changes)
        
        # 对每个段进行拟合
        for i in range(len(segment_points) - 1):
            start_idx = segment_points[i]
            end_idx = segment_points[i + 1] + 1  # 包含端点
            
            segment_coords = coordinates[start_idx:end_idx]
            
            if len(segment_coords) >= 3:
                # 递归调用单段拟合
                segment_geometries = self._fit_polynomial_curves(segment_coords)
                
                # 调整s坐标
                for geom in segment_geometries:
                    geom['s'] = current_s
                    current_s += geom['length']
                    segments.append(geom)
            else:
                # 点太少，使用直线拟合
                line_segments = self.fit_line_segments(segment_coords)
                for geom in line_segments:
                    geom['s'] = current_s
                    current_s += geom['length']
                    segments.append(geom)
        
        logger.debug(f"分段拟合完成，总段数: {len(segments)}, 原始点数: {len(coordinates)}")
        return segments
    
    def _detect_curvature_changes(self, coordinates: List[Tuple[float, float]]) -> List[int]:
        """检测曲率变化点
        
        Args:
            coordinates: 坐标点列表
            
        Returns:
            List[int]: 曲率变化点的索引列表
        """
        if len(coordinates) < 5:
            return []
        
        curvatures = []
        
        # 计算每个点的曲率
        for i in range(2, len(coordinates) - 2):
            # 使用5点法计算曲率
            p1 = coordinates[i-2]
            p2 = coordinates[i-1]
            p3 = coordinates[i]
            p4 = coordinates[i+1]
            p5 = coordinates[i+2]
            
            # 计算曲率（简化方法）
            curvature = self._calculate_point_curvature([p1, p2, p3, p4, p5])
            curvatures.append(curvature)
        
        # 检测曲率变化点
        change_points = []
        threshold = np.std(curvatures) * 1.5  # 动态阈值
        
        for i in range(1, len(curvatures) - 1):
            if abs(curvatures[i] - curvatures[i-1]) > threshold:
                change_points.append(i + 2)  # 调整索引
        
        return change_points
    
    def _calculate_point_curvature(self, points: List[Tuple[float, float]]) -> float:
        """计算点的曲率
        
        Args:
            points: 5个连续点
            
        Returns:
            float: 曲率值
        """
        if len(points) < 3:
            return 0.0
        
        # 使用三点法计算曲率
        p1, p2, p3 = points[0], points[2], points[4]
        
        # 计算向量
        v1 = (p2[0] - p1[0], p2[1] - p1[1])
        v2 = (p3[0] - p2[0], p3[1] - p2[1])
        
        # 计算叉积和模长
        cross = v1[0] * v2[1] - v1[1] * v2[0]
        norm1 = np.sqrt(v1[0]**2 + v1[1]**2)
        norm2 = np.sqrt(v2[0]**2 + v2[1]**2)
        
        if norm1 * norm2 > 1e-10:
            return abs(cross) / (norm1 * norm2)
        
        return 0.0
    
    def _determine_segment_points(self, coordinates: List[Tuple[float, float]], 
                                curvature_changes: List[int]) -> List[int]:
        """确定分段点
        
        Args:
            coordinates: 坐标点列表
            curvature_changes: 曲率变化点索引
            
        Returns:
            List[int]: 分段点索引列表
        """
        segment_points = [0]  # 起始点
        
        max_segment_length = 15  # 最大段长度
        min_segment_length = 5   # 最小段长度
        
        current_start = 0
        
        for change_point in curvature_changes:
            # 检查段长度是否合适
            if (change_point - current_start >= min_segment_length and 
                change_point - current_start <= max_segment_length):
                segment_points.append(change_point)
                current_start = change_point
            elif change_point - current_start > max_segment_length:
                # 强制分段
                forced_point = current_start + max_segment_length
                segment_points.append(forced_point)
                current_start = forced_point
        
        # 处理剩余部分
        remaining_length = len(coordinates) - 1 - current_start
        if remaining_length > max_segment_length:
            # 需要进一步分段
            while current_start + max_segment_length < len(coordinates) - 1:
                current_start += max_segment_length
                segment_points.append(current_start)
        
        # 添加终点
        if segment_points[-1] != len(coordinates) - 1:
            segment_points.append(len(coordinates) - 1)
        
        return segment_points
    
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
            
            # 根据曲率调整容差，减少过拟合
            adaptive_tolerance = self.effective_tolerance
            if curvature > 0.2:  # 高曲率区域，提高阈值从0.1到0.2
                adaptive_tolerance *= 0.7  # 减少简化程度，从0.5提高到0.7
            elif curvature < 0.05:  # 低曲率区域，提高阈值从0.01到0.05
                adaptive_tolerance *= 4.0  # 增加简化程度，从2.0提高到4.0
            else:  # 中等曲率区域
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
        
        # 如果简化后的点数仍然过多，进一步简化
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
    
    def _limit_segments(self, coordinates: List[Tuple[float, float]], max_segments: int) -> List[Tuple[float, float]]:
        """限制几何段数量，通过均匀采样减少点数
        
        Args:
            coordinates: 坐标点列表
            max_segments: 最大段数
            
        Returns:
            List[Tuple[float, float]]: 限制后的坐标点
        """
        if len(coordinates) <= max_segments:
            return coordinates
        
        # 保留首尾点，中间均匀采样
        result = [coordinates[0]]
        
        # 计算采样间隔
        step = (len(coordinates) - 1) / (max_segments - 1)
        
        for i in range(1, max_segments - 1):
            idx = int(round(i * step))
            if idx < len(coordinates) and coordinates[idx] not in result:
                result.append(coordinates[idx])
        
        result.append(coordinates[-1])
        
        logger.info(f"几何段数量从{len(coordinates)}限制到{len(result)}")
        return result
    
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
                center_coords, width_data = self._calculate_center_line(left_coords, right_coords)
                
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
                              right_coords: List[Tuple[float, float]]) -> Tuple[List[Tuple[float, float]], List[Dict]]:
        """计算两条边界线的中心线和对应的宽度变化，保持复杂形状
        
        Args:
            left_coords: 左边界坐标点
            right_coords: 右边界坐标点
            
        Returns:
            Tuple[List[Tuple[float, float]], List[Dict]]: (中心线坐标点, 宽度变化数据)
        """
        # 使用更密集的采样点来保持复杂形状
        max_points = max(len(left_coords), len(right_coords))
        # 对于点数较少的车道面，大幅增加采样密度以保持曲线形状
        if max_points <= 10:
            target_points = max(max_points * 10, 50)  # 少点数时增加10倍采样
        else:
            target_points = max(max_points * 2, 100)  # 多点数时增加2倍采样
        
        logger.debug(f"车道面中心线计算：原始点数 {max_points}，目标点数 {target_points}")
        
        # 对两条边界线进行高密度插值
        left_interpolated = self._interpolate_coordinates(left_coords, target_points)
        right_interpolated = self._interpolate_coordinates(right_coords, target_points)
        
        center_coords = []
        width_data = []
        current_s = 0.0
        
        for i, (left_pt, right_pt) in enumerate(zip(left_interpolated, right_interpolated)):
            center_x = (left_pt[0] + right_pt[0]) / 2
            center_y = (left_pt[1] + right_pt[1]) / 2
            center_coords.append((center_x, center_y))
            
            # 计算当前点的宽度
            width = math.sqrt((left_pt[0] - right_pt[0])**2 + (left_pt[1] - right_pt[1])**2)
            # 应用坐标精度控制
            width = round(width, self.coordinate_precision)
            
            width_info = {
                's': current_s,
                'width': width,
                'left_point': left_pt,
                'right_point': right_pt,
                'center_point': (center_x, center_y)
            }
            width_data.append(width_info)
            
            # 计算到下一个点的距离（用于s坐标）
            if i < len(left_interpolated) - 1:
                next_left, next_right = left_interpolated[i + 1], right_interpolated[i + 1]
                next_center_x = (next_left[0] + next_right[0]) / 2
                next_center_y = (next_left[1] + next_right[1]) / 2
                
                segment_length = math.sqrt((next_center_x - center_x)**2 + (next_center_y - center_y)**2)
                current_s += segment_length
        
        # 应用自适应简化，但保留更多细节
        if self.preserve_detail and len(center_coords) > 10:
            # 保存原始中心线坐标用于宽度数据简化
            original_center_coords = center_coords.copy()
            
            # 使用更小的容差来保留更多细节
            simplified_coords = self._adaptive_simplify(center_coords)
            logger.debug(f"中心线计算：原始点数 {len(center_coords)}，简化后 {len(simplified_coords)}")
            
            # 对宽度数据也进行相应的简化，保持与中心线的对应关系
            simplified_width_data = self._simplify_width_data(width_data, original_center_coords, simplified_coords)
            
            return simplified_coords, simplified_width_data
        
        return center_coords, width_data
    
    def _simplify_width_data(self, width_data: List[Dict], 
                           original_coords: List[Tuple[float, float]], 
                           simplified_coords: List[Tuple[float, float]]) -> List[Dict]:
        """简化宽度数据，保持与简化后中心线的对应关系
        
        Args:
            width_data: 原始宽度数据
            original_coords: 原始中心线坐标
            simplified_coords: 简化后的中心线坐标
            
        Returns:
            List[Dict]: 简化后的宽度数据
        """
        if not width_data or not simplified_coords:
            return width_data
    
    def _smooth_width_profile_bezier(self, width_profile: List[Dict]) -> List[Dict]:
        """使用贝塞尔曲线平滑宽度数据
        
        Args:
            width_profile: 原始宽度数据
            
        Returns:
            List[Dict]: 平滑后的宽度数据
        """
        if len(width_profile) < 4:
            return width_profile
        
        try:
            # 提取s坐标和宽度值
            s_values = [item['s'] for item in width_profile]
            width_values = [item['width'] for item in width_profile]
            
            # 使用三次贝塞尔曲线平滑
            smoothed_widths = self._bezier_smooth(s_values, width_values)
            
            # 更新宽度数据
            for i, item in enumerate(width_profile):
                if i < len(smoothed_widths):
                    item['width'] = max(0.1, smoothed_widths[i])  # 确保宽度不为负
            
            return width_profile
            
        except Exception as e:
            logger.warning(f"贝塞尔曲线平滑失败: {e}，使用原始数据")
            return width_profile
    
    def _calculate_cubic_polynomial_coefficients(self, width_profile: List[Dict]) -> List[Dict]:
        """计算宽度变化的三次多项式系数
        
        优化策略：
        1. 检测宽度变化阈值，合并变化微小的段
        2. 减少多项式段数量，避免过拟合
        3. 对于等宽或近似等宽的区域使用常数宽度
        
        Args:
            width_profile: 宽度变化数据
            
        Returns:
            List[Dict]: 包含三次多项式系数的宽度段数据
        """
        if len(width_profile) < 2:
            return []
        
        # 首先检测并合并宽度变化微小的相邻点
        simplified_profile = self._simplify_width_profile(width_profile)
        
        polynomial_segments = []
        
        for i in range(len(simplified_profile) - 1):
            current_point = simplified_profile[i]
            next_point = simplified_profile[i + 1]
            
            s0 = current_point['s']
            s1 = next_point['s']
            w0 = current_point['width']
            w1 = next_point['width']
            
            # 计算段长度
            ds = s1 - s0
            if ds <= 0:
                continue
            
            # 计算导数（斜率）
            if i == 0:
                # 第一段：使用前向差分
                if len(simplified_profile) > 2:
                    dw0 = (simplified_profile[i + 1]['width'] - w0) / (simplified_profile[i + 1]['s'] - s0)
                else:
                    dw0 = 0
            else:
                # 中间段：使用中心差分
                dw0 = (w1 - simplified_profile[i - 1]['width']) / (s1 - simplified_profile[i - 1]['s'])
            
            if i == len(simplified_profile) - 2:
                # 最后一段：使用后向差分
                if len(simplified_profile) > 2:
                    dw1 = (w1 - simplified_profile[i]['width']) / (s1 - simplified_profile[i]['s'])
                else:
                    dw1 = 0
            else:
                # 中间段：使用中心差分
                dw1 = (simplified_profile[i + 2]['width'] - w0) / (simplified_profile[i + 2]['s'] - s0)
            
            # 计算三次多项式系数
            # w(s) = a + b*(s-s0) + c*(s-s0)^2 + d*(s-s0)^3
            # 边界条件：w(s0) = w0, w(s1) = w1, w'(s0) = dw0, w'(s1) = dw1
            
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
        """使用贝塞尔曲线进行数据平滑
        
        Args:
            s_values: s坐标值
            width_values: 宽度值
            
        Returns:
            List[float]: 平滑后的宽度值
        """
        if len(width_values) < 4:
            return width_values
        
        smoothed = []
        
        # 对于每个数据段，使用三次贝塞尔曲线
        for i in range(len(width_values)):
            if i == 0:
                # 第一个点保持不变
                smoothed.append(width_values[i])
            elif i == len(width_values) - 1:
                # 最后一个点保持不变
                smoothed.append(width_values[i])
            else:
                # 中间点使用贝塞尔插值
                # 选择控制点
                p0_idx = max(0, i - 1)
                p1_idx = i
                p2_idx = min(len(width_values) - 1, i + 1)
                p3_idx = min(len(width_values) - 1, i + 2)
                
                p0 = width_values[p0_idx]
                p1 = width_values[p1_idx]
                p2 = width_values[p2_idx]
                p3 = width_values[p3_idx]
                
                # 计算控制点权重
                # 使用Catmull-Rom样条的控制点计算方法
                tension = 0.5  # 张力参数，控制平滑程度
                
                # 计算切线
                if i > 0 and i < len(width_values) - 1:
                    # 前向差分和后向差分的平均
                    tangent_in = (p2 - p0) * tension
                    tangent_out = (p3 - p1) * tension
                    
                    # 使用Hermite插值
                    t = 0.5  # 插值参数
                    h1 = 2*t**3 - 3*t**2 + 1
                    h2 = -2*t**3 + 3*t**2
                    h3 = t**3 - 2*t**2 + t
                    h4 = t**3 - t**2
                    
                    smoothed_value = h1*p1 + h2*p2 + h3*tangent_in + h4*tangent_out
                    
                    # 限制平滑后的值在合理范围内
                    min_val = min(p0, p1, p2, p3) * 0.8
                    max_val = max(p0, p1, p2, p3) * 1.2
                    smoothed_value = max(min_val, min(max_val, smoothed_value))
                    
                    smoothed.append(smoothed_value)
                else:
                    smoothed.append(p1)
        
        return smoothed
        
    def _simplify_width_data(self, width_data: List[Dict], original_coords: List[Tuple[float, float]], 
                            simplified_coords: List[Tuple[float, float]]) -> List[Dict]:
        """根据简化后的坐标调整宽度数据
        
        Args:
            width_data: 原始宽度数据
            original_coords: 原始中心线坐标
            simplified_coords: 简化后的中心线坐标
            
        Returns:
            List[Dict]: 简化后的宽度数据
        """
        if not width_data or not simplified_coords:
            return width_data
         
        simplified_width_data = []
        
        for simplified_pt in simplified_coords:
            # 找到最接近简化点的原始点索引
            min_distance = float('inf')
            closest_index = 0
            
            for i, original_pt in enumerate(original_coords):
                distance = math.sqrt((simplified_pt[0] - original_pt[0])**2 + 
                                   (simplified_pt[1] - original_pt[1])**2)
                if distance < min_distance:
                    min_distance = distance
                    closest_index = i
            
            # 使用最接近的宽度数据
            if closest_index < len(width_data):
                width_info = width_data[closest_index].copy()
                # 确保center_point是元组类型
                width_info['center_point'] = tuple(simplified_pt) if not isinstance(simplified_pt, tuple) else simplified_pt
                simplified_width_data.append(width_info)
        
        # 重新计算s坐标以保持连续性
        current_s = 0.0
        for i, width_info in enumerate(simplified_width_data):
            width_info['s'] = current_s
            
            if i < len(simplified_width_data) - 1:
                current_pt = width_info['center_point']
                next_pt = simplified_width_data[i + 1]['center_point']
                # 确保坐标是元组类型
                if isinstance(current_pt, (list, tuple)) and isinstance(next_pt, (list, tuple)):
                    segment_length = math.sqrt((next_pt[0] - current_pt[0])**2 + 
                                             (next_pt[1] - current_pt[1])**2)
                    current_s += segment_length
        
        logger.debug(f"宽度数据简化：原始 {len(width_data)} 个点，简化后 {len(simplified_width_data)} 个点")
        return simplified_width_data
    
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
        
        基于道路参考线几何段计算准确的s坐标和垂直车道宽度。
        
        Args:
            left_coords: 左边界坐标
            right_coords: 右边界坐标
            center_segments: 中心线几何段
            
        Returns:
            List[Dict]: 宽度变化数据，包含s坐标、宽度、左右边界点
        """
        width_profile = []
        
        # 确保坐标点数相同
        if len(left_coords) != len(right_coords):
            target_points = max(len(left_coords), len(right_coords))
            left_coords = self._interpolate_coordinates(left_coords, target_points)
            right_coords = self._interpolate_coordinates(right_coords, target_points)
        
        # 从几何段重建参考线坐标点
        reference_line = self._reconstruct_reference_line(center_segments)
        
        if not reference_line:
            logger.warning("无法从几何段重建参考线，使用简化计算")
            return self._calculate_width_profile_simple(left_coords, right_coords)
        
        # 计算总的参考线长度
        total_length = sum(segment['length'] for segment in center_segments)
        
        # 优化采样策略：基于道路长度自适应确定采样点数量，避免过拟合
        # 采用更合理的采样密度，减少控制点数量
        base_samples = min(len(left_coords), len(right_coords))  # 使用较少的边界点数作为基准
        
        # 根据道路长度动态调整采样密度
        if total_length <= 50:  # 短道路：每20-25米一个采样点
            samples_by_length = max(int(total_length / 25), 3)
        elif total_length <= 200:  # 中等道路：每30-40米一个采样点
            samples_by_length = max(int(total_length / 35), 6)
        else:  # 长道路：每50米一个采样点
            samples_by_length = max(int(total_length / 50), 8)
        
        # 限制最大采样点数量，避免过拟合
        max_samples = min(20, base_samples)  # 最多20个采样点
        num_samples = min(max(samples_by_length, 3), max_samples)  # 至少3个点，最多max_samples个点
        
        sample_interval = total_length / (num_samples - 1) if num_samples > 1 else 0
        
        for i in range(num_samples):
            current_s = i * sample_interval
            
            # 在参考线上找到对应的位置和方向
            ref_point, ref_heading = self._get_reference_point_at_s(center_segments, current_s)
            
            if ref_point is None:
                logger.warning(f"无法在s={current_s:.2f}处找到参考点")
                continue
            
            # 找到最接近参考点的左右边界点（使用新的两点方法）
            left_pts = self._find_closest_two_points(left_coords, ref_point)
            right_pts = self._find_closest_two_points(right_coords, ref_point)
            
            # 计算垂直于参考线的车道宽度（使用直线交点方法）
            width = self._calculate_line_intersection_width(left_pts, right_pts, ref_point, ref_heading)
            
            # 添加详细的宽度计算日志
            logger.debug(f"宽度计算 - s={current_s:.2f}: 左边界{left_pts}, 右边界{right_pts}, 参考点{ref_point}, 宽度={width:.3f}")
            
            # 检查宽度为0的情况
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
        
        # 应用贝塞尔曲线平滑
        if len(width_profile) > 3:
            width_profile = self._smooth_width_profile_bezier(width_profile)
        
        # 计算三次多项式系数
        polynomial_segments = self._calculate_cubic_polynomial_coefficients(width_profile)
        
        # 将多项式系数添加到width_profile中
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
        """简化宽度变化数据，合并变化微小的相邻点
        
        Args:
            width_profile: 原始宽度变化数据
            width_threshold: 宽度变化阈值（米），默认0.05米
            
        Returns:
            List[Dict]: 简化后的宽度变化数据
        """
        if len(width_profile) <= 2:
            return width_profile
        
        simplified = [width_profile[0]]  # 保留第一个点
        
        for i in range(1, len(width_profile) - 1):
            current_width = width_profile[i]['width']
            prev_width = simplified[-1]['width']
            next_width = width_profile[i + 1]['width']
            
            # 检查当前点是否为显著的宽度变化点
            width_change_prev = abs(current_width - prev_width)
            width_change_next = abs(next_width - current_width)
            
            # 如果宽度变化显著，或者是局部极值点，则保留
            if (width_change_prev > width_threshold or 
                width_change_next > width_threshold or
                self._is_local_extremum(width_profile, i)):
                simplified.append(width_profile[i])
        
        simplified.append(width_profile[-1])  # 保留最后一个点
        
        if len(simplified) < len(width_profile):
            logger.info(f"宽度数据简化: {len(width_profile)} -> {len(simplified)} 点 (阈值: {width_threshold}m)")
        return simplified
    
    def _is_local_extremum(self, width_profile: List[Dict], index: int) -> bool:
        """检查指定索引的点是否为局部极值点（最大值或最小值）
        
        Args:
            width_profile: 宽度变化数据
            index: 要检查的点的索引
            
        Returns:
            bool: 是否为局部极值点
        """
        if index <= 0 or index >= len(width_profile) - 1:
            return False
        
        current_width = width_profile[index]['width']
        prev_width = width_profile[index - 1]['width']
        next_width = width_profile[index + 1]['width']
        
        # 检查是否为局部最大值或最小值
        is_max = current_width > prev_width and current_width > next_width
        is_min = current_width < prev_width and current_width < next_width
        
        return is_max or is_min
    
    def _calculate_width_profile_simple(self, left_coords: List[Tuple[float, float]], 
                                       right_coords: List[Tuple[float, float]]) -> List[Dict]:
        """简化的车道宽度计算（回退方案）
        
        Args:
            left_coords: 左边界坐标
            right_coords: 右边界坐标
            
        Returns:
            List[Dict]: 宽度变化数据
        """
        width_profile = []
        current_s = 0.0
        
        for i, (left_pt, right_pt) in enumerate(zip(left_coords, right_coords)):
            width = math.sqrt((left_pt[0] - right_pt[0])**2 + (left_pt[1] - right_pt[1])**2)
            # 应用坐标精度控制
            width = round(width, self.coordinate_precision)
            
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
    
    def _reconstruct_reference_line(self, center_segments: List[Dict]) -> List[Tuple[float, float]]:
        """从几何段重建参考线坐标点
        
        Args:
            center_segments: 中心线几何段
            
        Returns:
            List[Tuple[float, float]]: 参考线坐标点
        """
        reference_line = []
        current_x = 0.0
        current_y = 0.0
        current_hdg = 0.0
        
        for segment in center_segments:
            # 更新起点坐标
            if 'x' in segment and 'y' in segment:
                current_x = segment['x']
                current_y = segment['y']
            if 'hdg' in segment:
                current_hdg = segment['hdg']
            
            # 添加起点
            reference_line.append((current_x, current_y))
            
            # 根据几何类型生成点
            if segment['type'] == 'line':
                # 直线段：在终点添加一个点
                length = segment['length']
                end_x = current_x + length * math.cos(current_hdg)
                end_y = current_y + length * math.sin(current_hdg)
                reference_line.append((end_x, end_y))
                
                # 更新当前位置
                current_x = end_x
                current_y = end_y
                
            elif segment['type'] == 'arc':
                # 圆弧段：生成多个中间点
                length = segment['length']
                curvature = segment.get('curvature', 0.0)
                
                if abs(curvature) > 1e-10:  # 避免除零
                    radius = 1.0 / curvature
                    # 生成圆弧上的点
                    num_points = max(int(length / 2.0), 5)  # 每2米一个点，最少5个点
                    
                    for i in range(1, num_points + 1):
                        s = (i / num_points) * length
                        angle = s / radius
                        
                        # 计算圆弧上的点
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
                    
                    # 更新当前位置和方向
                    current_x = reference_line[-1][0]
                    current_y = reference_line[-1][1]
                    current_hdg += length * curvature
                else:
                    # 曲率为0，按直线处理
                    end_x = current_x + length * math.cos(current_hdg)
                    end_y = current_y + length * math.sin(current_hdg)
                    reference_line.append((end_x, end_y))
                    current_x = end_x
                    current_y = end_y
        
        return reference_line
    
    def _get_reference_point_at_s(self, center_segments: List[Dict], s: float) -> Tuple[Tuple[float, float], float]:
        """获取参考线上s位置的点和方向
        
        Args:
            center_segments: 中心线几何段
            s: 沿参考线的距离
            
        Returns:
            Tuple[Tuple[float, float], float]: (坐标点, 方向角)
        """
        current_s = 0.0
        current_x = 0.0
        current_y = 0.0
        current_hdg = 0.0
        
        for segment in center_segments:
            # 更新起点
            if 'x' in segment and 'y' in segment:
                current_x = segment['x']
                current_y = segment['y']
            if 'hdg' in segment:
                current_hdg = segment['hdg']
            
            segment_length = segment['length']
            
            if current_s + segment_length >= s:
                # 目标点在当前段内
                local_s = s - current_s
                
                if segment['type'] == 'line':
                    # 直线段
                    point_x = current_x + local_s * math.cos(current_hdg)
                    point_y = current_y + local_s * math.sin(current_hdg)
                    heading = current_hdg
                    
                elif segment['type'] == 'arc':
                    # 圆弧段
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
                        # 曲率为0，按直线处理
                        point_x = current_x + local_s * math.cos(current_hdg)
                        point_y = current_y + local_s * math.sin(current_hdg)
                        heading = current_hdg
                else:
                    # 未知类型，按直线处理
                    point_x = current_x + local_s * math.cos(current_hdg)
                    point_y = current_y + local_s * math.sin(current_hdg)
                    heading = current_hdg
                
                return (point_x, point_y), heading
            
            # 移动到下一段
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
        
        # 如果s超出范围，返回最后一个点
        return (current_x, current_y), current_hdg
    
    def _find_closest_point(self, coords: List[Tuple[float, float]], 
                           target: Tuple[float, float]) -> Tuple[float, float]:
        """找到最接近目标点的坐标
        
        Args:
            coords: 坐标点列表
            target: 目标点
            
        Returns:
            Tuple[float, float]: 最接近的坐标点
        """
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
        """找到最接近目标点的两个坐标点
        
        Args:
            coords: 坐标点列表
            target: 目标点
            
        Returns:
            List[Tuple[float, float]]: 最接近的两个坐标点
        """
        if not coords:
            return [target, target]
        
        if len(coords) == 1:
            return [coords[0], coords[0]]
        
        # 计算所有点到目标点的距离
        distances = []
        for i, point in enumerate(coords):
            dist = math.sqrt((point[0] - target[0])**2 + (point[1] - target[1])**2)
            distances.append((dist, i, point))
        
        # 按距离排序
        distances.sort(key=lambda x: x[0])
        
        # 返回最近的两个点
        return [distances[0][2], distances[1][2]]
    
    def _calculate_perpendicular_width(self, left_pt: Tuple[float, float], 
                                     right_pt: Tuple[float, float],
                                     ref_pt: Tuple[float, float], 
                                     ref_heading: float) -> float:
        """计算垂直于参考线的车道宽度
        
        Args:
            left_pt: 左边界点
            right_pt: 右边界点
            ref_pt: 参考点
            ref_heading: 参考方向角
            
        Returns:
            float: 垂直车道宽度（按coordinate_precision精度舍入）
        """
        # 计算参考线的垂直方向向量
        perp_x = -math.sin(ref_heading)
        perp_y = math.cos(ref_heading)
        
        # 计算左右边界点到参考点的向量
        left_vec_x = left_pt[0] - ref_pt[0]
        left_vec_y = left_pt[1] - ref_pt[1]
        right_vec_x = right_pt[0] - ref_pt[0]
        right_vec_y = right_pt[1] - ref_pt[1]
        
        # 计算在垂直方向上的投影
        left_proj = left_vec_x * perp_x + left_vec_y * perp_y
        right_proj = right_vec_x * perp_x + right_vec_y * perp_y
        
        # 车道宽度是左右投影的差值的绝对值
        width = abs(left_proj - right_proj)
        
        # 添加详细的计算过程日志
        logger.debug(f"垂直宽度计算详情: 航向角={ref_heading:.3f}, 垂直向量=({perp_x:.3f},{perp_y:.3f}), "
                    f"左投影={left_proj:.3f}, 右投影={right_proj:.3f}, 原始宽度={width:.6f}")
        
        # 检查异常情况
        if width <= 0.001:
            # 计算直线距离作为备选
            direct_width = math.sqrt((left_pt[0] - right_pt[0])**2 + (left_pt[1] - right_pt[1])**2)
            logger.warning(f"垂直宽度异常小({width:.6f})，直线距离={direct_width:.3f}，"
                          f"左边界{left_pt}, 右边界{right_pt}, 参考点{ref_pt}")
            
            # 如果垂直宽度异常但直线距离正常，使用直线距离
            if direct_width > 0.1:  # 直线距离大于10cm
                logger.info(f"使用直线距离替代垂直宽度: {direct_width:.3f}")
                width = direct_width
        
        # 应用坐标精度控制
        return round(width, self.coordinate_precision)
    
    def _calculate_line_intersection_width(self, left_pts: List[Tuple[float, float]], 
                                         right_pts: List[Tuple[float, float]],
                                         ref_pt: Tuple[float, float], 
                                         ref_heading: float) -> float:
        """计算垂直于参考线的车道宽度（使用直线交点方法）
        
        Args:
            left_pts: 左边界的两个点
            right_pts: 右边界的两个点
            ref_pt: 参考点
            ref_heading: 参考方向角
            
        Returns:
            float: 垂直车道宽度（按coordinate_precision精度舍入）
        """
        if len(left_pts) < 2 or len(right_pts) < 2:
            # 回退到原有方法
            left_pt = left_pts[0] if left_pts else ref_pt
            right_pt = right_pts[0] if right_pts else ref_pt
            return self._calculate_perpendicular_width(left_pt, right_pt, ref_pt, ref_heading)
        
        # 计算垂直于参考线的方向向量
        perp_x = -math.sin(ref_heading)
        perp_y = math.cos(ref_heading)
        
        # 构造通过参考点的垂线
        # 垂线方程: (x - ref_pt[0]) / perp_x = (y - ref_pt[1]) / perp_y
        
        # 计算左边界直线与垂线的交点
        left_intersection = self._line_intersection(
            left_pts[0], left_pts[1],  # 左边界直线的两个点
            ref_pt, (ref_pt[0] + perp_x, ref_pt[1] + perp_y)  # 垂线的两个点
        )
        
        # 计算右边界直线与垂线的交点
        right_intersection = self._line_intersection(
            right_pts[0], right_pts[1],  # 右边界直线的两个点
            ref_pt, (ref_pt[0] + perp_x, ref_pt[1] + perp_y)  # 垂线的两个点
        )
        
        # 如果无法计算交点，回退到原有方法
        if left_intersection is None or right_intersection is None:
            logger.warning(f"无法计算直线交点，回退到投影方法")
            left_pt = left_pts[0]
            right_pt = right_pts[0]
            return self._calculate_perpendicular_width(left_pt, right_pt, ref_pt, ref_heading)
        
        # 计算两个交点之间的距离
        width = math.sqrt((left_intersection[0] - right_intersection[0])**2 + 
                         (left_intersection[1] - right_intersection[1])**2)
        
        # 添加详细的计算过程日志
        logger.debug(f"直线交点宽度计算: 左交点{left_intersection}, 右交点{right_intersection}, 宽度={width:.6f}")
        
        # 检查异常情况
        if width <= 0.001:
            logger.warning(f"交点宽度异常小({width:.6f})，回退到投影方法")
            left_pt = left_pts[0]
            right_pt = right_pts[0]
            return self._calculate_perpendicular_width(left_pt, right_pt, ref_pt, ref_heading)
        
        # 应用坐标精度控制
        return round(width, self.coordinate_precision)
    
    def _line_intersection(self, p1: Tuple[float, float], p2: Tuple[float, float],
                          p3: Tuple[float, float], p4: Tuple[float, float]) -> Optional[Tuple[float, float]]:
        """计算两条直线的交点
        
        Args:
            p1, p2: 第一条直线上的两个点
            p3, p4: 第二条直线上的两个点
            
        Returns:
            Optional[Tuple[float, float]]: 交点坐标，如果平行则返回None
        """
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4
        
        # 计算直线的方向向量
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        
        # 检查是否平行
        if abs(denom) < 1e-10:
            return None
        
        # 计算交点
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        
        intersection_x = x1 + t * (x2 - x1)
        intersection_y = y1 + t * (y2 - y1)
        
        return (intersection_x, intersection_y)
    
    def _fit_polynomial_curves(self, coordinates: List[Tuple[float, float]]) -> List[Dict]:
        """使用高精度多项式拟合曲线段，直接生成ParamPoly3几何类型
        
        优化改进：
        1. 自适应分段拟合，处理复杂曲线
        2. 使用弧长参数化，提高拟合精度
        3. 添加拟合质量评估和误差控制
        4. 优化边界条件处理
        5. 自适应多项式阶数选择
        
        Args:
            coordinates: 坐标点列表
            
        Returns:
            List[Dict]: ParamPoly3几何段列表
        """
        if len(coordinates) < 3:
            return self.fit_line_segments(coordinates)
        
        # 检测是否需要分段拟合
        if len(coordinates) > 20:  # 对于复杂曲线使用分段拟合
            return self._fit_segmented_polynomial_curves(coordinates)
        
        segments = []
        current_s = 0.0
        
        # 将坐标转换为numpy数组
        coords_array = np.array(coordinates)
        x_coords = coords_array[:, 0]
        y_coords = coords_array[:, 1]
        
        # 计算弧长参数（更精确的参数化）
        arc_lengths = self._calculate_arc_lengths(coordinates)
        total_length = arc_lengths[-1]
        
        if total_length <= 0:
            return self.fit_line_segments(coordinates)
        
        # 归一化弧长参数
        t_params = arc_lengths / total_length
        
        try:
            # 计算起始点的航向角（使用更多点提高精度）
            start_heading = self._calculate_precise_heading(coordinates[:min(3, len(coordinates))])
            
            # 将坐标转换为局部坐标系
            start_x, start_y = x_coords[0], y_coords[0]
            cos_hdg = math.cos(start_heading)
            sin_hdg = math.sin(start_heading)
            
            # 转换为局部坐标系
            local_u = np.zeros(len(coordinates))
            local_v = np.zeros(len(coordinates))
            
            for i in range(len(coordinates)):
                dx = x_coords[i] - start_x
                dy = y_coords[i] - start_y
                local_u[i] = dx * cos_hdg + dy * sin_hdg
                local_v[i] = -dx * sin_hdg + dy * cos_hdg
            
            # 自适应选择最优多项式阶数
            optimal_degree = self._select_optimal_polynomial_degree(t_params, local_u, local_v)
            
            # 使用加权最小二乘法进行拟合（给端点更高权重）
            weights = self._calculate_fitting_weights(len(coordinates))
            
            # 对局部坐标进行加权多项式拟合
            poly_u = np.polyfit(t_params, local_u, optimal_degree, w=weights)
            poly_v = np.polyfit(t_params, local_v, optimal_degree, w=weights)
            
            # 评估拟合质量
            fitting_error = self._evaluate_fitting_quality(t_params, local_u, local_v, poly_u, poly_v)
            
            # 如果拟合误差过大，降低阶数重新拟合
            if fitting_error > self.tolerance and optimal_degree > 2:
                logger.debug(f"拟合误差过大({fitting_error:.3f}m)，降低多项式阶数重新拟合")
                optimal_degree = max(2, optimal_degree - 1)
                poly_u = np.polyfit(t_params, local_u, optimal_degree, w=weights)
                poly_v = np.polyfit(t_params, local_v, optimal_degree, w=weights)
                fitting_error = self._evaluate_fitting_quality(t_params, local_u, local_v, poly_u, poly_v)
            
            # 转换系数格式
            poly_u_padded = np.pad(poly_u[::-1], (0, max(0, 4 - len(poly_u))), 'constant')
            poly_v_padded = np.pad(poly_v[::-1], (0, max(0, 4 - len(poly_v))), 'constant')
            
            # 提取系数
            au = float(poly_u_padded[0]) if len(poly_u_padded) > 0 else 0.0
            bu = float(poly_u_padded[1]) if len(poly_u_padded) > 1 else 0.0
            cu = float(poly_u_padded[2]) if len(poly_u_padded) > 2 else 0.0
            du = float(poly_u_padded[3]) if len(poly_u_padded) > 3 else 0.0
            
            av = float(poly_v_padded[0]) if len(poly_v_padded) > 0 else 0.0
            bv = float(poly_v_padded[1]) if len(poly_v_padded) > 1 else 0.0
            cv = float(poly_v_padded[2]) if len(poly_v_padded) > 2 else 0.0
            dv = float(poly_v_padded[3]) if len(poly_v_padded) > 3 else 0.0
            
            # 优化边界条件处理
            au, bu, cu, du, av, bv, cv, dv = self._optimize_boundary_conditions(
                local_u, local_v, au, bu, cu, du, av, bv, cv, dv, optimal_degree
            )
            
            # 创建ParamPoly3几何段
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
        """使用样条曲线拟合
        
        Args:
            coordinates: 坐标点列表
            
        Returns:
            List[Dict]: 样条曲线段列表
        """
        if len(coordinates) < 4:
            return self.fit_line_segments(coordinates)
        
        segments = []
        current_s = 0.0
        
        try:
            # 将坐标转换为numpy数组
            coords_array = np.array(coordinates)
            
            # 计算样条平滑参数
            smoothing_factor = self.curve_smoothness * len(coordinates) * self.tolerance
            
            # 使用scipy的样条插值
            tck, u = splprep([coords_array[:, 0], coords_array[:, 1]], 
                           s=smoothing_factor, k=min(3, len(coordinates)-1))
            
            # 根据平滑度确定输出点数量
            num_points = max(len(coordinates), int(len(coordinates) * (2.0 - self.curve_smoothness)))
            u_new = np.linspace(0, 1, num_points)
            
            # 计算样条曲线上的点
            spline_coords = splev(u_new, tck)
            
            # 强制固定起点和终点与原始坐标一致
            spline_x = spline_coords[0]
            spline_y = spline_coords[1]
            spline_x[0] = coords_array[0, 0]  # 固定起点X坐标
            spline_y[0] = coords_array[0, 1]  # 固定起点Y坐标
            spline_x[-1] = coords_array[-1, 0]  # 固定终点X坐标
            spline_y[-1] = coords_array[-1, 1]  # 固定终点Y坐标
            
            fitted_coords = list(zip(spline_x, spline_y))
            
            # 使用自适应直线段拟合生成最终几何段
            segments = self._fit_adaptive_line_segments(fitted_coords, current_s)
            
            logger.debug(f"样条拟合完成，原始点数: {len(coordinates)}, 拟合点数: {num_points}, 几何段数: {len(segments)}")
            
        except Exception as e:
            logger.warning(f"样条拟合失败: {e}，回退到直线拟合")
            segments = self.fit_line_segments(coordinates)
        
        return segments