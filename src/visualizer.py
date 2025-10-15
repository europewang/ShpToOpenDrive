#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Open3D可视化器模块
用于显示SHP文件和OpenDRIVE文件的3D可视化

作者: ShpToOpenDrive项目组
版本: 1.3.0
"""

import open3d as o3d
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
from typing import List, Dict, Optional, Tuple

try:
    from .shp_reader import ShapefileReader
    from .geometry_converter import GeometryConverter
    from .opendrive_generator import OpenDriveGenerator
    from .xodr_parser import XODRParser
except ImportError:
    from shp_reader import ShapefileReader
    from geometry_converter import GeometryConverter
    from opendrive_generator import OpenDriveGenerator
    from xodr_parser import XODRParser


class RoadVisualizer:
    """
    基于Open3D的道路可视化器
    支持SHP和OpenDRIVE文件的加载、显示和导出
    """
    
    def __init__(self):
        """
        初始化可视化器
        """
        self.vis = None
        self.geometries = []
        self.current_shp_data = None
        self.current_xodr_data = None
        self.root = None
        self.xodr_parser = XODRParser()
        
        # 颜色配置
        self.colors = {
            'shp_lines': [1.0, 0.0, 0.0],      # 红色 - SHP线条
            'xodr_lines': [0.0, 0.0, 1.0],     # 蓝色 - OpenDRIVE线条
            'points': [0.0, 1.0, 0.0],         # 绿色 - 点
            'background': [0.1, 0.1, 0.1]      # 深灰色背景
        }
        
    def create_gui(self):
        """
        创建GUI界面
        """
        self.root = tk.Tk()
        self.root.title("ShpToOpenDrive 可视化器")
        self.root.geometry("400x300")
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 文件导入区域
        import_frame = ttk.LabelFrame(main_frame, text="文件导入", padding="5")
        import_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Button(import_frame, text="导入SHP文件", 
                  command=self.load_shp_file).grid(row=0, column=0, padx=5, pady=2)
        ttk.Button(import_frame, text="导入OpenDRIVE文件", 
                  command=self.load_xodr_file).grid(row=0, column=1, padx=5, pady=2)
        
        # 显示控制区域
        display_frame = ttk.LabelFrame(main_frame, text="显示控制", padding="5")
        display_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Button(display_frame, text="启动3D可视化", 
                  command=self.start_visualization).grid(row=0, column=0, padx=5, pady=2)
        ttk.Button(display_frame, text="清除场景", 
                  command=self.clear_scene).grid(row=0, column=1, padx=5, pady=2)
        
        # 导出区域
        export_frame = ttk.LabelFrame(main_frame, text="导出功能", padding="5")
        export_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 导出格式选择
        ttk.Label(export_frame, text="导出格式:").grid(row=0, column=0, padx=5, pady=2)
        self.export_format = tk.StringVar(value="xodr")
        format_combo = ttk.Combobox(export_frame, textvariable=self.export_format, 
                                   values=["xodr", "obj", "ply", "stl"], state="readonly")
        format_combo.grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Button(export_frame, text="导出文件", 
                  command=self.export_file).grid(row=1, column=0, columnspan=2, pady=5)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, 
                                relief=tk.SUNKEN, anchor=tk.W)
        status_label.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
    def update_status(self, message: str):
        """
        更新状态栏信息
        
        Args:
            message: 状态信息
        """
        print(f"状态: {message}")
        if hasattr(self, 'status_var') and self.status_var:
            self.status_var.set(message)
            if self.root:
                self.root.update_idletasks()
    
    def load_shp_file(self):
        """
        加载SHP文件
        """
        file_path = filedialog.askopenfilename(
            title="选择SHP文件",
            filetypes=[("Shapefile", "*.shp"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                self.update_status("正在加载SHP文件...")
                reader = ShapefileReader(file_path, coordinate_precision=3)
                self.current_shp_data = reader.read_features()
                self.update_status(f"已加载SHP文件: {os.path.basename(file_path)}")
                messagebox.showinfo("成功", f"成功加载SHP文件\n包含 {len(self.current_shp_data)} 个要素")
            except Exception as e:
                self.update_status("SHP文件加载失败")
                messagebox.showerror("错误", f"加载SHP文件失败:\n{str(e)}")
    
    def load_xodr_file(self):
        """
        加载OpenDRIVE文件
        """
        file_path = filedialog.askopenfilename(
            title="选择OpenDRIVE文件",
            filetypes=[("OpenDRIVE", "*.xodr"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                self.update_status("正在加载OpenDRIVE文件...")
                # 使用XODR解析器解析文件
                self.current_xodr_data = self.xodr_parser.parse_file(file_path)
                
                # 获取统计信息
                stats = self.xodr_parser.get_statistics()
                
                self.update_status(f"已加载OpenDRIVE文件: {os.path.basename(file_path)}")
                messagebox.showinfo(
                    "OpenDRIVE文件加载成功", 
                    f"文件: {os.path.basename(file_path)}\n"
                    f"道路数量: {stats['roads_count']}\n"
                    f"交叉口数量: {stats['junctions_count']}\n"
                    f"总长度: {stats['total_length']:.2f}米"
                )
            except Exception as e:
                self.update_status("OpenDRIVE文件加载失败")
                messagebox.showerror("错误", f"加载OpenDRIVE文件失败:\n{str(e)}")
    
    def shp_to_line_set(self, shp_data: List[Dict]) -> o3d.geometry.LineSet:
        """
        将SHP数据转换为Open3D线集
        
        Args:
            shp_data: SHP数据列表
            
        Returns:
            Open3D线集对象
        """
        points = []
        lines = []
        point_index = 0
        
        # 收集所有坐标点以计算边界
        all_coords = []
        for feature in shp_data:
            coords = feature.get('coordinates', [])
            all_coords.extend(coords)
        
        if not all_coords:
            return o3d.geometry.LineSet()
        
        # 计算坐标范围并进行归一化
        coords_array = np.array(all_coords)
        min_coords = coords_array.min(axis=0)
        max_coords = coords_array.max(axis=0)
        center = (min_coords + max_coords) / 2
        
        for i, feature in enumerate(shp_data):
            # 获取坐标数据
            coords = feature.get('coordinates', [])
            if len(coords) >= 2:
                # 添加点（归一化到中心点附近）
                for coord in coords:
                    # 将坐标平移到原点附近
                    normalized_x = coord[0] - center[0]
                    normalized_y = coord[1] - center[1]
                    
                    if len(coord) == 2:
                        points.append([normalized_x, normalized_y, 0.0])
                    else:
                        points.append([normalized_x, normalized_y, coord[2] if len(coord) > 2 else 0.0])
                
                # 添加线段
                for j in range(len(coords) - 1):
                    lines.append([point_index + j, point_index + j + 1])
                
                point_index += len(coords)
        
        # 创建线集
        line_set = o3d.geometry.LineSet()
        if points:
            line_set.points = o3d.utility.Vector3dVector(np.array(points))
            line_set.lines = o3d.utility.Vector2iVector(np.array(lines))
            
            # 设置颜色
            colors = [self.colors['shp_lines'] for _ in range(len(lines))]
            line_set.colors = o3d.utility.Vector3dVector(np.array(colors))
        
        return line_set
    
    def start_visualization(self):
        """
        启动3D可视化
        """
        if not self.current_shp_data and not self.current_xodr_data:
            messagebox.showwarning("警告", "请先加载SHP或OpenDRIVE文件")
            return
        
        # 在新线程中启动可视化, 避免阻塞GUI
        threading.Thread(target=self._run_visualization, daemon=True).start()
    
    def _run_visualization(self):
        """
        运行3D可视化（在独立线程中）
        """
        try:
            self.update_status("正在启动3D可视化...")
            
            # 创建可视化窗口
            self.vis = o3d.visualization.Visualizer()
            self.vis.create_window(window_name="ShpToOpenDrive 3D可视化", width=1200, height=800)
            
            # 清除之前的几何体
            self.geometries.clear()
            
            # 添加SHP数据
            if self.current_shp_data:
                shp_line_set = self.shp_to_line_set(self.current_shp_data)
                if len(shp_line_set.points) > 0:
                    self.vis.add_geometry(shp_line_set)
                    self.geometries.append(shp_line_set)
            
            # 添加OpenDRIVE数据
            if self.current_xodr_data:
                xodr_geometries = self.create_opendrive_geometry()
                for geom in xodr_geometries:
                    self.vis.add_geometry(geom)
                    self.geometries.append(geom)
            
            # 根据数据范围调整坐标轴大小
            if self.current_shp_data:
                # 计算合适的坐标轴大小（约为数据范围的1/10）
                all_coords = []
                for feature in self.current_shp_data:
                    coords = feature.get('coordinates', [])
                    all_coords.extend(coords)
                
                if all_coords:
                    coords_array = np.array(all_coords)
                    data_range = np.max(coords_array.max(axis=0) - coords_array.min(axis=0))
                    axis_size = max(data_range / 10, 50)  # 最小50单位
                else:
                    axis_size = 100
            else:
                axis_size = 100
            
            coordinate_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=axis_size)
            self.vis.add_geometry(coordinate_frame)
            self.geometries.append(coordinate_frame)
            
            # 设置渲染选项
            render_option = self.vis.get_render_option()
            render_option.background_color = np.array(self.colors['background'])
            render_option.line_width = 2.0
            
            # 设置视角
            view_control = self.vis.get_view_control()
            view_control.set_zoom(0.8)
            
            self.update_status("3D可视化已启动")
            
            # 运行可视化循环
            self.vis.run()
            self.vis.destroy_window()
            
            self.update_status("3D可视化已关闭")
            
        except Exception as e:
            self.update_status("3D可视化启动失败")
            messagebox.showerror("错误", f"3D可视化启动失败:\n{str(e)}")
    
    def clear_scene(self):
        """
        清除场景
        """
        self.current_shp_data = None
        self.current_xodr_data = None
        self.geometries.clear()
        self.update_status("场景已清除")
        messagebox.showinfo("信息", "场景已清除")
    
    def export_file(self):
        """
        导出文件
        """
        if not self.current_shp_data and not self.current_xodr_data:
            messagebox.showwarning("警告", "没有可导出的数据")
            return
        
        export_format = self.export_format.get()
        
        # 选择保存路径
        file_path = filedialog.asksaveasfilename(
            title="保存文件",
            defaultextension=f".{export_format}",
            filetypes=[
                (f"{export_format.upper()}文件", f"*.{export_format}"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_path:
            try:
                self.update_status(f"正在导出{export_format.upper()}文件...")
                
                if export_format == "xodr":
                    self._export_xodr(file_path)
                else:
                    self._export_3d_format(file_path, export_format)
                
                self.update_status(f"文件已导出: {os.path.basename(file_path)}")
                messagebox.showinfo("成功", f"文件已成功导出到:\n{file_path}")
                
            except Exception as e:
                self.update_status("文件导出失败")
                messagebox.showerror("错误", f"文件导出失败:\n{str(e)}")
    
    def _export_xodr(self, file_path: str):
        """
        导出OpenDRIVE格式
        
        Args:
            file_path: 导出文件路径
        """
        if self.current_shp_data:
            # 使用现有的转换器
            converter = GeometryConverter(coordinate_precision=3)
            generator = OpenDriveGenerator()
            
            # 转换几何数据
            converted_data = []
            for feature in self.current_shp_data:
                # geometry字段直接是LineString对象, 不是字典
                geometry = feature.get('geometry')
                if geometry is not None and hasattr(geometry, 'coords'):
                    # 使用coordinates字段获取坐标列表
                    coords = feature.get('coordinates', [])
                    if len(coords) >= 2:
                        converted_geom = converter.convert_road_geometry(coords)
                        converted_data.append(converted_geom)
            
            # 生成OpenDRIVE文件
            xodr_content = generator.generate_opendrive(converted_data)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(xodr_content)
        else:
            raise ValueError("没有SHP数据可导出")
    
    def _export_3d_format(self, file_path: str, format_type: str):
        """
        导出3D格式文件
        
        Args:
            file_path: 导出文件路径
            format_type: 格式类型 (obj, ply, stl)
        """
        if self.current_shp_data:
            line_set = self.shp_to_line_set(self.current_shp_data)
            
            if format_type == "obj":
                o3d.io.write_line_set(file_path, line_set)
            elif format_type == "ply":
                o3d.io.write_line_set(file_path, line_set)
            elif format_type == "stl":
                # STL需要三角网格, 将线集转换为管道网格
                mesh = self._line_set_to_mesh(line_set)
                o3d.io.write_triangle_mesh(file_path, mesh)
            else:
                raise ValueError(f"不支持的导出格式: {format_type}")
        else:
            raise ValueError("没有数据可导出")
    
    def _line_set_to_mesh(self, line_set: o3d.geometry.LineSet) -> o3d.geometry.TriangleMesh:
        """
        将线集转换为三角网格（用于STL导出）
        
        Args:
            line_set: 输入线集
            
        Returns:
            三角网格
        """
        # 简单实现：为每条线创建圆柱体
        mesh = o3d.geometry.TriangleMesh()
        
        points = np.asarray(line_set.points)
        lines = np.asarray(line_set.lines)
        
        for line in lines:
            start_point = points[line[0]]
            end_point = points[line[1]]
            
            # 创建圆柱体表示线段
            cylinder = o3d.geometry.TriangleMesh.create_cylinder(radius=0.5, height=1.0)
            
            # 计算变换矩阵
            direction = end_point - start_point
            length = np.linalg.norm(direction)
            
            if length > 0:
                direction = direction / length
                center = (start_point + end_point) / 2
                
                # 缩放和平移
                cylinder.scale(1.0, center=[0, 0, 0])
                cylinder.translate(center)
                
                mesh += cylinder
        
        return mesh
    
    def create_opendrive_geometry(self):
        """
        创建OpenDRIVE几何对象
        
        Returns:
            Open3D几何对象列表
        """
        geometries = []
        
        if self.current_xodr_data is None:
            return geometries
        
        try:
            # 获取道路中心线
            center_lines = self.xodr_parser.get_road_center_lines(resolution=2.0)
            
            for i, road_points in enumerate(center_lines):
                if len(road_points) < 2:
                    continue
                
                # 创建道路中心线
                line_set = o3d.geometry.LineSet()
                points = np.array(road_points)
                
                # 创建线段连接
                lines = []
                for j in range(len(points) - 1):
                    lines.append([j, j + 1])
                
                line_set.points = o3d.utility.Vector3dVector(points)
                line_set.lines = o3d.utility.Vector2iVector(lines)
                
                # 为不同道路设置不同颜色
                colors = []
                if i % 3 == 0:
                    color = [0, 1, 0]  # 绿色
                elif i % 3 == 1:
                    color = [0, 0, 1]  # 蓝色
                else:
                    color = [1, 0, 1]  # 紫色
                
                colors = [color] * len(lines)
                line_set.colors = o3d.utility.Vector3dVector(colors)
                
                geometries.append(line_set)
                
                # 添加道路起点标记
                if len(points) > 0:
                    sphere = o3d.geometry.TriangleMesh.create_sphere(radius=1.0)
                    sphere.translate(points[0])
                    sphere.paint_uniform_color([1, 0, 0])  # 红色起点
                    geometries.append(sphere)
            
            # 添加交叉口标记
            if 'junctions' in self.current_xodr_data:
                for junction in self.current_xodr_data['junctions']:
                    # 简化处理：在原点附近创建交叉口标记
                    cylinder = o3d.geometry.TriangleMesh.create_cylinder(radius=2.0, height=1.0)
                    cylinder.translate([0, 0, 0.5])
                    cylinder.paint_uniform_color([1, 1, 0])  # 黄色交叉口
                    geometries.append(cylinder)
            
        except Exception as e:
            messagebox.showerror("错误", f"创建OpenDRIVE几何失败: {str(e)}")
        
        return geometries
    
    def run(self):
        """
        运行可视化器应用
        """
        self.create_gui()
        self.update_status("ShpToOpenDrive可视化器已启动")
        self.root.mainloop()


def main():
    """
    主函数
    """
    visualizer = RoadVisualizer()
    visualizer.run()


if __name__ == "__main__":
    main()