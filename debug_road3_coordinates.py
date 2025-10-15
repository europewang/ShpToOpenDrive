#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from shp_reader import ShapefileReader
import math

def debug_road3_coordinates():
    """调试道路3的坐标数据和航向角计算"""
    
    # 读取shapefile
    reader = ShapefileReader('data/testODsample/LaneTest.shp')
    reader.load_shapefile()
    reader.convert_to_utm()
    roads = reader.extract_road_geometries()
    
    print("=== 道路数据结构分析 ===")
    print(f"读取到 {len(roads)} 条道路")
    
    if roads:
        print(f"第一条道路的键: {list(roads[0].keys())}")
        # 检查是否为lane格式
        first_road = roads[0]
        is_lane_format = all(key in first_road for key in ['road_id', 'lanes', 'lane_surfaces'])
        print(f"是否为Lane格式: {is_lane_format}")
        
        # 显示所有道路的ID
        print("所有道路ID:")
        for i, road in enumerate(roads):
            road_id = road.get('id', road.get('road_id', 'N/A'))
            print(f"  道路 {i}: ID={road_id}")
    
    # 找到第三条道路（道路4117）
    road3 = None
    if len(roads) >= 3:
        road3 = roads[2]  # 第三条道路（索引2）
    
    if not road3:
        print("未找到第三条道路")
        return
    
    road3_id = road3.get('id', road3.get('road_id', 'N/A'))
    print(f"\n=== 道路{road3_id}坐标数据分析 ===")
    
    print(f"道路{road3_id}包含 {len(road3['lanes'])} 个车道")
    
    # 分析每个车道的边界线
    for lane_idx, lane in enumerate(road3['lanes']):
        print(f"\n车道 {lane_idx}:")
        
        # 分析左边界
        if 'left_boundary' in lane and lane['left_boundary']:
            coords = lane['left_boundary']
            print(f"  左边界坐标点数: {len(coords)}")
            print(f"  起点: ({coords[0][0]:.2f}, {coords[0][1]:.2f})")
            print(f"  终点: ({coords[-1][0]:.2f}, {coords[-1][1]:.2f})")
            
            # 计算起点航向角
            if len(coords) >= 2:
                dx = coords[1][0] - coords[0][0]
                dy = coords[1][1] - coords[0][1]
                start_heading = math.atan2(dy, dx)
                print(f"  起点航向角: {math.degrees(start_heading):.2f}°")
            
            # 计算终点航向角
            if len(coords) >= 2:
                dx = coords[-1][0] - coords[-2][0]
                dy = coords[-1][1] - coords[-2][1]
                end_heading = math.atan2(dy, dx)
                print(f"  终点航向角: {math.degrees(end_heading):.2f}°")
        
        # 分析右边界
        if 'right_boundary' in lane and lane['right_boundary']:
            coords = lane['right_boundary']
            print(f"  右边界坐标点数: {len(coords)}")
            print(f"  起点: ({coords[0][0]:.2f}, {coords[0][1]:.2f})")
            print(f"  终点: ({coords[-1][0]:.2f}, {coords[-1][1]:.2f})")
            
            # 计算起点航向角
            if len(coords) >= 2:
                dx = coords[1][0] - coords[0][0]
                dy = coords[1][1] - coords[0][1]
                start_heading = math.atan2(dy, dx)
                print(f"  起点航向角: {math.degrees(start_heading):.2f}°")
            
            # 计算终点航向角
            if len(coords) >= 2:
                dx = coords[-1][0] - coords[-2][0]
                dy = coords[-1][1] - coords[-2][1]
                end_heading = math.atan2(dy, dx)
                print(f"  终点航向角: {math.degrees(end_heading):.2f}°")
        
        # 分析中心线
        if 'center_line' in lane and lane['center_line']:
            coords = lane['center_line']
            print(f"  中心线坐标点数: {len(coords)}")
            print(f"  起点: ({coords[0][0]:.2f}, {coords[0][1]:.2f})")
            print(f"  终点: ({coords[-1][0]:.2f}, {coords[-1][1]:.2f})")
            
            # 计算起点航向角
            if len(coords) >= 2:
                dx = coords[1][0] - coords[0][0]
                dy = coords[1][1] - coords[0][1]
                start_heading = math.atan2(dy, dx)
                print(f"  起点航向角: {math.degrees(start_heading):.2f}°")
            
            # 计算终点航向角
            if len(coords) >= 2:
                dx = coords[-1][0] - coords[-2][0]
                dy = coords[-1][1] - coords[-2][1]
                end_heading = math.atan2(dy, dx)
                print(f"  终点航向角: {math.degrees(end_heading):.2f}°")
            
            # 打印所有坐标点
            print(f"  所有坐标点:")
            for i, (x, y) in enumerate(coords):
                print(f"    点{i}: ({x:.6f}, {y:.6f})")

if __name__ == "__main__":
    debug_road3_coordinates()