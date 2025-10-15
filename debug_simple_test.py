#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from shp_reader import ShapefileReader

def analyze_simple_test():
    """分析SimpleTest.shp的数据结构"""
    reader = ShapefileReader('data/test_simple/SimpleTest.shp')
    
    # 加载shapefile
    if not reader.load_shapefile():
        print("加载shapefile失败")
        return
    
    # 提取车道几何信息
    roads = reader.extract_lane_geometries()
    
    print('=== 道路数据结构 ===')
    for road in roads:
        print(f'Road {road["road_id"]}: {len(road["lane_surfaces"])} surfaces')
    
    print('\n=== 车道面详情 ===')
    for road in roads:
        for surface in road['lane_surfaces']:
            left_index = surface['left_boundary'].get('index')
            right_index = surface['right_boundary'].get('index')
            surface_id = surface['surface_id']
            print(f'Surface {surface_id}: left_index={left_index}, right_index={right_index}')
    
    print('\n=== 所有边界线详细信息 ===')
    for road in roads:
        road_id = road['road_id']
        print(f'\nRoad {road_id}:')
        
        # 显示所有车道信息
        for i, lane in enumerate(road['lanes']):
            left_index = lane.get('left_index', 'N/A')
            right_index = lane.get('right_index', 'N/A')
            print(f"  Lane {i}: left_index={left_index}, right_index={right_index}")
            print(f"    Lane keys: {list(lane.keys())}")
        
        # 显示所有车道面的边界线信息
        for surface in road['lane_surfaces']:
            surface_id = surface['surface_id']
            left_boundary = surface['left_boundary']
            right_boundary = surface['right_boundary']
            
            print(f"  Surface {surface_id}:")
            print(f"    左边界: index={left_boundary.get('index')}, 坐标点数={len(left_boundary.get('coordinates', []))}")
            print(f"    右边界: index={right_boundary.get('index')}, 坐标点数={len(right_boundary.get('coordinates', []))}")
            
            # 检查是否有index=0的边界线
            if left_boundary.get('index') == '0' or right_boundary.get('index') == '0':
                print(f"    *** 找到index=0边界线 ***")
    
    print('\n=== 原始shapefile中的所有Index值 ===')
    # 直接查看原始数据
    gdf = reader.gdf
    if gdf is not None:
        for road_id in gdf['RoadID'].unique():
            road_data = gdf[gdf['RoadID'] == road_id]
            indices = sorted(road_data['Index'].unique())
            print(f"Road {road_id}: Index值 = {indices}")

if __name__ == '__main__':
    analyze_simple_test()