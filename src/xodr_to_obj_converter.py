#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XODR到OBJ转换器
将OpenDRIVE文件转换为OBJ 3D模型格式
参考libOpenDRIVE实现，支持精确几何体解析和车道级渲染

作者: ShpToOpenDrive项目组
版本: 2.0.0
"""

import numpy as np
import math
from typing import List, Dict, Tuple, Optional
from xodr_parser import XODRParser


class XODRToOBJConverter:
    """
    XODR到OBJ转换器
    将道路几何数据转换为3D网格模型
    参考libOpenDRIVE实现，支持精确几何体解析
    """
    
    def __init__(self, road_width: float = 3.5, resolution: float = 0.5):
        """
        初始化转换器
        
        Args:
            road_width: 默认道路宽度（米）
            resolution: 采样分辨率（米），更小的值产生更精细的网格
        """
        self.road_width = road_width
        self.resolution = resolution
        self.vertices = []
        self.faces = []
        self.vertex_count = 0
        self.materials = {}  # 材质定义
        self.lane_materials = {}  # 车道材质映射
        
    def convert(self, xodr_file_path: str, obj_file_path: str) -> bool:
        """
        将XODR文件转换为OBJ文件（简化接口）
        
        Args:
            xodr_file_path: XODR文件路径
            obj_file_path: 输出OBJ文件路径
            
        Returns:
            转换是否成功
        """
        return self.convert_xodr_to_obj(xodr_file_path, obj_file_path)
    
    def convert_xodr_to_obj(self, xodr_file_path: str, obj_file_path: str) -> bool:
        """
        将XODR文件转换为OBJ文件
        
        Args:
            xodr_file_path: XODR文件路径
            obj_file_path: 输出OBJ文件路径
            
        Returns:
            转换是否成功
        """
        try:
            # 解析XODR文件
            parser = XODRParser()
            parser.parse_file(xodr_file_path)
            
            # 重置顶点和面数据
            self.vertices = []
            self.faces = []
            self.vertex_count = 0
            
            # 为每条道路生成网格
            for road in parser.roads:
                self._generate_road_mesh(road)
            
            # 导出OBJ文件
            self._export_obj_file(obj_file_path)
            
            return True
            
        except Exception as e:
            print(f"转换失败: {str(e)}")
            return False
    
    def _generate_road_mesh(self, road_data: Dict):
        """
        为单条道路生成3D网格
        
        Args:
            road_data: 道路数据字典
        """
        if not road_data['planView']:
            return
        
        # 生成道路中心线点
        center_points = self._generate_road_centerline(road_data)
        if len(center_points) < 2:
            return
        
        # 计算道路宽度（使用车道信息或默认值）
        road_width = self._calculate_road_width(road_data)
        
        # 生成道路表面网格
        self._generate_road_surface_mesh(center_points, road_width)
    
    def _generate_road_centerline(self, road_data: Dict) -> List[Tuple[float, float, float]]:
        """
        生成道路中心线点序列
        
        Args:
            road_data: 道路数据
            
        Returns:
            中心线点列表
        """
        points = []
        
        for geometry in road_data['planView']:
            geom_points = self._generate_geometry_points(geometry)
            points.extend(geom_points)
        
        return points
    
    def _generate_geometry_points(self, geometry: Dict) -> List[Tuple[float, float, float]]:
        """
        根据几何类型生成点序列
        参考libOpenDRIVE实现，支持精确几何体解析
        
        Args:
            geometry: 几何数据
            
        Returns:
            3D点列表
        """
        points = []
        length = geometry['length']
        num_points = max(2, int(length / self.resolution) + 1)
        
        x0, y0 = geometry['x'], geometry['y']
        hdg = geometry['hdg']
        
        for i in range(num_points):
            s = (i / (num_points - 1)) * length
            
            if geometry['type'] == 'line':
                x, y, heading = self._calc_line_point(x0, y0, hdg, s)
            elif geometry['type'] == 'arc':
                curvature = geometry['params']['curvature']
                x, y, heading = self._calc_arc_point(x0, y0, hdg, curvature, s)
            elif geometry['type'] == 'spiral':
                curv_start = geometry['params'].get('curvStart', 0.0)
                curv_end = geometry['params'].get('curvEnd', 0.0)
                x, y, heading = self._calc_spiral_point(x0, y0, hdg, curv_start, curv_end, length, s)
            elif geometry['type'] == 'poly3':
                a, b, c, d = geometry['params'].get('a', 0), geometry['params'].get('b', 0), \
                           geometry['params'].get('c', 0), geometry['params'].get('d', 0)
                x, y, heading = self._calc_poly3_point(x0, y0, hdg, a, b, c, d, s)
            elif geometry['type'] == 'paramPoly3':
                aU, bU, cU, dU = geometry['params'].get('aU', 0), geometry['params'].get('bU', 0), \
                               geometry['params'].get('cU', 0), geometry['params'].get('dU', 0)
                aV, bV, cV, dV = geometry['params'].get('aV', 0), geometry['params'].get('bV', 0), \
                               geometry['params'].get('cV', 0), geometry['params'].get('dV', 0)
                x, y, heading = self._calc_param_poly3_point(x0, y0, hdg, aU, bU, cU, dU, aV, bV, cV, dV, s)
            else:
                # 默认使用线性近似
                x, y, heading = self._calc_line_point(x0, y0, hdg, s)
            
            # 计算高程（简化处理，可以后续扩展支持elevation profile）
            z = 0.0
            
            points.append((x, y, z))
        
        return points
    
    def _calc_line_point(self, x0: float, y0: float, hdg: float, s: float) -> Tuple[float, float, float]:
        """
        计算直线几何体上的点
        
        Args:
            x0, y0: 起始点坐标
            hdg: 起始航向角
            s: 沿路径的距离
            
        Returns:
            (x, y, heading) 坐标和航向角
        """
        x = x0 + s * math.cos(hdg)
        y = y0 + s * math.sin(hdg)
        return x, y, hdg
    
    def _calc_arc_point(self, x0: float, y0: float, hdg: float, curvature: float, s: float) -> Tuple[float, float, float]:
        """
        计算圆弧几何体上的点
        
        Args:
            x0, y0: 起始点坐标
            hdg: 起始航向角
            curvature: 曲率
            s: 沿路径的距离
            
        Returns:
            (x, y, heading) 坐标和航向角
        """
        if abs(curvature) < 1e-10:
            return self._calc_line_point(x0, y0, hdg, s)
        
        radius = 1.0 / curvature
        angle = s * curvature
        
        x = x0 + radius * (math.sin(hdg + angle) - math.sin(hdg))
        y = y0 - radius * (math.cos(hdg + angle) - math.cos(hdg))
        heading = hdg + angle
        
        return x, y, heading
    
    def _calc_spiral_point(self, x0: float, y0: float, hdg: float, curv_start: float, curv_end: float, 
                          length: float, s: float) -> Tuple[float, float, float]:
        """
        计算螺旋线几何体上的点（Clothoid螺旋线）
        
        Args:
            x0, y0: 起始点坐标
            hdg: 起始航向角
            curv_start: 起始曲率
            curv_end: 结束曲率
            length: 螺旋线长度
            s: 沿路径的距离
            
        Returns:
            (x, y, heading) 坐标和航向角
        """
        # 计算曲率变化率
        if length > 0:
            curv_dot = (curv_end - curv_start) / length
        else:
            curv_dot = 0
        
        # 当前曲率
        curvature = curv_start + curv_dot * s
        
        # 使用数值积分计算螺旋线点
        # 这是一个简化实现，实际应该使用Fresnel积分
        num_steps = max(10, int(s / 0.1))
        x, y = x0, y0
        heading = hdg
        
        if num_steps > 0:
            ds = s / num_steps
            for i in range(num_steps):
                s_local = i * ds
                curv_local = curv_start + curv_dot * s_local
                
                x += ds * math.cos(heading)
                y += ds * math.sin(heading)
                heading += curv_local * ds
        
        return x, y, heading
    
    def _calc_poly3_point(self, x0: float, y0: float, hdg: float, a: float, b: float, c: float, d: float, 
                         s: float) -> Tuple[float, float, float]:
        """
        计算三次多项式几何体上的点
        
        Args:
            x0, y0: 起始点坐标
            hdg: 起始航向角
            a, b, c, d: 多项式系数
            s: 沿路径的距离
            
        Returns:
            (x, y, heading) 坐标和航向角
        """
        # 计算横向偏移
        t = a + b * s + c * s * s + d * s * s * s
        
        # 计算切线方向的导数
        dt_ds = b + 2 * c * s + 3 * d * s * s
        
        # 计算点坐标
        cos_hdg = math.cos(hdg)
        sin_hdg = math.sin(hdg)
        
        x = x0 + s * cos_hdg - t * sin_hdg
        y = y0 + s * sin_hdg + t * cos_hdg
        
        # 计算航向角
        heading = hdg + math.atan(dt_ds)
        
        return x, y, heading
    
    def _calc_param_poly3_point(self, x0: float, y0: float, hdg: float, 
                               aU: float, bU: float, cU: float, dU: float,
                               aV: float, bV: float, cV: float, dV: float, 
                               s: float) -> Tuple[float, float, float]:
        """
        计算参数三次多项式几何体上的点
        
        Args:
            x0, y0: 起始点坐标
            hdg: 起始航向角
            aU, bU, cU, dU: U方向多项式系数
            aV, bV, cV, dV: V方向多项式系数
            s: 沿路径的距离
            
        Returns:
            (x, y, heading) 坐标和航向角
        """
        # 计算参数坐标
        u = aU + bU * s + cU * s * s + dU * s * s * s
        v = aV + bV * s + cV * s * s + dV * s * s * s
        
        # 计算导数
        du_ds = bU + 2 * cU * s + 3 * dU * s * s
        dv_ds = bV + 2 * cV * s + 3 * dV * s * s
        
        # 转换到全局坐标系
        cos_hdg = math.cos(hdg)
        sin_hdg = math.sin(hdg)
        
        x = x0 + u * cos_hdg - v * sin_hdg
        y = y0 + u * sin_hdg + v * cos_hdg
        
        # 计算航向角
        heading = hdg + math.atan2(dv_ds, du_ds)
        
        return x, y, heading
    
    def _calculate_road_width(self, road_data: Dict) -> float:
        """
        计算道路总宽度
        
        Args:
            road_data: 道路数据
            
        Returns:
            道路宽度
        """
        total_width = 0.0
        
        # 如果有车道信息，计算实际宽度
        if road_data['lanes']:
            for lane_section in road_data['lanes']:
                section_width = 0.0
                
                # 计算左侧车道宽度
                for lane in lane_section['left']:
                    if lane['width']:
                        section_width += lane['width'][0]['a']  # 使用起始宽度
                
                # 计算右侧车道宽度
                for lane in lane_section['right']:
                    if lane['width']:
                        section_width += lane['width'][0]['a']  # 使用起始宽度
                
                total_width = max(total_width, section_width)
        
        # 如果没有车道信息或宽度为0，使用默认宽度
        return total_width if total_width > 0 else self.road_width
    
    def _generate_road_surface_mesh(self, center_points: List[Tuple[float, float, float]], width: float, lane_data: Dict = None):
        """
        生成道路表面网格，支持车道级别渲染
        
        Args:
            center_points: 中心线点列表
            width: 道路宽度
            lane_data: 车道数据（可选）
        """
        if len(center_points) < 2:
            return
        
        # 如果有车道数据，按车道生成网格
        if lane_data and 'lanes' in lane_data:
            self._generate_lane_based_mesh(center_points, lane_data)
        else:
            self._generate_simple_road_mesh(center_points, width)
    
    def _generate_lane_based_mesh(self, center_points: List[Tuple[float, float, float]], lane_data: Dict):
        """
        基于车道数据生成精确的车道网格
        
        Args:
            center_points: 中心线点列表
            lane_data: 车道数据
        """
        lanes = lane_data.get('lanes', [])
        if not lanes:
            self._generate_simple_road_mesh(center_points, 6.0)
            return
        
        # 为每条车道生成网格
        for lane_idx, lane in enumerate(lanes):
            lane_width = lane.get('width', 3.5)
            lane_type = lane.get('type', 'driving')
            
            # 计算车道边界点
            lane_left_points = []
            lane_right_points = []
            
            # 计算车道偏移（相对于道路中心线）
            lane_offset = self._calculate_lane_offset(lanes, lane_idx)
            
            for i, (x, y, z) in enumerate(center_points):
                # 计算道路方向向量
                if i == 0:
                    dx = center_points[i + 1][0] - x
                    dy = center_points[i + 1][1] - y
                elif i == len(center_points) - 1:
                    dx = x - center_points[i - 1][0]
                    dy = y - center_points[i - 1][1]
                else:
                    dx1 = x - center_points[i - 1][0]
                    dy1 = y - center_points[i - 1][1]
                    dx2 = center_points[i + 1][0] - x
                    dy2 = center_points[i + 1][1] - y
                    dx = (dx1 + dx2) / 2.0
                    dy = (dy1 + dy2) / 2.0
                
                # 归一化方向向量
                length = math.sqrt(dx * dx + dy * dy)
                if length > 0:
                    dx /= length
                    dy /= length
                
                # 计算垂直向量
                perp_x = -dy
                perp_y = dx
                
                # 计算车道边界点
                left_offset = lane_offset + lane_width / 2
                right_offset = lane_offset - lane_width / 2
                
                left_x = x + perp_x * left_offset
                left_y = y + perp_y * left_offset
                right_x = x + perp_x * right_offset
                right_y = y + perp_y * right_offset
                
                lane_left_points.append((left_x, left_y, z))
                lane_right_points.append((right_x, right_y, z))
            
            # 添加车道顶点
            start_vertex_index = self.vertex_count
            
            for point in lane_left_points:
                self.vertices.append(point)
                self.vertex_count += 1
            
            for point in lane_right_points:
                self.vertices.append(point)
                self.vertex_count += 1
            
            # 生成车道面
            num_segments = len(center_points) - 1
            
            for i in range(num_segments):
                left_i = start_vertex_index + i
                left_i_next = start_vertex_index + i + 1
                right_i = start_vertex_index + len(lane_left_points) + i
                right_i_next = start_vertex_index + len(lane_left_points) + i + 1
                
                self.faces.append((left_i + 1, right_i + 1, left_i_next + 1))
                self.faces.append((left_i_next + 1, right_i + 1, right_i_next + 1))
                
                # 记录材质
                material_name = self._get_lane_material(lane_type)
                if material_name not in self.materials:
                    self.materials[material_name] = len(self.materials)
    
    def _generate_simple_road_mesh(self, center_points: List[Tuple[float, float, float]], width: float):
        """
        生成简单的道路表面网格
        
        Args:
            center_points: 中心线点列表
            width: 道路宽度
        """
        half_width = width / 2.0
        
        # 为每个中心点生成左右边界点
        left_points = []
        right_points = []
        
        for i, (x, y, z) in enumerate(center_points):
            # 计算道路方向向量
            if i == 0:
                # 第一个点，使用下一个点的方向
                dx = center_points[i + 1][0] - x
                dy = center_points[i + 1][1] - y
            elif i == len(center_points) - 1:
                # 最后一个点，使用前一个点的方向
                dx = x - center_points[i - 1][0]
                dy = y - center_points[i - 1][1]
            else:
                # 中间点，使用平均方向
                dx1 = x - center_points[i - 1][0]
                dy1 = y - center_points[i - 1][1]
                dx2 = center_points[i + 1][0] - x
                dy2 = center_points[i + 1][1] - y
                dx = (dx1 + dx2) / 2.0
                dy = (dy1 + dy2) / 2.0
            
            # 归一化方向向量
            length = math.sqrt(dx * dx + dy * dy)
            if length > 0:
                dx /= length
                dy /= length
            
            # 计算垂直向量（左右方向）
            perp_x = -dy
            perp_y = dx
            
            # 生成左右边界点
            left_x = x + perp_x * half_width
            left_y = y + perp_y * half_width
            right_x = x - perp_x * half_width
            right_y = y - perp_y * half_width
            
            left_points.append((left_x, left_y, z))
            right_points.append((right_x, right_y, z))
        
        # 添加顶点到列表
        start_vertex_index = self.vertex_count
        
        for point in left_points:
            self.vertices.append(point)
            self.vertex_count += 1
        
        for point in right_points:
            self.vertices.append(point)
            self.vertex_count += 1
        
        # 生成三角形面
        num_segments = len(center_points) - 1
        
        for i in range(num_segments):
            # 左侧点索引
            left_i = start_vertex_index + i
            left_i_next = start_vertex_index + i + 1
            
            # 右侧点索引
            right_i = start_vertex_index + len(left_points) + i
            right_i_next = start_vertex_index + len(left_points) + i + 1
            
            # 生成两个三角形组成一个四边形
            # 三角形1: left_i, right_i, left_i_next
            self.faces.append((left_i + 1, right_i + 1, left_i_next + 1))  # OBJ索引从1开始
            
            # 三角形2: left_i_next, right_i, right_i_next
            self.faces.append((left_i_next + 1, right_i + 1, right_i_next + 1))
    
    def _calculate_lane_offset(self, lanes: List[Dict], lane_idx: int) -> float:
        """
        计算车道相对于道路中心线的偏移
        
        Args:
            lanes: 车道列表
            lane_idx: 当前车道索引
            
        Returns:
            车道中心线偏移量
        """
        offset = 0.0
        
        # 计算到当前车道的累积偏移
        for i in range(lane_idx):
            lane_width = lanes[i].get('width', 3.5)
            offset += lane_width
        
        # 加上当前车道的一半宽度
        current_lane_width = lanes[lane_idx].get('width', 3.5)
        offset += current_lane_width / 2
        
        # 如果车道在左侧，偏移为正；右侧为负
        # 这里假设车道索引0是最左侧的车道
        total_width = sum(lane.get('width', 3.5) for lane in lanes)
        offset -= total_width / 2
        
        return offset
    
    def _get_lane_material(self, lane_type: str) -> str:
        """
        根据车道类型获取材质名称
        
        Args:
            lane_type: 车道类型
            
        Returns:
            材质名称
        """
        return self.lane_materials.get(lane_type, 'asphalt')
    
    def _export_obj_file(self, obj_file_path: str):
        """
        导出OBJ文件，支持材质
        
        Args:
            obj_file_path: OBJ文件路径
        """
        try:
            import os
            from datetime import datetime
            
            # 生成MTL文件路径
            mtl_file_path = obj_file_path.replace('.obj', '.mtl')
            mtl_file_name = os.path.basename(mtl_file_path)
            
            # 导出MTL文件
            self._export_mtl_file(mtl_file_path)
            
            with open(obj_file_path, 'w', encoding='utf-8') as f:
                # 写入头部注释
                f.write(f"# Generated by XODRToOBJConverter v2.0.0\n")
                f.write(f"# Reference libOpenDRIVE implementation\n")
                f.write(f"# Vertices: {len(self.vertices)}\n")
                f.write(f"# Faces: {len(self.faces)}\n")
                f.write(f"# Materials: {len(self.materials)}\n")
                f.write(f"# Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # 引用MTL文件
                if self.materials:
                    f.write(f"mtllib {mtl_file_name}\n\n")
                
                # 写入顶点
                for vertex in self.vertices:
                    f.write(f"v {vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f}\n")
                
                f.write("\n")
                
                # 写入面（按材质分组）
                if self.materials:
                    # 按材质分组面
                    material_faces = {}
                    for i, face in enumerate(self.faces):
                        # 这里需要根据面的索引确定材质
                        # 简化处理：使用默认材质
                        material = 'asphalt'
                        if material not in material_faces:
                            material_faces[material] = []
                        material_faces[material].append(face)
                    
                    # 按材质输出面
                    for material, faces in material_faces.items():
                        f.write(f"usemtl {material}\n")
                        for face in faces:
                            f.write(f"f {face[0]} {face[1]} {face[2]}\n")
                        f.write("\n")
                else:
                    # 没有材质时直接输出面
                    for face in self.faces:
                        f.write(f"f {face[0]} {face[1]} {face[2]}\n")
                
            print(f"OBJ文件已导出到: {obj_file_path}")
            if self.materials:
                print(f"MTL文件已导出到: {mtl_file_path}")
            
        except Exception as e:
            print(f"导出OBJ文件时出错: {e}")
    
    def _export_mtl_file(self, mtl_file_path: str):
        """
        导出MTL材质文件
        
        Args:
            mtl_file_path: MTL文件路径
        """
        try:
            from datetime import datetime
            
            with open(mtl_file_path, 'w', encoding='utf-8') as f:
                f.write(f"# Generated by XODRToOBJConverter v2.0.0\n")
                f.write(f"# Material library for OpenDRIVE road network\n")
                f.write(f"# Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # 定义标准道路材质
                road_materials = {
                    'asphalt': {
                        'Ka': (0.2, 0.2, 0.2),  # 环境光
                        'Kd': (0.4, 0.4, 0.4),  # 漫反射
                        'Ks': (0.1, 0.1, 0.1),  # 镜面反射
                        'Ns': 10.0,             # 镜面指数
                        'd': 1.0                # 透明度
                    },
                    'concrete': {
                        'Ka': (0.3, 0.3, 0.3),
                        'Kd': (0.6, 0.6, 0.6),
                        'Ks': (0.2, 0.2, 0.2),
                        'Ns': 20.0,
                        'd': 1.0
                    },
                    'grass': {
                        'Ka': (0.1, 0.2, 0.1),
                        'Kd': (0.2, 0.6, 0.2),
                        'Ks': (0.0, 0.1, 0.0),
                        'Ns': 5.0,
                        'd': 1.0
                    },
                    'marking': {
                        'Ka': (0.8, 0.8, 0.8),
                        'Kd': (0.9, 0.9, 0.9),
                        'Ks': (0.3, 0.3, 0.3),
                        'Ns': 30.0,
                        'd': 1.0
                    }
                }
                
                # 输出所有使用的材质
                for material_name in self.materials.keys():
                    if material_name in road_materials:
                        mat = road_materials[material_name]
                    else:
                        # 默认材质
                        mat = road_materials['asphalt']
                    
                    f.write(f"newmtl {material_name}\n")
                    f.write(f"Ka {mat['Ka'][0]:.3f} {mat['Ka'][1]:.3f} {mat['Ka'][2]:.3f}\n")
                    f.write(f"Kd {mat['Kd'][0]:.3f} {mat['Kd'][1]:.3f} {mat['Kd'][2]:.3f}\n")
                    f.write(f"Ks {mat['Ks'][0]:.3f} {mat['Ks'][1]:.3f} {mat['Ks'][2]:.3f}\n")
                    f.write(f"Ns {mat['Ns']:.1f}\n")
                    f.write(f"d {mat['d']:.1f}\n")
                    f.write("\n")
                    
        except Exception as e:
            print(f"导出MTL文件时出错: {e}")
    
    def get_conversion_stats(self) -> Dict:
        """
        获取转换统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'vertices_count': len(self.vertices),
            'faces_count': len(self.faces),
            'road_width': self.road_width,
            'resolution': self.resolution
        }


def main():
    """
    测试函数
    """
    import sys
    import os
    
    if len(sys.argv) != 3:
        print("用法: python xodr_to_obj_converter.py <xodr_file> <obj_file>")
        return
    
    xodr_file = sys.argv[1]
    obj_file = sys.argv[2]
    
    if not os.path.exists(xodr_file):
        print(f"XODR文件不存在: {xodr_file}")
        return
    
    converter = XODRToOBJConverter()
    
    print(f"开始转换: {xodr_file} -> {obj_file}")
    
    if converter.convert_xodr_to_obj(xodr_file, obj_file):
        stats = converter.get_conversion_stats()
        print("转换成功!")
        print(f"顶点数量: {stats['vertices_count']}")
        print(f"面数量: {stats['faces_count']}")
        print(f"道路宽度: {stats['road_width']}米")
        print(f"分辨率: {stats['resolution']}米")
    else:
        print("转换失败!")


if __name__ == "__main__":
    main()