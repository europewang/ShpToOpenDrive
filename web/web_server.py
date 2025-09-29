#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web3D可视化服务器
基于Flask提供SHP数据的Web API接口和静态文件服务
"""

import os
import json
import tempfile
import shutil
from werkzeug.utils import secure_filename
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import sys

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from shp_reader import ShapefileReader
from geometry_converter import GeometryConverter
from xodr_parser import XODRParser
from xodr_to_obj_converter import XODRToOBJConverter

app = Flask(__name__, 
           template_folder='templates',
           static_folder='static')
CORS(app)  # 允许跨域请求

# 文件上传配置
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB最大文件大小
app.config['UPLOAD_EXTENSIONS'] = ['.shp', '.shx', '.dbf', '.prj', '.cpg', '.sbn', '.sbx', '.xodr']
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()  # 临时上传目录

class Web3DServer:
    def __init__(self):
        self.shp_reader = None
        self.xodr_parser = XODRParser()
        self.geometry_converter = GeometryConverter()
        self.xodr_to_obj_converter = XODRToOBJConverter()
        self.current_data = None
        self.current_shp_path = None  # 存储当前SHP文件路径，用于XODR导出
        self.current_xodr_path = None  # 存储当前XODR文件路径，用于OBJ导出
        self.uploaded_files = {}  # 存储上传的文件路径
        self.current_obj_data = None  # 存储当前OBJ文件数据
        
    def validate_uploaded_files(self, files):
        """验证上传的文件是否包含必要的SHP文件组件"""
        required_extensions = ['.shp', '.shx', '.dbf']
        uploaded_extensions = [os.path.splitext(f.filename)[1].lower() for f in files]
        
        for ext in required_extensions:
            if ext not in uploaded_extensions:
                return False, f"缺少必要的文件: {ext}"
        
        return True, "文件验证通过"
    
    def save_uploaded_files(self, files):
        """保存上传的文件到临时目录"""
        upload_dir = tempfile.mkdtemp()
        saved_files = {}
        
        for file in files:
            if file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                
                ext = os.path.splitext(filename)[1].lower()
                saved_files[ext] = file_path
        
        return upload_dir, saved_files
    
    def load_xodr_file(self, file_path):
        """加载OpenDrive文件"""
        try:
            # 保存当前XODR文件路径，用于OBJ导出
            self.current_xodr_path = file_path
            
            # 解析XODR文件
            parse_result = self.xodr_parser.parse_file(file_path)
            if not parse_result:
                return None
            
            # 获取道路中心线数据
            roads_data = self.xodr_parser.get_road_center_lines()
            
            # 转换为GeoJSON格式
            geojson_data = self.xodr_to_geojson(roads_data)
            
            # 获取统计信息
            stats = self.xodr_parser.get_statistics()
            
            # 保存当前数据
            self.current_data = {
                'type': 'xodr',
                'data': geojson_data,
                'stats': {
                    'roads_count': stats['roads_count'],
                    'total_length': stats['total_length']
                }
            }
            
            return self.current_data
            
        except Exception as e:
            print(f"加载OpenDrive文件错误: {e}")
            return None
        
    def load_shp_file(self, file_path):
        """加载SHP文件"""
        try:
            # 保存原始SHP文件路径，用于后续的XODR导出
            self.current_shp_path = file_path
            
            # 创建新的读取器实例
            self.shp_reader = ShapefileReader(file_path)
            
            if not self.shp_reader.load_shapefile():
                return None
            
            # 转换坐标系（如果需要）
            if not self.shp_reader.convert_to_utm():
                print("坐标系转换失败，继续使用原坐标系")
            
            # 转换为局部坐标系（适合OpenDrive）
            if not self.shp_reader.convert_to_local_coordinates():
                print("局部坐标系转换失败，继续使用当前坐标系")
                
            # 获取道路数据
            roads_data = self.shp_reader.extract_roads_data()
            
            # 转换为GeoJSON格式
            geojson_data = self.shp_to_geojson(self.shp_reader.gdf)
            
            # 获取坐标偏移量
            coordinate_offset = self.shp_reader.get_coordinate_offset()
            
            # 保存当前数据
            self.current_data = {
                'type': 'shp',
                'data': geojson_data,
                'coordinate_offset': coordinate_offset,
                'stats': {
                    'roads_count': len(roads_data),
                    'total_length': self._calculate_total_length(roads_data)
                }
            }
            
            return self.current_data
            
        except Exception as e:
            print(f"加载SHP文件错误: {e}")
            return None
    
    def _calculate_total_length(self, roads_data):
        """计算道路总长度，兼容不同数据格式"""
        total_length = 0
        try:
            for road in roads_data:
                if 'length' in road:
                    # 普通道路格式
                    total_length += road['length']
                elif 'lanes' in road:
                    # Lane.shp格式
                    for lane in road['lanes']:
                        if 'left_boundary' in lane and 'geometry' in lane['left_boundary']:
                            total_length += lane['left_boundary']['geometry'].length
        except Exception as e:
            print(f"计算总长度错误: {e}")
            total_length = 0
        return total_length
        
    def shp_to_geojson(self, gdf):
        """将GeoDataFrame转换为GeoJSON格式"""
        try:
            # 坐标归一化处理
            if gdf is None or gdf.empty:
                return None
                
            # 收集所有坐标点
            all_coords = []
            for _, row in gdf.iterrows():
                geom = row.geometry
                if hasattr(geom, 'coords'):
                    all_coords.extend(list(geom.coords))
                elif hasattr(geom, 'geoms'):
                    for g in geom.geoms:
                        if hasattr(g, 'coords'):
                            all_coords.extend(list(g.coords))
            
            if not all_coords:
                return None
                
            # 计算边界和中心（支持二维和三维坐标）
            xs = [coord[0] for coord in all_coords]
            ys = [coord[1] for coord in all_coords]
            center_x = (min(xs) + max(xs)) / 2
            center_y = (min(ys) + max(ys)) / 2
            
            # 检查是否有Z坐标
            has_z = len(all_coords[0]) > 2 if all_coords else False
            center_z = 0
            if has_z:
                zs = [coord[2] for coord in all_coords]
                center_z = (min(zs) + max(zs)) / 2
            
            # 创建归一化的GeoJSON
            features = []
            for idx, row in gdf.iterrows():
                geom = row.geometry
                
                # 归一化坐标（支持二维和三维坐标）
                if hasattr(geom, 'coords'):
                    if has_z:
                        # 处理三维坐标
                        normalized_coords = [(coord[0] - center_x, coord[1] - center_y, coord[2] - center_z) for coord in geom.coords]
                    else:
                        # 处理二维坐标
                        normalized_coords = [(coord[0] - center_x, coord[1] - center_y) for coord in geom.coords]
                    feature = {
                        "type": "Feature",
                        "properties": {
                            "id": idx,
                            "road_type": row.get('ROAD_TYPE', 'unknown'),
                            "name": row.get('NAME', f'Road_{idx}')
                        },
                        "geometry": {
                            "type": "LineString",
                            "coordinates": normalized_coords
                        }
                    }
                    features.append(feature)
                    
            # 创建元数据
            metadata = {
                "center": [center_x, center_y, center_z] if has_z else [center_x, center_y],
                "bounds": {
                    "min_x": min(xs),
                    "max_x": max(xs),
                    "min_y": min(ys),
                    "max_y": max(ys)
                },
                "coordinate_system": str(gdf.crs) if hasattr(gdf, 'crs') and gdf.crs else "unknown",
                "feature_count": len(features),
                "has_elevation": has_z
            }
            
            if has_z:
                metadata["bounds"]["min_z"] = min(zs)
                metadata["bounds"]["max_z"] = max(zs)
            
            geojson = {
                "type": "FeatureCollection",
                "features": features,
                "metadata": metadata
            }
            
            return geojson
            
        except Exception as e:
            print(f"转换GeoJSON时出错: {e}")
            return None
    
    def xodr_to_geojson(self, roads_data):
        """将OpenDrive道路数据转换为GeoJSON格式"""
        try:
            if not roads_data:
                return None
            
            # roads_data是字典格式，键为道路ID，值包含coordinates和length
            # 收集所有坐标点用于归一化
            all_coords = []
            for road_id, road_info in roads_data.items():
                coords = road_info.get('coordinates', [])
                if coords:
                    all_coords.extend(coords)
            
            if not all_coords:
                return None
            
            # 计算中心点
            xs = [coord[0] for coord in all_coords]
            ys = [coord[1] for coord in all_coords]
            center_x = (min(xs) + max(xs)) / 2
            center_y = (min(ys) + max(ys)) / 2
            
            # 检查是否有Z坐标
            has_z = len(all_coords[0]) > 2 if all_coords else False
            center_z = 0
            if has_z:
                zs = [coord[2] for coord in all_coords]
                center_z = (min(zs) + max(zs)) / 2
            
            # 创建归一化的GeoJSON特征
            features = []
            for road_id, road_info in roads_data.items():
                coords = road_info.get('coordinates', [])
                if coords:
                    # 归一化坐标
                    if has_z:
                        normalized_coords = [(coord[0] - center_x, coord[1] - center_y, coord[2] - center_z) for coord in coords]
                    else:
                        normalized_coords = [(coord[0] - center_x, coord[1] - center_y) for coord in coords]
                    
                    feature = {
                        "type": "Feature",
                        "properties": {
                            "id": road_id,
                            "name": f"Road_{road_id}",
                            "length": road_info.get('length', 0),
                            "road_type": "xodr_road"
                        },
                        "geometry": {
                            "type": "LineString",
                            "coordinates": normalized_coords
                        }
                    }
                    features.append(feature)
            
            # 创建元数据
            metadata = {
                "center": [center_x, center_y, center_z] if has_z else [center_x, center_y],
                "bounds": {
                    "min_x": min(xs),
                    "max_x": max(xs),
                    "min_y": min(ys),
                    "max_y": max(ys)
                },
                "coordinate_system": "OpenDRIVE",
                "feature_count": len(features),
                "has_elevation": has_z
            }
            
            if has_z:
                metadata["bounds"]["min_z"] = min(zs)
                metadata["bounds"]["max_z"] = max(zs)
            
            geojson = {
                "type": "FeatureCollection",
                "features": features,
                "metadata": metadata
            }
            
            return geojson
            
        except Exception as e:
            print(f"转换OpenDrive GeoJSON时出错: {e}")
            return None
    
    def export_to_xodr(self, output_path, crs='EPSG:4326', version='1.7', road_width=3.5, lane_count=2, include_elevation=False):
        """导出当前数据为OpenDRIVE格式（旧版本兼容）"""
        try:
            if not self.current_data:
                return False
            
            # 检查是否有原始SHP文件路径
            if hasattr(self, 'current_shp_path') and self.current_shp_path:
                # 使用shp2xodr.py中的完整转换逻辑
                return self._convert_shp_to_xodr_with_main(self.current_shp_path, output_path, road_width, lane_count)
            else:
                # 如果没有原始SHP文件，使用基本的XODR创建方法
                return self._create_basic_xodr(output_path, version, road_width, lane_count, include_elevation)
            
        except Exception as e:
            print(f"导出XODR文件错误: {e}")
            return False
    
    def export_to_xodr_with_config(self, output_path, config_file='default', geometry_tolerance=1.0, 
                                   default_lane_width=3.5, default_num_lanes=1, default_speed_limit=50,
                                   use_arc_fitting=False, use_smooth_curves=True, preserve_detail=True):
        """使用配置参数导出当前数据为OpenDRIVE格式"""
        try:
            if not self.current_data:
                return False
            
            # 检查是否有原始SHP文件路径
            if hasattr(self, 'current_shp_path') and self.current_shp_path:
                # 使用shp2xodr.py中的完整转换逻辑，传入新的配置参数
                result = self._convert_shp_to_xodr_with_config(
                    self.current_shp_path, output_path, config_file, geometry_tolerance,
                    default_lane_width, default_num_lanes, default_speed_limit,
                    use_arc_fitting, use_smooth_curves, preserve_detail
                )
            else:
                # 如果没有原始SHP文件，使用基本的XODR创建方法
                result = self._create_basic_xodr_with_config(
                    output_path, geometry_tolerance, default_lane_width, 
                    default_num_lanes, default_speed_limit, use_arc_fitting, 
                    use_smooth_curves, preserve_detail
                )
            
            # 如果导出成功，保存当前XODR文件路径
            if result:
                self.current_xodr_path = output_path
            
            return result
            
        except Exception as e:
            print(f"导出XODR文件错误: {e}")
            return False
    
    def _convert_shp_to_xodr_with_main(self, shp_path, output_path, road_width=3.5, lane_count=2):
        """使用shp2xodr.py中的完整转换逻辑（旧版本兼容）"""
        try:
            import sys
            import os
            
            # 添加src目录到Python路径
            src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
            if src_path not in sys.path:
                sys.path.insert(0, src_path)
            
            from shp2xodr import ShpToOpenDriveConverter
            
            # 创建转换器配置
            config = {
                'default_lane_width': road_width,
                'default_num_lanes': lane_count,
                'geometry_tolerance': 1.0,
                'min_road_length': 1.0,
                'use_smooth_curves': True,
                'preserve_detail': True,
                'curve_fitting_mode': 'parampoly3',
                'coordinate_precision': 3
            }
            
            # 创建转换器实例
            converter = ShpToOpenDriveConverter(config)
            
            # 执行转换
            success = converter.convert(shp_path, output_path)
            
            if success:
                print(f"成功使用shp2xodr.py转换逻辑导出XODR文件: {output_path}")
                return True
            else:
                print("使用shp2xodr.py转换逻辑失败")
                return False
                
        except Exception as e:
            print(f"调用shp2xodr.py转换逻辑时出错: {e}")
            return False
    
    def _convert_shp_to_xodr_with_config(self, shp_path, output_path, config_file='default', 
                                         geometry_tolerance=1.0, default_lane_width=3.5, 
                                         default_num_lanes=1, default_speed_limit=50,
                                         use_arc_fitting=False, use_smooth_curves=True, 
                                         preserve_detail=True):
        """使用配置参数的shp2xodr.py转换逻辑"""
        try:
            import sys
            import os
            import json
            
            # 添加src目录到Python路径
            src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
            if src_path not in sys.path:
                sys.path.insert(0, src_path)
            
            from shp2xodr import ShpToOpenDriveConverter
            
            # 加载配置文件
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', f'{config_file}.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    base_config = json.load(f)
            else:
                # 使用默认配置
                base_config = {
                    "conversion": {
                        "geometry_tolerance": 1.0,
                        "min_road_length": 1.0,
                        "default_lane_width": 3.5,
                        "default_num_lanes": 1,
                        "default_speed_limit": 50,
                        "curve_fitting_mode": "parampoly3",
                        "polynomial_degree": 3,
                        "curve_smoothness": 0.1,
                        "coordinate_precision": 3
                    }
                }
            
            # 更新配置参数
            config = base_config.get('conversion', {})
            config.update({
                'geometry_tolerance': geometry_tolerance,
                'default_lane_width': default_lane_width,
                'default_num_lanes': default_num_lanes,
                'default_speed_limit': default_speed_limit,
                'use_smooth_curves': use_smooth_curves,
                'preserve_detail': preserve_detail,
                'curve_fitting_mode': 'arc' if use_arc_fitting else config.get('curve_fitting_mode', 'parampoly3')
            })
            
            # 创建转换器实例
            converter = ShpToOpenDriveConverter(config)
            
            # 执行转换
            success = converter.convert(shp_path, output_path)
            
            if success:
                print(f"成功使用配置参数转换逻辑导出XODR文件: {output_path}")
                return True
            else:
                print("使用配置参数转换逻辑失败")
                return False
                
        except Exception as e:
            print(f"调用配置参数转换逻辑时出错: {e}")
            return False
    
    def export_to_shp(self, output_path, crs='EPSG:4326', include_attributes=True, geometry_type='LineString'):
        """导出当前数据为Shapefile格式"""
        try:
            if not self.current_data:
                return False
            
            # 检查是否有格式转换工具
            if not hasattr(self.geometry_converter, 'geojson_to_shp'):
                # 如果没有现成的转换方法，使用基本的转换
                return self._create_basic_shp(output_path, crs, include_attributes, geometry_type)
            
            # 使用格式转换工具
            geojson_data = self.current_data['data']
            result = self.geometry_converter.geojson_to_shp(
                geojson_data,
                output_path,
                crs=crs,
                include_attributes=include_attributes,
                geometry_type=geometry_type
            )
            
            return result
            
        except Exception as e:
            print(f"导出Shapefile错误: {e}")
            return False
    
    def _create_basic_xodr(self, output_path, version='1.7', road_width=3.5, lane_count=2, include_elevation=False):
        """创建基本的OpenDRIVE文件"""
        try:
            geojson_data = self.current_data['data']
            features = geojson_data.get('features', [])
            
            # 创建基本的OpenDRIVE XML结构
            xodr_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<OpenDRIVE>
    <header revMajor="{version.split('.')[0]}" revMinor="{version.split('.')[1]}" name="Exported from ShpToOpenDrive" version="1.00">
        <geoReference><![CDATA[+proj=longlat +datum=WGS84 +no_defs]]></geoReference>
    </header>
'''
            
            # 添加道路数据
            for i, feature in enumerate(features):
                geometry = feature.get('geometry', {})
                coordinates = geometry.get('coordinates', [])
                
                if coordinates:
                    road_id = i + 1
                    road_length = len(coordinates) * 10  # 简化长度计算
                    
                    xodr_content += f'''    <road name="Road_{road_id}" length="{road_length}" id="{road_id}" junction="-1">
'''
                    
                    # 添加几何信息
                    if coordinates:
                        start_x, start_y = coordinates[0][:2]
                        xodr_content += f'''        <planView>
            <geometry s="0.0" x="{start_x}" y="{start_y}" hdg="0.0" length="{road_length}">
                <line/>
            </geometry>
        </planView>
'''
                    
                    # 添加车道信息
                    xodr_content += f'''        <lanes>
            <laneSection s="0.0">
                <center>
                    <lane id="0" type="none" level="true">
                        <roadMark sOffset="0.0" type="solid" weight="standard" color="standard" width="0.13"/>
                    </lane>
                </center>
                <right>
'''
                    
                    for lane_id in range(1, lane_count + 1):
                        xodr_content += f'''                    <lane id="-{lane_id}" type="driving" level="true">
                        <width sOffset="0.0" a="{road_width}" b="0.0" c="0.0" d="0.0"/>
                        <roadMark sOffset="0.0" type="broken" weight="standard" color="standard" width="0.13"/>
                    </lane>
'''
                    
                    xodr_content += '''                </right>
            </laneSection>
        </lanes>
    </road>
'''
            
            xodr_content += '</OpenDRIVE>'
            
            # 写入文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(xodr_content)
            
            return True
            
        except Exception as e:
            print(f"创建基本XODR文件错误: {e}")
            return False
    
    def _create_basic_xodr_with_config(self, output_path, geometry_tolerance=1.0, default_lane_width=3.5, 
                                       default_num_lanes=1, default_speed_limit=50, use_arc_fitting=False, 
                                       use_smooth_curves=True, preserve_detail=True):
        """使用配置参数创建基本的XODR文件"""
        try:
            if not self.current_data:
                return False
            
            geojson_data = self.current_data['data']
            features = geojson_data.get('features', [])
            
            # 创建XODR文件内容
            xodr_content = '''<?xml version="1.0" encoding="UTF-8"?>
<OpenDRIVE>
    <header revMajor="1" revMinor="7" name="" version="1.00" date="" north="0.0" south="0.0" east="0.0" west="0.0" vendor="ShpToOpenDrive">
        <geoReference><![CDATA[+proj=utm +zone=33 +datum=WGS84 +units=m +no_defs]]></geoReference>
    </header>
'''
            
            # 处理每个要素
            for i, feature in enumerate(features):
                geometry = feature.get('geometry', {})
                coordinates = geometry.get('coordinates', [])
                
                if coordinates:
                    road_id = i + 1
                    road_length = len(coordinates) * 10  # 简化长度计算
                    
                    xodr_content += f'''    <road name="Road_{road_id}" length="{road_length}" id="{road_id}" junction="-1">
'''
                    
                    # 添加几何信息
                    if coordinates:
                        start_x, start_y = coordinates[0][:2]
                        xodr_content += f'''        <planView>
            <geometry s="0.0" x="{start_x}" y="{start_y}" hdg="0.0" length="{road_length}">
                <line/>
            </geometry>
        </planView>
'''
                    
                    # 添加车道信息
                    xodr_content += f'''        <lanes>
            <laneSection s="0.0">
                <center>
                    <lane id="0" type="none" level="true">
                        <roadMark sOffset="0.0" type="solid" weight="standard" color="standard" width="0.13"/>
                    </lane>
                </center>
                <right>
'''
                    
                    for lane_id in range(1, default_num_lanes + 1):
                        xodr_content += f'''                    <lane id="-{lane_id}" type="driving" level="true">
                        <width sOffset="0.0" a="{default_lane_width}" b="0.0" c="0.0" d="0.0"/>
                        <roadMark sOffset="0.0" type="broken" weight="standard" color="standard" width="0.13"/>
                        <speed sOffset="0.0" max="{default_speed_limit}"/>
                    </lane>
'''
                    
                    xodr_content += '''                </right>
            </laneSection>
        </lanes>
    </road>
'''
            
            xodr_content += '</OpenDRIVE>'
            
            # 写入文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(xodr_content)
            
            print(f"成功使用配置参数创建基本XODR文件: {output_path}")
            return True
            
        except Exception as e:
            print(f"使用配置参数创建基本XODR文件错误: {e}")
            return False
    
    def _create_basic_shp(self, output_path, crs='EPSG:4326', include_attributes=True, geometry_type='LineString'):
        """创建基本的Shapefile文件"""
        try:
            import geopandas as gpd
            from shapely.geometry import LineString, Point, Polygon
            import pandas as pd
            
            geojson_data = self.current_data['data']
            features = geojson_data.get('features', [])
            
            # 准备数据
            geometries = []
            attributes = []
            
            for feature in features:
                geometry = feature.get('geometry', {})
                properties = feature.get('properties', {})
                coordinates = geometry.get('coordinates', [])
                
                if coordinates:
                    # 创建几何对象
                    if geometry_type == 'LineString':
                        geom = LineString(coordinates)
                    elif geometry_type == 'Point':
                        geom = Point(coordinates[0] if coordinates else [0, 0])
                    else:
                        geom = LineString(coordinates)  # 默认使用LineString
                    
                    geometries.append(geom)
                    
                    # 添加属性
                    if include_attributes:
                        attributes.append({
                            'id': properties.get('id', 0),
                            'name': properties.get('name', 'Unknown'),
                            'road_type': properties.get('road_type', 'unknown')
                        })
                    else:
                        attributes.append({'id': len(geometries)})
            
            # 创建GeoDataFrame
            if geometries:
                gdf = gpd.GeoDataFrame(attributes, geometry=geometries, crs=crs)
                gdf.to_file(output_path)
                return True
            
            return False
            
        except Exception as e:
            print(f"创建基本Shapefile错误: {e}")
            return False

# 创建Web3D服务器实例
web3d_server = Web3DServer()

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/upload_shp', methods=['POST'])
def upload_shp():
    """上传SHP文件"""
    try:
        if 'files' not in request.files:
            return jsonify({"error": "没有选择文件"}), 400
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({"error": "没有选择有效文件"}), 400
        
        # 验证文件
        is_valid, message = web3d_server.validate_uploaded_files(files)
        if not is_valid:
            return jsonify({"error": message}), 400
        
        # 保存文件
        upload_dir, saved_files = web3d_server.save_uploaded_files(files)
        
        # 获取SHP文件路径
        shp_path = saved_files.get('.shp')
        if not shp_path:
            shutil.rmtree(upload_dir, ignore_errors=True)
            return jsonify({"error": "未找到SHP文件"}), 400
        
        # 加载SHP文件
        result = web3d_server.load_shp_file(shp_path)
        if not result:
            shutil.rmtree(upload_dir, ignore_errors=True)
            return jsonify({"error": "无法读取上传的SHP文件"}), 400
        
        return jsonify({
            "success": True,
            "message": f"成功上传并加载 {result['stats']['roads_count']} 条道路",
            "data": result['data'],
            "filename": os.path.basename(shp_path),
            "upload_dir": upload_dir
        })
        
    except Exception as e:
        return jsonify({"error": f"上传SHP文件时出错: {str(e)}"}), 500

@app.route('/api/upload_xodr', methods=['POST'])
def upload_xodr():
    """上传OpenDrive文件"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "没有选择文件"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "没有选择有效文件"}), 400
        
        # 检查文件扩展名
        if not file.filename.lower().endswith('.xodr'):
            return jsonify({"error": "请选择.xodr文件"}), 400
        
        # 保存文件
        upload_dir = tempfile.mkdtemp()
        filename = secure_filename(file.filename)
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # 加载OpenDrive文件
        result = web3d_server.load_xodr_file(file_path)
        if not result:
            shutil.rmtree(upload_dir, ignore_errors=True)
            return jsonify({"error": "无法读取上传的OpenDrive文件"}), 400
        
        return jsonify({
            "success": True,
            "message": f"成功上传并加载 {result['stats']['roads_count']} 条道路",
            "data": result['data'],
            "filename": filename,
            "upload_dir": upload_dir
        })
        
    except Exception as e:
        return jsonify({"error": f"上传OpenDrive文件时出错: {str(e)}"}), 500

@app.route('/api/convert_xodr_to_obj', methods=['POST'])
def convert_xodr_to_obj():
    """
    将XODR文件转换为OBJ格式API接口
    
    功能：支持两种模式的XODR到OBJ转换
    方法：POST
    
    模式1 - 文件上传模式（兼容性）：
    - 上传XODR文件进行转换
    - 支持坐标偏移参数
    
    模式2 - JSON参数模式（推荐）：
    请求参数（JSON）：
    - fileName: 输出文件名（默认：export.obj）
    - resolution: 网格分辨率（默认：0.2）
    - eps: 精度参数（默认：1e-6）
    - includeLaneHeight: 包含车道高度（默认：false）
    - includeRoadObjects: 包含道路对象（默认：true）
    - meshPrecision: 网格精度（默认：0.1）
    - qualityMode: 质量模式（high/medium/low，默认：medium）
    
    返回：OBJ文件下载或错误信息
    """
    try:
        # 检查是否为文件上传请求
        if 'file' in request.files:
            # 文件上传模式（保持兼容性）
            file = request.files['file']
            if file.filename == '':
                return jsonify({"error": "没有选择有效文件"}), 400
            
            # 检查文件扩展名
            if not file.filename.lower().endswith('.xodr'):
                return jsonify({"error": "请选择.xodr文件"}), 400
            
            # 保存上传的XODR文件
            upload_dir = tempfile.mkdtemp()
            filename = secure_filename(file.filename)
            xodr_path = os.path.join(upload_dir, filename)
            file.save(xodr_path)
            
            # 生成OBJ文件名
            obj_filename = os.path.splitext(filename)[0] + '.obj'
            obj_path = os.path.join(upload_dir, obj_filename)
            
            # 获取坐标偏移参数（如果提供）
            coordinate_offset = (0.0, 0.0)
            if 'coordinate_offset' in request.form:
                try:
                    offset_data = json.loads(request.form['coordinate_offset'])
                    coordinate_offset = (float(offset_data.get('x', 0.0)), float(offset_data.get('y', 0.0)))
                except (json.JSONDecodeError, ValueError, TypeError):
                    coordinate_offset = (0.0, 0.0)
            
            # 使用默认参数创建转换器
            converter = XODRToOBJConverter(
                resolution=0.2,  # 中级质量模式
                with_lane_height=False,
                coordinate_offset=coordinate_offset,
                verbose=True
            )
        else:
            # JSON参数模式（新的导出功能）
            data = request.get_json()
            if not data:
                return jsonify({"error": "缺少导出参数"}), 400
            
            # 检查是否有当前XODR数据
            if not hasattr(web3d_server, 'current_xodr_path') or not web3d_server.current_xodr_path:
                return jsonify({"error": "没有可用的XODR数据"}), 400
            
            # 获取导出参数
            file_name = data.get('fileName', 'export.obj')
            resolution = data.get('resolution', 0.2)
            eps = data.get('eps', 1e-6)
            include_lane_height = data.get('includeLaneHeight', False)
            include_road_objects = data.get('includeRoadObjects', True)
            mesh_precision = data.get('meshPrecision', 0.1)
            quality_mode = data.get('qualityMode', 'medium')
            
            # 根据质量模式调整参数
            if quality_mode == 'high':
                resolution = 0.1
                include_lane_height = True
            elif quality_mode == 'low':
                resolution = 0.5
                include_lane_height = False
            
            # 创建临时文件
            upload_dir = tempfile.mkdtemp()
            obj_path = os.path.join(upload_dir, file_name)
            
            # 创建转换器
            converter = XODRToOBJConverter(
                resolution=resolution,
                eps=eps,
                with_lane_height=include_lane_height,
                with_road_objects=include_road_objects,
                mesh_precision=mesh_precision,
                verbose=True
            )
            
            xodr_path = web3d_server.current_xodr_path
            obj_filename = file_name
        
        # 转换XODR到OBJ
        success = converter.convert(xodr_path, obj_path)
        
        if not success:
            shutil.rmtree(upload_dir, ignore_errors=True)
            return jsonify({"error": "XODR到OBJ转换失败"}), 500
        
        # 检查OBJ文件是否生成成功
        if not os.path.exists(obj_path):
            shutil.rmtree(upload_dir, ignore_errors=True)
            return jsonify({"error": "OBJ文件生成失败"}), 500
        
        # 返回OBJ文件
        return send_from_directory(upload_dir, obj_filename, as_attachment=True, 
                                 download_name=obj_filename, mimetype='application/octet-stream')
        
    except Exception as e:
        return jsonify({"error": f"转换XODR到OBJ时出错: {str(e)}"}), 500

@app.route('/api/convert_shp_to_obj', methods=['POST'])
def convert_shp_to_obj():
    """将SHP文件转换为OBJ格式（完整流程：SHP -> XODR -> OBJ）"""
    try:
        # 验证上传的文件
        files = request.files.getlist('files')
        if not files:
            return jsonify({"error": "没有选择文件"}), 400
        
        # 验证SHP文件组件
        if not web3d_server.validate_uploaded_files(files):
            return jsonify({"error": "请上传完整的SHP文件组件(.shp, .shx, .dbf)"}), 400
        
        # 保存上传的文件
        upload_dir = tempfile.mkdtemp()
        shp_path = None
        
        for file in files:
            if file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                
                if filename.lower().endswith('.shp'):
                    shp_path = file_path
        
        if not shp_path:
            shutil.rmtree(upload_dir, ignore_errors=True)
            return jsonify({"error": "未找到.shp文件"}), 400
        
        # 第一步：SHP -> XODR
        xodr_filename = os.path.splitext(os.path.basename(shp_path))[0] + '.xodr'
        xodr_path = os.path.join(upload_dir, xodr_filename)
        
        # 读取SHP文件并计算坐标偏移
        shp_reader = ShapefileReader()
        shp_data = shp_reader.read_shapefile(shp_path)
        
        if not shp_data or 'features' not in shp_data:
            shutil.rmtree(upload_dir, ignore_errors=True)
            return jsonify({"error": "无法读取SHP文件"}), 500
        
        # 计算坐标偏移（使用所有坐标的最小值，与SHP文件处理方式一致）
        min_x = float('inf')
        min_y = float('inf')
        
        for feature in shp_data['features']:
            if 'geometry' in feature and 'coordinates' in feature['geometry']:
                coords = feature['geometry']['coordinates']
                if coords:
                    # 处理不同的几何类型
                    if isinstance(coords[0], list):
                        # LineString或MultiLineString
                        for coord in coords:
                            if isinstance(coord, list) and len(coord) >= 2:
                                min_x = min(min_x, float(coord[0]))
                                min_y = min(min_y, float(coord[1]))
                    elif len(coords) >= 2:
                        # Point
                        min_x = min(min_x, float(coords[0]))
                        min_y = min(min_y, float(coords[1]))
        
        # 如果没有找到有效坐标，使用默认值
        if min_x == float('inf') or min_y == float('inf'):
            coordinate_offset = (0.0, 0.0)
        else:
            coordinate_offset = (min_x, min_y)
        
        # 转换SHP到XODR
        geometry_converter = GeometryConverter()
        opendrive_data = geometry_converter.convert_to_opendrive(shp_data)
        
        if not opendrive_data:
            shutil.rmtree(upload_dir, ignore_errors=True)
            return jsonify({"error": "SHP到XODR转换失败"}), 500
        
        # 保存XODR文件
        with open(xodr_path, 'w', encoding='utf-8') as f:
            f.write(opendrive_data)
        
        # 第二步：XODR -> OBJ（应用坐标偏移）
        obj_filename = os.path.splitext(os.path.basename(shp_path))[0] + '.obj'
        obj_path = os.path.join(upload_dir, obj_filename)
        
        # 创建带坐标偏移的转换器
        converter = XODRToOBJConverter(
            resolution=0.2,  # 中级质量模式
            with_lane_height=False,
            coordinate_offset=coordinate_offset,
            verbose=True
        )
        
        # 转换XODR到OBJ
        success = converter.convert(xodr_path, obj_path)
        
        if not success or not os.path.exists(obj_path):
            shutil.rmtree(upload_dir, ignore_errors=True)
            return jsonify({"error": "XODR到OBJ转换失败"}), 500
        
        # 返回OBJ文件和坐标偏移信息
        response_data = {
            "obj_file": obj_filename,
            "coordinate_offset": {
                "x": coordinate_offset[0],
                "y": coordinate_offset[1]
            }
        }
        
        # 返回OBJ文件
        return send_from_directory(upload_dir, obj_filename, as_attachment=True, 
                                 download_name=obj_filename, mimetype='application/octet-stream')
        
    except Exception as e:
        return jsonify({"error": f"转换SHP到OBJ时出错: {str(e)}"}), 500



@app.route('/api/current_data')
def get_current_data():
    """获取当前加载的数据"""
    if web3d_server.current_data:
        return jsonify(web3d_server.current_data)
    else:
        return jsonify({"error": "没有加载的数据"}), 404

@app.route('/api/export_xodr', methods=['POST'])
def export_xodr():
    """
    导出为OpenDRIVE格式API接口
    
    功能：将当前加载的SHP数据转换为OpenDRIVE格式并下载
    方法：POST
    
    请求参数（JSON）：
    - fileName: 输出文件名（默认：export.xodr）
    - configFile: 配置文件名（默认：default）
    - geometryTolerance: 几何容差（默认：1.0）
    - defaultLaneWidth: 默认车道宽度（默认：3.5）
    - defaultNumLanes: 默认车道数量（默认：1）
    - defaultSpeedLimit: 默认限速（默认：50）
    - useArcFitting: 是否使用圆弧拟合（默认：false）
    - useSmoothCurves: 是否使用平滑曲线（默认：true）
    - preserveDetail: 是否保留细节（默认：true）
    
    返回：XODR文件下载或错误信息
    """
    try:
        if not web3d_server.current_data:
            return jsonify({"error": "没有加载的数据可供导出"}), 400
        
        # 获取导出参数
        data = request.get_json()
        if not data:
            return jsonify({"error": "缺少导出参数"}), 400
        
        file_name = data.get('fileName', 'export.xodr')
        config_file = data.get('configFile', 'default')
        geometry_tolerance = data.get('geometryTolerance', 1.0)
        default_lane_width = data.get('defaultLaneWidth', 3.5)
        default_num_lanes = data.get('defaultNumLanes', 1)
        default_speed_limit = data.get('defaultSpeedLimit', 50)
        use_arc_fitting = data.get('useArcFitting', False)
        use_smooth_curves = data.get('useSmoothCurves', True)
        preserve_detail = data.get('preserveDetail', True)
        
        # 创建临时文件
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, file_name)
        
        # 调用格式转换工具导出XODR
        result = web3d_server.export_to_xodr_with_config(
            output_path,
            config_file=config_file,
            geometry_tolerance=geometry_tolerance,
            default_lane_width=default_lane_width,
            default_num_lanes=default_num_lanes,
            default_speed_limit=default_speed_limit,
            use_arc_fitting=use_arc_fitting,
            use_smooth_curves=use_smooth_curves,
            preserve_detail=preserve_detail
        )
        
        if not result:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return jsonify({"error": "导出XODR文件失败"}), 500
        
        # 返回文件
        return send_from_directory(temp_dir, file_name, as_attachment=True)
        
    except Exception as e:
        return jsonify({"error": f"导出XODR文件时出错: {str(e)}"}), 500

@app.route('/api/export_shp', methods=['POST'])
def export_shp():
    """导出为Shapefile格式"""
    try:
        if not web3d_server.current_data:
            return jsonify({"error": "没有加载的数据可供导出"}), 400
        
        # 获取导出参数
        data = request.get_json()
        if not data:
            return jsonify({"error": "缺少导出参数"}), 400
        
        file_name = data.get('fileName', 'export.shp')
        
        # 创建临时文件
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, file_name)
        
        # 调用格式转换工具导出SHP（使用默认参数）
        result = web3d_server.export_to_shp(
            output_path,
            crs='EPSG:4326',
            include_attributes=True,
            geometry_type='LineString'
        )
        
        if not result:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return jsonify({"error": "导出Shapefile失败"}), 500
        
        # 返回文件
        return send_from_directory(temp_dir, file_name, as_attachment=True)
        
    except Exception as e:
        return jsonify({"error": f"导出Shapefile时出错: {str(e)}"}), 500

@app.route('/api/get_coordinate_offset', methods=['GET'])
def get_coordinate_offset():
    """获取坐标偏移量信息"""
    try:
        if not web3d_server.current_data:
            return jsonify({"error": "没有加载的数据"}), 400
        
        coordinate_offset = web3d_server.current_data.get('coordinate_offset', {'x': 0.0, 'y': 0.0})
        
        return jsonify({
            "success": True,
            "coordinate_offset": coordinate_offset
        })
        
    except Exception as e:
        return jsonify({"error": f"获取坐标偏移量时出错: {str(e)}"}), 500

@app.route('/api/save_obj_data', methods=['POST'])
def save_obj_data():
    """保存上传的OBJ文件数据"""
    try:
        if 'obj_file' not in request.files:
            return jsonify({'error': '没有找到OBJ文件'}), 400
        
        obj_file = request.files['obj_file']
        if obj_file.filename == '':
            return jsonify({'error': 'OBJ文件名为空'}), 400
        
        # 读取OBJ文件内容
        obj_content = obj_file.read().decode('utf-8')
        
        # 保存到服务器的current_obj_data属性
        web3d_server.current_obj_data = obj_content
        
        return jsonify({'message': 'OBJ数据保存成功'}), 200
        
    except Exception as e:
        return jsonify({'error': f'保存OBJ数据失败: {str(e)}'}), 500

@app.route('/api/convert_obj_to_obj', methods=['POST'])
def convert_obj_to_obj():
    """重新导出OBJ文件（可能用于重新设置参数或重命名）"""
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求数据为空"}), 400
        
        filename = data.get('fileName', 'exported_model')
        if not filename.endswith('.obj'):
            filename += '.obj'
        
        # 检查是否有可用的OBJ数据
        if not hasattr(web3d_server, 'current_obj_data') or web3d_server.current_obj_data is None:
            return jsonify({'error': '没有可用的OBJ数据'}), 400
        
        # 创建临时目录
        upload_dir = tempfile.mkdtemp()
        obj_path = os.path.join(upload_dir, filename)
        
        # 将当前OBJ数据写入文件
        with open(obj_path, 'w', encoding='utf-8') as f:
            f.write(web3d_server.current_obj_data)
        
        # 返回文件
        return send_from_directory(upload_dir, filename, as_attachment=True, 
                                 download_name=filename, mimetype='application/octet-stream')
        
    except Exception as e:
        return jsonify({"error": f"导出OBJ文件时出错: {str(e)}"}), 500

# 静态文件服务
@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory('js', filename)

@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory('css', filename)

if __name__ == '__main__':
    print("启动Web3D可视化服务器...")
    print("访问地址: http://localhost:5000")
    
    # 打印所有注册的路由
    print("\n注册的路由:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint} [{', '.join(rule.methods)}]")
    print()
    
    app.run(debug=True, host='0.0.0.0', port=5000)