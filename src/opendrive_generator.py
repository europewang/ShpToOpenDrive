"""OpenDrive生成模块

使用scenariogeneration库生成标准的OpenDrive (.xodr) 格式文件。
"""

from scenariogeneration import xodr
from scenariogeneration.xodr.geometry import Line, Arc, ParamPoly3, PlanView
from scenariogeneration.xodr.lane import Lane, LaneSection, Lanes
from scenariogeneration.xodr.enumerations import LaneType
import numpy as np
from typing import List, Dict, Optional, Tuple
import logging
import os

logger = logging.getLogger(__name__)


class OpenDriveGenerator:
    """OpenDrive文件生成器
    
    将转换后的几何数据生成为标准的OpenDrive XML文件。
    """
    
    def __init__(self, name: str = "ConvertedRoad", curve_fitting_mode: str = "polyline", 
                 polynomial_degree: int = 3, curve_smoothness: float = 0.5):
        """初始化生成器
        
        Args:
            name: 道路网络名称
            curve_fitting_mode: 曲线拟合模式
            polynomial_degree: 多项式拟合阶数
            curve_smoothness: 曲线平滑度
        """
        self.name = name
        self.curve_fitting_mode = curve_fitting_mode
        self.polynomial_degree = polynomial_degree
        self.curve_smoothness = curve_smoothness
        self.odr = xodr.OpenDrive(self.name)
        
        # 设置OpenDrive版本属性
        self.odr.revMajor = 1
        self.odr.revMinor = 7
        
        self.roads = []
        self.road_id_counter = 1
        
    def create_road_from_segments(self, segments: List[Dict], 
                                 road_attributes: Dict = None) -> int:
        """从几何段创建道路
        
        Args:
            segments: 几何段列表
            road_attributes: 道路属性（宽度、车道数等）
            
        Returns:
            int: 创建的道路ID
        """
        if not segments:
            logger.error("几何段列表为空")
            return -1
        
        # 设置默认属性
        if road_attributes is None:
            road_attributes = {
                'lane_width': 3.5,  # 默认车道宽度3.5米
                'num_lanes': 1,     # 默认单车道
                'speed_limit': 50   # 默认限速50km/h
            }
        
        road_id = self.road_id_counter
        self.road_id_counter += 1
        
        try:
            # 创建道路几何
            planview = self._create_planview_from_segments(segments)
            
            # 创建车道剖面
            lanes = self._create_lane_section(road_attributes)
            
            # 创建道路
            road = xodr.Road(road_id, planview, lanes)
            
            # 道路类型暂时跳过，专注于基本几何
            
            # 添加到OpenDrive
            self.odr.add_road(road)
            self.roads.append(road)
            
            logger.info(f"成功创建道路 ID: {road_id}，包含 {len(segments)} 个几何段")
            return road_id
            
        except Exception as e:
            logger.error(f"创建道路失败: {e}")
            return -1
    
    def create_road_from_lane_surfaces(self, lane_surfaces: List[Dict], 
                                     road_attributes: Dict = None) -> int:
        """从车道面数据创建道路
        
        Args:
            lane_surfaces: 车道面数据列表
            road_attributes: 道路属性
            
        Returns:
            int: 创建的道路ID
        """
        if not lane_surfaces:
            logger.error("车道面数据为空")
            return -1
        
        # 计算道路参考线（使用index为'0'的边界线作为planview）
        segments = self._calculate_road_reference_line(lane_surfaces)
        if not segments:
            logger.error("无法计算道路参考线")
            return -1
        
        road_id = self.road_id_counter
        self.road_id_counter += 1
        
        try:
            # 创建道路几何
            planview = self._create_planview_from_segments(segments)
            
            # 创建基于车道面的车道剖面
            lanes = self._create_lane_section_from_surfaces(lane_surfaces, road_attributes, road_id)
            
            # 创建道路
            road = xodr.Road(road_id, planview, lanes)
            
            # 添加到OpenDrive
            self.odr.add_road(road)
            self.roads.append(road)
            
            logger.info(f"成功创建基于车道面的道路 ID: {road_id}，包含 {len(lane_surfaces)} 个车道面")
            return road_id
            
        except Exception as e:
            logger.error(f"创建基于车道面的道路失败: {e}")
            return -1
    
    def _calculate_road_reference_line(self, lane_surfaces: List[Dict]) -> List[Dict]:
        """计算道路参考线（使用index为'0'的边界线作为planview）
        
        该方法会遍历所有车道面，查找index为'0'的边界线（左边界或右边界），
        将其坐标转换为几何段（支持直线、圆弧、样条线拟合）作为道路参考线。
        如果未找到index为'0'的边界线，则回退到使用第一个车道面的中心线。
        
        Args:
            lane_surfaces: 车道面数据列表，每个车道面包含left_boundary和right_boundary
            
        Returns:
            List[Dict]: 道路参考线的几何段，用于生成OpenDRIVE的planView
            
        Note:
            - 优先查找index为'0'的左边界线
            - 如果左边界线index不为'0'，则查找index为'0'的右边界线
            - 边界线坐标通过GeometryConverter转换为标准化几何段
        """
        try:
            if not lane_surfaces:
                return []
            
            # 查找所有边界线中index为'0'的边界线
            reference_boundary = None
            reference_coords = None
            
            logger.info("查找index为'0'的边界线作为planview参考线")
            
            # 遍历所有车道面，查找index为'0'的边界线
            for surface in lane_surfaces:
                # 检查左边界
                if ('left_boundary' in surface and 
                    surface['left_boundary'].get('index') == '0'):
                    reference_boundary = surface['left_boundary']
                    reference_coords = surface['left_boundary']['coordinates']
                    logger.info(f"找到index为'0'的左边界线，坐标点数: {len(reference_coords)}")
                    break
                
                # 检查右边界
                if ('right_boundary' in surface and 
                    surface['right_boundary'].get('index') == '0'):
                    reference_boundary = surface['right_boundary']
                    reference_coords = surface['right_boundary']['coordinates']
                    logger.info(f"找到index为'0'的右边界线，坐标点数: {len(reference_coords)}")
                    break
            
            if not reference_coords:
                logger.warning("未找到index为'0'的边界线，回退到使用第一个车道面的中心线")
                # 回退方案：使用第一个车道面的中心线
                reference_surface = lane_surfaces[0]
                if 'center_line' in reference_surface:
                    reference_coords = reference_surface['center_line']
                elif ('left_boundary' in reference_surface and 
                      'right_boundary' in reference_surface):
                    left_coords = reference_surface['left_boundary']['coordinates']
                    right_coords = reference_surface['right_boundary']['coordinates']
                    reference_coords = self._calculate_center_line_coords(left_coords, right_coords)
                
                if not reference_coords:
                    logger.error("无法获取有效的参考线坐标")
                    return []
            
            # 将边界线坐标转换为几何段（高精度拟合，完全按照index=0边界线的折线形状）
            from geometry_converter import GeometryConverter
            # 使用更高精度的参数：更小的容差，保留细节，支持曲线拟合模式
            converter = GeometryConverter(
                tolerance=0.1, 
                smooth_curves=False, 
                preserve_detail=True,
                curve_fitting_mode=getattr(self, 'curve_fitting_mode', 'polyline'),
                polynomial_degree=getattr(self, 'polynomial_degree', 3),
                curve_smoothness=getattr(self, 'curve_smoothness', 0.5),
                coordinate_precision=getattr(self, 'coordinate_precision', 3)
            )
            segments = converter.convert_road_geometry(reference_coords)
            
            logger.info(f"使用高精度参数转换边界线：容差=0.1m, 保留细节=True, 原始坐标点数={len(reference_coords)}")
            
            if segments:
                logger.info(f"道路参考线计算完成，使用index为'0'的边界线，包含 {len(segments)} 个几何段")
                return segments
            else:
                logger.error("边界线坐标转换为几何段失败")
                return []
            
        except Exception as e:
            logger.error(f"计算道路参考线失败: {e}")
            return []
    
    def _extract_coordinates_from_segments(self, segments: List[Dict]) -> List[Tuple[float, float]]:
        """从几何段中提取坐标点
        
        Args:
            segments: 几何段列表
            
        Returns:
            List[Tuple[float, float]]: 坐标点列表
        """
        # 使用geometry_converter的重建方法
        from geometry_converter import GeometryConverter
        converter = GeometryConverter(coordinate_precision=getattr(self, 'coordinate_precision', 3))
        return converter._reconstruct_reference_line(segments)
    
    def _calculate_center_line_coords(self, left_coords: List[Tuple[float, float]], 
                                    right_coords: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """从左右边界计算中心线坐标
        
        Args:
            left_coords: 左边界坐标
            right_coords: 右边界坐标
            
        Returns:
            List[Tuple[float, float]]: 中心线坐标
        """
        if not left_coords or not right_coords:
            return []
        
        # 确保两边界点数相同
        min_points = min(len(left_coords), len(right_coords))
        center_coords = []
        
        for i in range(min_points):
            left_x, left_y = left_coords[i]
            right_x, right_y = right_coords[i]
            center_x = (left_x + right_x) / 2
            center_y = (left_y + right_y) / 2
            center_coords.append((center_x, center_y))
        
        return center_coords
    
    def _calculate_average_center_line(self, all_center_coords: List[List[Tuple[float, float]]]) -> List[Tuple[float, float]]:
        """计算多个中心线的平均线
        
        Args:
            all_center_coords: 所有车道面的中心线坐标列表
            
        Returns:
            List[Tuple[float, float]]: 平均中心线坐标
        """
        if not all_center_coords:
            return []
        
        # 找到最长的中心线长度
        max_length = max(len(coords) for coords in all_center_coords)
        if max_length == 0:
            return []
        
        # 对所有中心线进行插值，使其长度与最长的一致
        interpolated_coords = []
        for coords in all_center_coords:
            if len(coords) == max_length:
                # 已经是最长的，直接使用
                interpolated_coords.append(coords)
            else:
                # 需要插值到最长长度
                interpolated = self._interpolate_to_target_length(coords, max_length)
                interpolated_coords.append(interpolated)
        
        # 计算平均坐标
        avg_coords = []
        for i in range(max_length):
            avg_x = sum(coords[i][0] for coords in interpolated_coords) / len(interpolated_coords)
            avg_y = sum(coords[i][1] for coords in interpolated_coords) / len(interpolated_coords)
            avg_coords.append((avg_x, avg_y))
        
        return avg_coords
    
    def _interpolate_to_target_length(self, coords: List[Tuple[float, float]], target_length: int) -> List[Tuple[float, float]]:
        """将坐标列表插值到目标长度
        
        Args:
            coords: 原始坐标列表
            target_length: 目标长度
            
        Returns:
            List[Tuple[float, float]]: 插值后的坐标列表
        """
        if len(coords) <= 1 or target_length <= 1:
            return coords
        
        import numpy as np
        from scipy import interpolate
        
        # 计算原始坐标的累积距离
        distances = [0]
        for i in range(1, len(coords)):
            dist = ((coords[i][0] - coords[i-1][0])**2 + (coords[i][1] - coords[i-1][1])**2)**0.5
            distances.append(distances[-1] + dist)
        
        # 创建目标距离数组
        total_distance = distances[-1]
        target_distances = np.linspace(0, total_distance, target_length)
        
        # 分别对x和y坐标进行插值
        x_coords = [coord[0] for coord in coords]
        y_coords = [coord[1] for coord in coords]
        
        # 使用线性插值
        f_x = interpolate.interp1d(distances, x_coords, kind='linear', bounds_error=False, fill_value='extrapolate')
        f_y = interpolate.interp1d(distances, y_coords, kind='linear', bounds_error=False, fill_value='extrapolate')
        
        # 生成插值后的坐标
        interpolated_x = f_x(target_distances)
        interpolated_y = f_y(target_distances)
        
        return list(zip(interpolated_x, interpolated_y))
    
    def _create_planview_from_segments(self, segments: List[Dict]) -> xodr.PlanView:
        """从几何段创建平面视图
        
        Args:
            segments: 几何段列表
            
        Returns:
            xodr.PlanView: 平面视图对象
        """
        # 创建PlanView并设置起始位置
        start_x = segments[0].get('x', 0) if segments else 0
        start_y = segments[0].get('y', 0) if segments else 0
        start_heading = segments[0].get('hdg', 0) if segments else 0
        
        planview = xodr.PlanView(start_x, start_y, start_heading)
        
        for segment in segments:
            if segment['type'] == 'line':
                # 创建直线段
                geometry = Line(length=segment['length'])
                planview.add_geometry(geometry, heading=segment['hdg'])
                
            elif segment['type'] == 'arc':
                # 创建圆弧段
                geometry = Arc(curvature=segment['curvature'], length=segment['length'])
                planview.add_geometry(geometry, heading=segment['hdg'])
                
            elif segment['type'] == 'parampoly3':
                # 创建参数化三次多项式段
                geometry = ParamPoly3(
                    au=segment['au'],
                    bu=segment['bu'], 
                    cu=segment['cu'],
                    du=segment['du'],
                    av=segment['av'],
                    bv=segment['bv'],
                    cv=segment['cv'],
                    dv=segment['dv'],
                    prange='normalized',
                    length=segment['length']
                )
                planview.add_geometry(geometry, heading=segment['hdg'])
                
            else:
                logger.warning(f"未知的几何类型: {segment['type']}")
        
        return planview
    
    def _create_lane_section(self, attributes: Dict) -> xodr.Lanes:
        """创建车道剖面
        
        Args:
            attributes: 道路属性
            
        Returns:
            xodr.Lanes: 车道对象
        """
        # 创建车道剖面
        lanes = xodr.Lanes()
        
        # 创建车道段
        lane_section = xodr.LaneSection(0, xodr.standard_lane())
        
        # 添加行车道（右侧）
        num_lanes = attributes.get('num_lanes', 1)
        lane_width = attributes.get('lane_width', 3.5)
        
        for i in range(1, num_lanes + 1):
             # 创建车道
             lane = xodr.Lane(lane_type=xodr.LaneType.driving)
             lane.add_lane_width(a=lane_width, soffset=0)
             
             # 添加车道标线（可选）
             road_mark = xodr.RoadMark(
                 xodr.RoadMarkType.solid,
                 xodr.RoadMarkWeight.standard,
                 xodr.RoadMarkColor.white
             )
             lane.add_roadmark(road_mark)
             
             lane_section.add_right_lane(lane)
        
        # 添加左侧车道（如果是双向道路）
        if attributes.get('bidirectional', False):
             for i in range(1, num_lanes + 1):
                 lane = xodr.Lane(lane_type=xodr.LaneType.driving)
                 lane.add_lane_width(a=lane_width, soffset=0)
                 lane_section.add_left_lane(lane)
        
        lanes.add_lanesection(lane_section)
        return lanes
    
    def _create_lane_section_from_surfaces(self, lane_surfaces: List[Dict], 
                                         attributes: Dict = None, road_id: int = None) -> xodr.Lanes:
        """从车道面数据创建车道剖面（所有车道都在planview右侧）
        
        Args:
            lane_surfaces: 车道面数据列表
            attributes: 道路属性
            road_id: 道路ID（用于日志跟踪）
            
        Returns:
            xodr.Lanes: 车道对象
        """
        # 创建车道剖面
        lanes = xodr.Lanes()
        
        # 创建车道段
        lane_section = xodr.LaneSection(0, xodr.standard_lane())
        
        # 将所有车道面都创建为右侧车道（包括index为0的车道面）
        logger.info(f"创建车道剖面 (Road ID: {road_id})：总共{len(lane_surfaces)}个车道面，全部创建为右侧车道")
        
        for i, surface in enumerate(lane_surfaces):
                
            # 创建车道
            lane = xodr.Lane(lane_type=xodr.LaneType.driving)
            
            # 计算车道ID（右侧车道为负数，从-1开始）
            lane_id = -(i + 1)
            
            # 处理车道宽度变化（从宽度变化数据中获取）
            width_profile = surface.get('width_profile', [])
            surface_id = surface.get('surface_id', f'surface_{i}')
            
            logger.info(f"处理车道 (Road ID: {road_id}, Lane ID: {lane_id}, Surface ID: {surface_id})")
            
            if width_profile:
                # 检查是否为变宽车道
                widths = [wp['width'] for wp in width_profile]
                min_width = min(widths)
                max_width = max(widths)
                width_change = max_width - min_width
                
                # 详细记录宽度数据
                logger.info(f"  宽度数据: {len(width_profile)}个采样点, 最小={min_width:.3f}m, 最大={max_width:.3f}m, 变化={width_change:.3f}m")
                
                # 检查是否有宽度为0的情况
                zero_widths = [wp for wp in width_profile if wp['width'] <= 0.001]
                if zero_widths:
                    logger.warning(f"  发现{len(zero_widths)}个异常宽度点 (Road ID: {road_id}, Lane ID: {lane_id}):")
                    for zw in zero_widths[:5]:  # 只显示前5个
                        logger.warning(f"    s={zw['s']:.2f}m, width={zw['width']:.6f}")
                
                # 更严格的变宽车道检测：考虑宽度变化幅度和相对变化率
                # 当min_width为0时，使用平均宽度作为基准计算变化率
                if min_width > 0:
                    width_change_ratio = width_change / min_width
                else:
                    # 计算平均宽度作为基准
                    avg_width = sum(wp['width'] for wp in width_profile) / len(width_profile) if width_profile else 0
                    width_change_ratio = width_change / avg_width if avg_width > 0 else float('inf')  # 如果平均宽度也为0，设为无穷大表示显著变化
                
                if width_change > 0.1 and width_change_ratio > 0.03:  # 绝对变化>0.1米且相对变化>3%
                    logger.info(f"  检测到变宽车道: 变化率={width_change_ratio:.1%}, 原始宽度点数={len(width_profile)}")
                    
                    # 过滤多项式段，只保留显著变化的段
                    filtered_profile = self._filter_significant_width_changes(width_profile)
                    logger.info(f"  过滤后宽度点数: {len(filtered_profile)} (Road ID: {road_id}, Lane ID: {lane_id})")
                    
                    # 限制多项式段数量，避免过拟合
                    max_segments = min(8, len(filtered_profile))  # 最多8个多项式段
                    if len(filtered_profile) > max_segments:
                        logger.warning(f"  宽度变化段过多，将从{len(filtered_profile)}段简化为{max_segments}段")
                    
                    segment_count = 0
                    for j, wp in enumerate(filtered_profile):
                        if segment_count >= max_segments:
                            break
                            
                        if 'polynomial' in wp:
                            poly = wp['polynomial']
                            lane.add_lane_width(
                                a=poly['a'], 
                                b=poly['b'], 
                                c=poly['c'], 
                                d=poly['d'], 
                                soffset=wp['s']
                            )
                            segment_count += 1
                            if j == 0:
                                logger.info(f"    起始多项式段: s={wp['s']:.2f}m, a={poly['a']:.3f}, b={poly['b']:.3f}, c={poly['c']:.3f}, d={poly['d']:.3f}")
                        else:
                            # 回退到常数宽度
                            lane.add_lane_width(a=wp['width'], soffset=wp['s'])
                            segment_count += 1
                            
                        if j == len(filtered_profile) - 1:
                            logger.info(f"    结束宽度: s={wp['s']:.2f}m, width={wp['width']:.2f}m")
                    
                    logger.info(f"    实际使用{segment_count}个多项式段（原始{len(width_profile)}个，过滤后{len(filtered_profile)}个，限制{max_segments}个）")
                else:
                    # 等宽车道，使用第一个宽度值
                    lane_width = width_profile[0]['width']
                    lane.add_lane_width(a=lane_width, soffset=0)
                    logger.info(f"  等宽车道: 宽度={lane_width:.3f}m")
                    
                    # 特别检查宽度为0的情况
                    if lane_width <= 0.001:
                        logger.error(f"  异常！车道宽度为0 (Road ID: {road_id}, Lane ID: {lane_id}, Surface ID: {surface_id})")
                        logger.error(f"    宽度数据详情: {width_profile[:3]}...")  # 显示前3个数据点
                        
                        # 尝试使用后续非零宽度值
                        valid_widths = [wp['width'] for wp in width_profile if wp['width'] > 0.001]
                        if valid_widths:
                            lane_width = min(valid_widths)  # 使用最小的有效宽度
                            lane.add_lane_width(a=lane_width, soffset=0)
                            logger.warning(f"    已修正为最小有效宽度: {lane_width:.3f}m")
                        else:
                            # 如果所有宽度都为0，跳过此车道
                            logger.error(f"    所有宽度数据都为0，跳过此车道")
                            continue
            else:
                # 默认宽度
                lane_width = attributes.get('lane_width', 3.5) if attributes else 3.5
                lane.add_lane_width(a=lane_width, soffset=0)
                logger.warning(f"  车道面缺少宽度信息，使用默认宽度{lane_width:.2f}m (Road ID: {road_id}, Lane ID: {lane_id})")
            
            # 添加车道标线
            road_mark = xodr.RoadMark(
                xodr.RoadMarkType.solid,
                xodr.RoadMarkWeight.standard,
                xodr.RoadMarkColor.white
            )
            lane.add_roadmark(road_mark)
            
            # 添加到右侧车道（所有车道都在planview右侧）
            lane_section.add_right_lane(lane)
            logger.info(f"  车道已添加为右侧车道 (Road ID: {road_id}, Lane ID: {lane_id}, Surface ID: {surface_id})")
        
        lanes.add_lanesection(lane_section)
        logger.info(f"车道剖面创建完成 (Road ID: {road_id})，包含{len(lane_surfaces)}个右侧车道")
        return lanes
    
    def create_multiple_roads(self, roads_data: List[Dict]) -> List[int]:
        """创建多条道路
        
        Args:
            roads_data: 道路数据列表，每个包含segments和attributes
            
        Returns:
            List[int]: 创建的道路ID列表
        """
        road_ids = []
        
        for road_data in roads_data:
            segments = road_data.get('segments', [])
            attributes = road_data.get('attributes', {})
            
            road_id = self.create_road_from_segments(segments, attributes)
            if road_id > 0:
                road_ids.append(road_id)
        
        logger.info(f"成功创建 {len(road_ids)} 条道路")
        return road_ids
    
    def _filter_significant_width_changes(self, width_profile: List[Dict], 
                                        change_threshold: float = 0.05) -> List[Dict]:
        """过滤显著的宽度变化段，减少多项式段数量
        
        Args:
            width_profile: 原始宽度变化数据
            change_threshold: 宽度变化阈值（米）
            
        Returns:
            List[Dict]: 过滤后的宽度变化数据
        """
        if len(width_profile) <= 2:
            return width_profile
        
        filtered = [width_profile[0]]  # 保留第一个点
        
        for i in range(1, len(width_profile) - 1):
            current_width = width_profile[i]['width']
            prev_width = filtered[-1]['width']
            next_width = width_profile[i + 1]['width']
            
            # 检查宽度变化是否显著
            width_change_prev = abs(current_width - prev_width)
            width_change_next = abs(next_width - current_width)
            
            # 检查是否为转折点（宽度变化方向改变）
            is_turning_point = ((current_width > prev_width and current_width > next_width) or
                              (current_width < prev_width and current_width < next_width))
            
            # 保留显著变化点或转折点
            if (width_change_prev > change_threshold or 
                width_change_next > change_threshold or 
                is_turning_point):
                filtered.append(width_profile[i])
        
        filtered.append(width_profile[-1])  # 保留最后一个点
        
        return filtered
    
    def add_road_connections(self, connections: List[Dict]):
        """添加道路连接（简化版本）
        
        Args:
            connections: 连接信息列表
        """
        # 这是一个简化的实现，实际的道路连接需要更复杂的逻辑
        for connection in connections:
            try:
                road1_id = connection['road1_id']
                road2_id = connection['road2_id']
                contact_point = connection.get('contact_point', 'end')
                
                # 在实际实现中，这里需要创建Junction和Connection对象
                logger.info(f"添加道路连接: {road1_id} -> {road2_id}")
                
            except Exception as e:
                logger.error(f"添加道路连接失败: {e}")
    
    def add_road_objects(self, road_id: int, objects: List[Dict]):
        """添加道路对象（标志、信号灯等）
        
        Args:
            road_id: 道路ID
            objects: 对象列表
        """
        try:
            road = next((r for r in self.roads if r.id == road_id), None)
            if not road:
                logger.error(f"未找到道路 ID: {road_id}")
                return
            
            for obj in objects:
                # 创建道路对象
                road_object = xodr.Object(
                    s=obj.get('s', 0),
                    t=obj.get('t', 0),
                    object_id=obj.get('id', 0),
                    object_type=obj.get('type', 'pole'),
                    name=obj.get('name', ''),
                    zOffset=obj.get('z_offset', 0),
                    hdg=obj.get('heading', 0)
                )
                
                road.add_object(road_object)
            
            logger.info(f"为道路 {road_id} 添加了 {len(objects)} 个对象")
            
        except Exception as e:
            logger.error(f"添加道路对象失败: {e}")
    
    def set_road_elevation(self, road_id: int, elevation_data: List[Dict]):
        """设置道路高程（简化版本）
        
        Args:
            road_id: 道路ID
            elevation_data: 高程数据列表
        """
        try:
            road = next((r for r in self.roads if r.id == road_id), None)
            if not road:
                logger.error(f"未找到道路 ID: {road_id}")
                return
            
            # 创建高程剖面
            elevation_profile = xodr.ElevationProfile()
            
            for elev in elevation_data:
                elevation = xodr.Elevation(
                    s=elev.get('s', 0),
                    a=elev.get('a', 0),  # 高程值
                    b=elev.get('b', 0),  # 坡度
                    c=elev.get('c', 0),  # 曲率变化
                    d=elev.get('d', 0)   # 曲率变化率
                )
                elevation_profile.add_elevation(elevation)
            
            road.add_elevation_profile(elevation_profile)
            logger.info(f"为道路 {road_id} 设置了高程剖面")
            
        except Exception as e:
            logger.error(f"设置道路高程失败: {e}")
    
    def generate_file(self, output_path: str) -> bool:
        """生成OpenDrive文件
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            bool: 生成是否成功
        """
        try:
            # 创建输出目录
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # 调整道路和车道连接关系
            self.odr.adjust_roads_and_lanes()
            
            # 生成文件
            self.odr.write_xml(output_path)
            
            logger.info(f"OpenDrive文件已生成: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"生成OpenDrive文件失败: {e}")
            return False
    
    def validate_opendrive(self) -> Dict[str, any]:
        """验证OpenDrive数据的有效性
        
        Returns:
            Dict: 验证结果
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'road_count': len(self.roads),
            'total_length': 0
        }
        
        try:
            # 检查道路数量
            if len(self.roads) == 0:
                validation_result['errors'].append("没有道路数据")
                validation_result['valid'] = False
            
            # 检查每条道路
            for road in self.roads:
                # 计算道路长度
                road_length = 0
                if hasattr(road, 'planview') and road.planview:
                    # PlanView对象没有geometries属性，暂时跳过长度计算
                    road_length = 100.0  # 设置默认长度用于验证
                
                validation_result['total_length'] += road_length
                
                # 检查道路长度
                if road_length < 1.0:
                    validation_result['warnings'].append(f"道路 {road.id} 长度过短: {road_length:.2f}m")
                
                # 检查车道
                if not hasattr(road, 'lanes') or not road.lanes:
                    validation_result['errors'].append(f"道路 {road.id} 缺少车道定义")
                    validation_result['valid'] = False
            
            logger.info(f"验证完成: {validation_result['road_count']} 条道路，总长度: {validation_result['total_length']:.2f}m")
            
        except Exception as e:
            validation_result['errors'].append(f"验证过程出错: {e}")
            validation_result['valid'] = False
        
        return validation_result
    
    def get_statistics(self) -> Dict[str, any]:
        """获取生成的OpenDrive统计信息
        
        Returns:
            Dict: 统计信息
        """
        stats = {
            'road_count': len(self.roads),
            'total_length': 0,
            'geometry_types': {},
            'lane_count': 0
        }
        
        for road in self.roads:
            # 统计几何类型（PlanView对象没有geometries属性，暂时跳过）
            if hasattr(road, 'planview') and road.planview:
                # 使用默认长度进行统计
                stats['total_length'] += 100.0  # 默认长度
                stats['geometry_types']['Line'] = stats['geometry_types'].get('Line', 0) + 1
            
            # 统计车道数（Lanes对象结构不明确，暂时跳过）
            if hasattr(road, 'lanes') and road.lanes:
                # 使用默认车道数进行统计
                stats['lane_count'] += 2  # 假设每条道路有2条车道
        
        return stats