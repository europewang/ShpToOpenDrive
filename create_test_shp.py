#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建简单的测试shp文件
用于测试道路连接处斜率一致性
"""

import geopandas as gpd
from shapely.geometry import LineString
import pandas as pd
import os

def create_simple_test_shp():
    """创建简单的测试shp文件"""
    
    # 使用投影坐标系，避免坐标转换问题
    crs = 'EPSG:32650'  # UTM Zone 50N
    
    # 创建三条连接的道路，每条道路有左右边界线
    geometries = []
    data = {
        'RoadID': [],
        'Index': [],
        'SNodeID': [],
        'ENodeID': [],
        'Width': [],
        'LaneType': []
    }
    
    # 道路1: 水平线段，增加中间点以支持ParamPoly3拟合
    # 最左侧车道线 (Index=0)
    road1_left = [(0, 1.75), (25, 1.75), (50, 1.75), (75, 1.75), (100, 1.75)]
    geometries.append(LineString(road1_left))
    data['RoadID'].append(1)
    data['Index'].append(0)
    data['SNodeID'].append(1001)
    data['ENodeID'].append(1002)
    data['Width'].append(3.5)
    data['LaneType'].append('driving')
    
    # 参考线 (Index=1)
    road1_ref = [(0, 0), (25, 0), (50, 0), (75, 0), (100, 0)]
    geometries.append(LineString(road1_ref))
    data['RoadID'].append(1)
    data['Index'].append(1)
    data['SNodeID'].append(1001)
    data['ENodeID'].append(1002)
    data['Width'].append(3.5)
    data['LaneType'].append('reference')
    
    # 最右侧车道线 (Index=2)
    road1_right = [(0, -1.75), (25, -1.75), (50, -1.75), (75, -1.75), (100, -1.75)]
    geometries.append(LineString(road1_right))
    data['RoadID'].append(1)
    data['Index'].append(2)
    data['SNodeID'].append(1001)
    data['ENodeID'].append(1002)
    data['Width'].append(3.5)
    data['LaneType'].append('driving')
    
    # 道路2: 曲线段，增加中间点形成S型曲线以支持ParamPoly3拟合
    # 最左侧车道线 (Index=0)
    road2_left = [(100, 1.75), (125, 8.75), (150, 20.75), (175, 35.75), (200, 51.75)]
    geometries.append(LineString(road2_left))
    data['RoadID'].append(2)
    data['Index'].append(0)
    data['SNodeID'].append(1002)
    data['ENodeID'].append(1003)
    data['Width'].append(3.5)
    data['LaneType'].append('driving')
    
    # 参考线 (Index=1)
    road2_ref = [(100, 0), (125, 7), (150, 19), (175, 34), (200, 50)]
    geometries.append(LineString(road2_ref))
    data['RoadID'].append(2)
    data['Index'].append(1)
    data['SNodeID'].append(1002)
    data['ENodeID'].append(1003)
    data['Width'].append(3.5)
    data['LaneType'].append('reference')
    
    # 最右侧车道线 (Index=2)
    road2_right = [(100, -1.75), (125, 5.25), (150, 17.25), (175, 32.25), (200, 48.25)]
    geometries.append(LineString(road2_right))
    data['RoadID'].append(2)
    data['Index'].append(2)
    data['SNodeID'].append(1002)
    data['ENodeID'].append(1003)
    data['Width'].append(3.5)
    data['LaneType'].append('driving')
    
    # 道路3: 水平线段，增加中间点以支持ParamPoly3拟合
    # 最左侧车道线 (Index=0)
    road3_left = [(200, 51.75), (225, 51.75), (250, 51.75), (275, 51.75), (300, 51.75)]
    geometries.append(LineString(road3_left))
    data['RoadID'].append(3)
    data['Index'].append(0)
    data['SNodeID'].append(1003)
    data['ENodeID'].append(1004)
    data['Width'].append(3.5)
    data['LaneType'].append('driving')
    
    # 参考线 (Index=1)
    road3_ref = [(200, 50), (225, 50), (250, 50), (275, 50), (300, 50)]
    geometries.append(LineString(road3_ref))
    data['RoadID'].append(3)
    data['Index'].append(1)
    data['SNodeID'].append(1003)
    data['ENodeID'].append(1004)
    data['Width'].append(3.5)
    data['LaneType'].append('reference')
    
    # 最右侧车道线 (Index=2)
    road3_right = [(200, 48.25), (225, 48.25), (250, 48.25), (275, 48.25), (300, 48.25)]
    geometries.append(LineString(road3_right))
    data['RoadID'].append(3)
    data['Index'].append(2)
    data['SNodeID'].append(1003)
    data['ENodeID'].append(1004)
    data['Width'].append(3.5)
    data['LaneType'].append('driving')
    
    # 创建GeoDataFrame
    gdf = gpd.GeoDataFrame(data, geometry=geometries, crs=crs)
    
    # 确保输出目录存在
    output_dir = 'data/test_simple'
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存为shapefile
    output_path = os.path.join(output_dir, 'SimpleTest.shp')
    gdf.to_file(output_path)
    
    print(f"简单测试shp文件已创建: {output_path}")
    print("道路信息:")
    for i, row in gdf.iterrows():
        print(f"  道路{row['RoadID']}: SNodeID={row['SNodeID']}, ENodeID={row['ENodeID']}")
    
    return output_path

if __name__ == '__main__':
    create_simple_test_shp()