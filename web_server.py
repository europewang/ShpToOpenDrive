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
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from shp_reader import ShapefileReader
from geometry_converter import GeometryConverter
from xodr_parser import XODRParser

app = Flask(__name__, 
           template_folder='web/templates',
           static_folder='web/static')
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
        self.current_data = None
        self.uploaded_files = {}  # 存储上传的文件路径
        
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
        try:
            # 创建唯一的临时目录
            upload_dir = tempfile.mkdtemp()
            saved_files = {}
            shp_file_path = None
            
            for file in files:
                if file.filename == '':
                    continue
                    
                filename = secure_filename(file.filename)
                file_ext = os.path.splitext(filename)[1].lower()
                
                if file_ext in app.config['UPLOAD_EXTENSIONS']:
                    file_path = os.path.join(upload_dir, filename)
                    file.save(file_path)
                    saved_files[file_ext] = file_path
                    
                    if file_ext == '.shp':
                        shp_file_path = file_path
            
            self.uploaded_files = saved_files
            return shp_file_path, upload_dir
            
        except Exception as e:
            return None
    
    def load_xodr_file(self, file_path):
        """加载OpenDrive文件"""
        try:
            # 解析OpenDrive文件
            xodr_data = self.xodr_parser.parse_file(file_path)
            
            if not xodr_data:
                return None
            
            # 获取道路中心线数据
            center_lines = self.xodr_parser.get_road_center_lines(resolution=2.0)
            
            # 转换为GeoJSON格式
            geojson_data = self.xodr_to_geojson(center_lines)
            
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
            # 创建新的读取器实例
            self.shp_reader = ShapefileReader(file_path)
            
            if not self.shp_reader.load_shapefile():
                return None
                
            # 获取道路数据
            roads_data = self.shp_reader.extract_roads_data()
            
            # 转换为GeoJSON格式
            geojson_data = self.shp_to_geojson(self.shp_reader.gdf)
            
            # 保存当前数据
            self.current_data = {
                'type': 'shp',
                'data': geojson_data,
                'stats': {
                    'roads_count': len(roads_data),
                    'total_length': sum(road['length'] for road in roads_data)
                }
            }
            
            return self.current_data
            
        except Exception as e:
            print(f"加载SHP文件错误: {e}")
            return None
        
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
                    
            # 构建metadata
            metadata = {
                "center": [center_x, center_y] + ([center_z] if has_z else []),
                "bounds": {
                    "min_x": min(xs),
                    "max_x": max(xs),
                    "min_y": min(ys),
                    "max_y": max(ys)
                },
                "feature_count": len(features),
                "has_z_coordinate": has_z
            }
            
            # 如果有Z坐标，添加Z轴边界信息
            if has_z:
                zs = [coord[2] for coord in all_coords]
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
    
    def xodr_to_geojson(self, center_lines):
        """将OpenDrive中心线数据转换为GeoJSON格式"""
        try:
            features = []
            all_coords = []
            
            # 收集所有坐标点用于计算边界和中心
            for road_id, line_data in center_lines.items():
                coords = line_data['coordinates']
                all_coords.extend(coords)
            
            if not all_coords:
                return None
            
            # 计算边界和中心点
            xs = [coord[0] for coord in all_coords]
            ys = [coord[1] for coord in all_coords]
            
            center_x = (min(xs) + max(xs)) / 2
            center_y = (min(ys) + max(ys)) / 2
            
            # 检查是否有Z坐标
            has_z = len(all_coords[0]) > 2
            center_z = 0
            if has_z:
                zs = [coord[2] for coord in all_coords]
                center_z = (min(zs) + max(zs)) / 2
            
            # 转换每条道路为GeoJSON Feature
            for road_id, line_data in center_lines.items():
                coords = line_data['coordinates']
                
                # 归一化坐标
                if has_z:
                    normalized_coords = [(coord[0] - center_x, coord[1] - center_y, coord[2] - center_z) for coord in coords]
                else:
                    normalized_coords = [(coord[0] - center_x, coord[1] - center_y) for coord in coords]
                
                feature = {
                    "type": "Feature",
                    "properties": {
                        "id": road_id,
                        "road_type": "opendrive",
                        "name": f"Road_{road_id}",
                        "length": line_data.get('length', 0)
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": normalized_coords
                    }
                }
                features.append(feature)
            
            # 构建metadata
            metadata = {
                "center": [center_x, center_y] + ([center_z] if has_z else []),
                "bounds": {
                    "min_x": min(xs),
                    "max_x": max(xs),
                    "min_y": min(ys),
                    "max_y": max(ys)
                },
                "feature_count": len(features),
                "has_z_coordinate": has_z
            }
            
            # 如果有Z坐标，添加Z轴边界信息
            if has_z:
                zs = [coord[2] for coord in all_coords]
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
        """导出当前数据为OpenDRIVE格式"""
        try:
            if not self.current_data:
                return False
            
            # 检查是否有格式转换工具
            if not hasattr(self.geometry_converter, 'geojson_to_xodr'):
                # 如果没有现成的转换方法，创建基本的XODR文件
                return self._create_basic_xodr(output_path, version, road_width, lane_count, include_elevation)
            
            # 使用格式转换工具
            geojson_data = self.current_data['data']
            result = self.geometry_converter.geojson_to_xodr(
                geojson_data, 
                output_path,
                crs=crs,
                version=version,
                road_width=road_width,
                lane_count=lane_count,
                include_elevation=include_elevation
            )
            
            return result
            
        except Exception as e:
            print(f"导出XODR文件错误: {e}")
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
                    # 根据几何类型创建几何对象
                    if geometry_type == 'LineString':
                        geom = LineString(coordinates)
                    elif geometry_type == 'Point':
                        geom = Point(coordinates[0] if coordinates else [0, 0])
                    elif geometry_type == 'Polygon':
                        if len(coordinates) > 2:
                            geom = Polygon(coordinates)
                        else:
                            continue
                    else:
                        geom = LineString(coordinates)
                    
                    geometries.append(geom)
                    
                    if include_attributes:
                        attributes.append({
                            'id': properties.get('id', len(attributes)),
                            'name': properties.get('name', f'Feature_{len(attributes)}'),
                            'road_type': properties.get('road_type', 'unknown')
                        })
                    else:
                        attributes.append({'id': len(attributes)})
            
            # 创建GeoDataFrame
            if geometries:
                gdf = gpd.GeoDataFrame(attributes, geometry=geometries, crs=crs)
                
                # 保存为Shapefile
                gdf.to_file(output_path)
                return True
            
            return False
            
        except Exception as e:
            print(f"创建基本Shapefile错误: {e}")
            return False

web3d_server = Web3DServer()

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/load_shp', methods=['POST'])
def load_shp():
    """加载SHP文件API"""
    try:
        data = request.get_json()
        shp_path = data.get('shp_path')
        
        if not shp_path or not os.path.exists(shp_path):
            return jsonify({"error": "SHP文件路径无效"}), 400
            
        # 加载SHP文件
        result = web3d_server.load_shp_file(shp_path)
        if result is None:
            return jsonify({"error": "无法读取SHP文件或文件为空"}), 400
            
        return jsonify({
            "success": True,
            "message": f"成功加载 {result['stats']['roads_count']} 条道路",
            "data": result['data']
        })
        
    except Exception as e:
        return jsonify({"error": f"加载SHP文件时出错: {str(e)}"}), 500

@app.route('/api/upload_shp', methods=['POST'])
def upload_shp():
    """上传SHP文件API"""
    try:
        # 检查是否有文件上传
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
        shp_file_path, upload_dir = web3d_server.save_uploaded_files(files)
        if not shp_file_path:
            return jsonify({"error": f"保存文件失败: {upload_dir}"}), 500
        
        # 加载SHP文件
        result = web3d_server.load_shp_file(shp_file_path)
        if result is None:
            # 清理临时文件
            shutil.rmtree(upload_dir, ignore_errors=True)
            return jsonify({"error": "无法读取上传的SHP文件"}), 400
        
        # 获取文件名
        filename = os.path.basename(shp_file_path)
        
        return jsonify({
            "success": True,
            "message": f"成功上传并加载 {result['stats']['roads_count']} 条道路",
            "data": result['data'],
            "filename": filename,
            "upload_dir": upload_dir
        })
        
    except Exception as e:
        return jsonify({"error": f"上传文件时出错: {str(e)}"}), 500

@app.route('/api/upload_xodr', methods=['POST'])
def upload_xodr():
    """上传OpenDrive文件API"""
    try:
        # 检查是否有文件上传
        if 'files' not in request.files:
            return jsonify({"error": "没有选择文件"}), 400
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({"error": "没有选择有效文件"}), 400
        
        # 查找.xodr文件
        xodr_file = None
        for file in files:
            if file.filename.lower().endswith('.xodr'):
                xodr_file = file
                break
        
        if not xodr_file:
            return jsonify({"error": "请选择.xodr格式的OpenDrive文件"}), 400
        
        # 保存文件到临时目录
        upload_dir = tempfile.mkdtemp()
        filename = secure_filename(xodr_file.filename)
        file_path = os.path.join(upload_dir, filename)
        xodr_file.save(file_path)
        
        # 加载OpenDrive文件
        result = web3d_server.load_xodr_file(file_path)
        if result is None:
            # 清理临时文件
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

@app.route('/api/get_sample_files')
def get_sample_files():
    """获取示例SHP文件列表"""
    try:
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        shp_files = []
        
        if os.path.exists(data_dir):
            for file in os.listdir(data_dir):
                if file.endswith('.shp'):
                    shp_files.append({
                        "name": file,
                        "path": os.path.join(data_dir, file)
                    })
                    
        return jsonify({"files": shp_files})
        
    except Exception as e:
        return jsonify({"error": f"获取文件列表时出错: {str(e)}"}), 500

@app.route('/api/current_data')
def get_current_data():
    """获取当前加载的数据"""
    if web3d_server.current_data:
        return jsonify(web3d_server.current_data)
    else:
        return jsonify({"error": "没有加载的数据"}), 404

@app.route('/api/export_xodr', methods=['POST'])
def export_xodr():
    """导出为OpenDRIVE格式"""
    try:
        if not web3d_server.current_data:
            return jsonify({"error": "没有加载的数据可供导出"}), 400
        
        # 获取导出参数
        data = request.get_json()
        if not data:
            return jsonify({"error": "缺少导出参数"}), 400
        
        file_name = data.get('fileName', 'export.xodr')
        crs = data.get('crs', 'EPSG:4326')
        custom_crs = data.get('customCRS', '')
        xodr_version = data.get('xodrVersion', '1.7')
        road_width = data.get('roadWidth', 3.5)
        lane_count = data.get('laneCount', 2)
        include_elevation = data.get('includeElevation', False)
        
        # 使用自定义CRS如果指定
        if crs == 'custom' and custom_crs:
            crs = custom_crs
        
        # 创建临时文件
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, file_name)
        
        # 调用格式转换工具导出XODR
        result = web3d_server.export_to_xodr(
            output_path, 
            crs=crs,
            version=xodr_version,
            road_width=road_width,
            lane_count=lane_count,
            include_elevation=include_elevation
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
        crs = data.get('crs', 'EPSG:4326')
        custom_crs = data.get('customCRS', '')
        include_attributes = data.get('includeAttributes', True)
        geometry_type = data.get('geometryType', 'LineString')
        
        # 使用自定义CRS如果指定
        if crs == 'custom' and custom_crs:
            crs = custom_crs
        
        # 创建临时文件
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, file_name)
        
        # 调用格式转换工具导出SHP
        result = web3d_server.export_to_shp(
            output_path,
            crs=crs,
            include_attributes=include_attributes,
            geometry_type=geometry_type
        )
        
        if not result:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return jsonify({"error": "导出Shapefile失败"}), 500
        
        # 返回文件
        return send_from_directory(temp_dir, file_name, as_attachment=True)
        
    except Exception as e:
        return jsonify({"error": f"导出Shapefile时出错: {str(e)}"}), 500

# 静态文件服务
@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory('web/js', filename)

@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory('web/css', filename)

if __name__ == '__main__':
    print("启动Web3D可视化服务器...")
    print("访问地址: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)