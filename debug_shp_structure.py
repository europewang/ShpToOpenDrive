#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import geopandas as gpd

def analyze_shp_structure():
    """分析SimpleTest.shp的原始数据结构，包括SNodeID、ENodeID、RoadID、Index"""
    
    shp_path = 'data/test_simple/SimpleTest.shp'
    
    # 直接读取shapefile
    gdf = gpd.read_file(shp_path)
    
    print('=== Shapefile列信息 ===')
    print(f'列名: {list(gdf.columns)}')
    print(f'数据行数: {len(gdf)}')
    
    print('\n=== 所有记录的详细信息 ===')
    for idx, row in gdf.iterrows():
        print(f'\n记录 {idx}:')
        for col in gdf.columns:
            if col != 'geometry':
                print(f'  {col}: {row[col]}')
        
        # 显示几何信息
        geom = row.geometry
        if hasattr(geom, 'coords'):
            coords = list(geom.coords)
            print(f'  geometry: {geom.geom_type}, 坐标点数: {len(coords)}')
            print(f'  起点: {coords[0]}, 终点: {coords[-1]}')
    
    print('\n=== 按RoadID分组分析 ===')
    if 'RoadID' in gdf.columns:
        grouped = gdf.groupby('RoadID')
        for road_id, group in grouped:
            print(f'\nRoadID {road_id}:')
            print(f'  包含 {len(group)} 条记录')
            
            # 显示该RoadID下的所有Index、SNodeID、ENodeID
            for idx, row in group.iterrows():
                index_val = row.get('Index', 'N/A')
                snode_val = row.get('SNodeID', 'N/A')
                enode_val = row.get('ENodeID', 'N/A')
                print(f'    记录{idx}: Index={index_val}, SNodeID={snode_val}, ENodeID={enode_val}')
    
    print('\n=== 节点连接关系分析 ===')
    if 'SNodeID' in gdf.columns and 'ENodeID' in gdf.columns:
        # 收集所有节点
        all_nodes = set()
        for idx, row in gdf.iterrows():
            snode = row.get('SNodeID')
            enode = row.get('ENodeID')
            if snode is not None:
                all_nodes.add(snode)
            if enode is not None:
                all_nodes.add(enode)
        
        print(f'所有节点: {sorted(all_nodes)}')
        
        # 分析每个节点的连接关系
        for node in sorted(all_nodes):
            connected_roads = []
            for idx, row in gdf.iterrows():
                road_id = row.get('RoadID')
                index_val = row.get('Index')
                if row.get('SNodeID') == node or row.get('ENodeID') == node:
                    role = 'start' if row.get('SNodeID') == node else 'end'
                    connected_roads.append(f'RoadID={road_id}, Index={index_val}, role={role}')
            
            print(f'节点 {node} 连接的道路线: {connected_roads}')

if __name__ == '__main__':
    analyze_shp_structure()