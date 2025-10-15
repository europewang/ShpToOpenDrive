#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试connection_manager中的surface信息
"""

import sys
sys.path.append('src')

from shp_reader import ShapefileReader
from opendrive_generator import OpenDriveGenerator
from geometry_converter import RoadConnectionManager

def debug_connection_manager():
    # 读取shapefile
    reader = ShapefileReader('data/test_simple/SimpleTest.shp')
    reader.load_shapefile()
    roads_data = reader.extract_lane_geometries()
    
    # 转换为lane_geometries格式
    lane_geometries = {}
    for i, road_data in enumerate(roads_data):
        road_id = f"Road {i+1}"
        lane_geometries[road_id] = {
            'lanes': {
                'Lane 0': {
                    'surfaces': road_data.get('lane_surfaces', [])
                }
            }
        }
    
    print("=== 原始车道几何数据 ===")
    for road_id, road_data in lane_geometries.items():
        print(f"\n道路 {road_id}:")
        for lane_id, lane_data in road_data['lanes'].items():
            print(f"  车道 {lane_id}:")
            for surface in lane_data['surfaces']:
                surface_id = surface.get('surface_id')
                print(f"    Surface ID: {surface_id}")
    
    # 创建connection_manager
    connection_manager = RoadConnectionManager()
    
    # 添加surfaces到connection_manager
    generator = OpenDriveGenerator()
    generator._add_surfaces_to_connection_manager(lane_geometries, connection_manager)
    
    print("\n=== Connection Manager中的Surface信息 ===")
    print(f"存储的surface数量: {len(connection_manager.surfaces)}")
    for surface_id, surface_data in connection_manager.surfaces.items():
        print(f"Surface ID: {surface_id}")
        print(f"  起始航向角: {surface_data.get('start_heading', 'N/A')}°")
        print(f"  终点航向角: {surface_data.get('end_heading', 'N/A')}°")
    
    print("\n=== Node Headings ===")
    for node_id, heading in connection_manager.node_headings.items():
        print(f"Node {node_id}: {heading:.2f}°")
    
    # 测试道路参考线计算
    print("\n=== 道路参考线计算测试 ===")
    for road_id, road_data in lane_geometries.items():
        print(f"\n处理道路 {road_id}:")
        lane_surfaces = []
        for lane_id, lane_data in road_data['lanes'].items():
            lane_surfaces.extend(lane_data['surfaces'])
        
        # 模拟_calculate_road_reference_line的逻辑
        reference_coords = []
        reference_surface_id = None
        
        # 查找index=0的边界线
        for surface in lane_surfaces:
            if ('left_boundary' in surface and 
                surface['left_boundary'].get('index') == '0'):
                reference_surface_id = surface.get('surface_id')
                print(f"  找到index=0的左边界线，Surface ID: {reference_surface_id}")
                break
            elif ('right_boundary' in surface and 
                  surface['right_boundary'].get('index') == '0'):
                reference_surface_id = surface.get('surface_id')
                print(f"  找到index=0的右边界线，Surface ID: {reference_surface_id}")
                break
        
        if not reference_surface_id:
            # 回退方案
            reference_surface = lane_surfaces[0]
            reference_surface_id = reference_surface.get('surface_id')
            print(f"  回退到第一个车道面，Surface ID: {reference_surface_id}")
        
        # 检查这个surface_id是否在connection_manager中
        if reference_surface_id in connection_manager.surfaces:
            surface_data = connection_manager.surfaces[reference_surface_id]
            print(f"  在Connection Manager中找到匹配的Surface:")
            print(f"    起始航向角: {surface_data.get('start_heading', 'N/A')}°")
            print(f"    终点航向角: {surface_data.get('end_heading', 'N/A')}°")
        else:
            print(f"  警告：Surface ID {reference_surface_id} 在Connection Manager中未找到！")
            print(f"  Connection Manager中的Surface IDs: {list(connection_manager.surfaces.keys())}")

if __name__ == '__main__':
    debug_connection_manager()