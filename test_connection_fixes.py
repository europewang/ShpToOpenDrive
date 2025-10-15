#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试道路连接修复效果
检查航向角计算和端点位置匹配
"""

import sys
import os
import math
from typing import List, Tuple, Dict

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from geometry_converter import GeometryConverter, RoadConnectionManager
from shp_reader import ShapefileReader

def calculate_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """计算两点间距离"""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def calculate_heading_difference(h1: float, h2: float) -> float:
    """计算两个航向角的差值（考虑周期性）"""
    diff = h1 - h2
    while diff > math.pi:
        diff -= 2 * math.pi
    while diff < -math.pi:
        diff += 2 * math.pi
    return abs(diff)

def test_connection_fixes():
    """测试连接修复效果"""
    print("=== 测试道路连接修复效果 ===")
    
    # 读取测试数据
    shapefile_path = "data/testODsample/LaneTest.shp"
    if not os.path.exists(shapefile_path):
        print(f"测试文件不存在: {shapefile_path}")
        return
    
    reader = ShapefileReader(shapefile_path)
    roads_data = reader.read_shapefile()
    print(f"读取到 {len(roads_data)} 条道路")
    
    # 创建几何转换器
    converter = GeometryConverter()
    
    # 转换为车道面格式
    converted_roads = []
    for road_data in roads_data:
        converted_road = converter.convert_to_lane_surfaces(road_data)
        if converted_road['type'] == 'lane_based':
            converted_roads.append(converted_road)
    
    print(f"转换为车道面格式的道路数: {len(converted_roads)}")
    
    # 创建连接管理器并添加数据
    connection_manager = RoadConnectionManager()
    all_lane_surfaces = []
    
    for road_data in converted_roads:
        lane_surfaces = road_data['lane_surfaces']
        all_lane_surfaces.extend(lane_surfaces)
        converter.add_surfaces_to_connection_manager(lane_surfaces)
    
    # 构建连接关系
    connection_manager.build_connections()
    
    print(f"\n=== 连接管理器状态 ===")
    print(f"道路面总数: {len(connection_manager.road_surfaces)}")
    print(f"节点连接数: {len(connection_manager.node_connections)}")
    print(f"前继映射数: {len(connection_manager.predecessor_map)}")
    print(f"后继映射数: {len(connection_manager.successor_map)}")
    print(f"节点统一航向角数: {len(connection_manager.node_headings)}")
    
    # 检查连接质量
    print(f"\n=== 连接质量分析 ===")
    
    gap_issues = []
    heading_issues = []
    
    for surface_id, surface_info in connection_manager.road_surfaces.items():
        # 检查前继连接
        predecessors = connection_manager.get_predecessors(surface_id)
        if predecessors:
            pred_id = predecessors[0]
            pred_info = connection_manager.road_surfaces.get(pred_id)
            if pred_info:
                # 检查端点位置匹配
                pred_end = pred_info['data']['center_line'][-1]
                curr_start = surface_info['data']['center_line'][0]
                gap_distance = calculate_distance(pred_end, curr_start)
                
                if gap_distance > 1.0:  # 1米阈值
                    gap_issues.append({
                        'predecessor': pred_id,
                        'current': surface_id,
                        'gap_distance': gap_distance,
                        'pred_end': pred_end,
                        'curr_start': curr_start
                    })
                
                # 检查航向角匹配
                pred_end_heading = pred_info.get('end_heading')
                curr_start_heading = surface_info.get('start_heading')
                if pred_end_heading is not None and curr_start_heading is not None:
                    heading_diff = calculate_heading_difference(pred_end_heading, curr_start_heading)
                    if heading_diff > math.radians(10):  # 10度阈值
                        heading_issues.append({
                            'predecessor': pred_id,
                            'current': surface_id,
                            'heading_diff_degrees': math.degrees(heading_diff),
                            'pred_end_heading': math.degrees(pred_end_heading),
                            'curr_start_heading': math.degrees(curr_start_heading)
                        })
    
    print(f"发现 {len(gap_issues)} 个位置间隙问题:")
    for issue in gap_issues[:5]:  # 只显示前5个
        print(f"  {issue['predecessor']} -> {issue['current']}: 间隙 {issue['gap_distance']:.2f}m")
    
    print(f"\n发现 {len(heading_issues)} 个航向角不匹配问题:")
    for issue in heading_issues[:5]:  # 只显示前5个
        print(f"  {issue['predecessor']} -> {issue['current']}: 角度差 {issue['heading_diff_degrees']:.1f}°")
    
    # 检查节点统一航向角效果
    print(f"\n=== 节点统一航向角效果 ===")
    for node_id, unified_heading in connection_manager.node_headings.items():
        connections = connection_manager.node_connections.get(node_id, {})
        incoming = connections.get('incoming', [])
        outgoing = connections.get('outgoing', [])
        
        print(f"节点 {node_id}: 统一航向角 {math.degrees(unified_heading):.1f}°")
        print(f"  进入道路: {len(incoming)} 条, 离开道路: {len(outgoing)} 条")
        
        # 检查实际航向角与统一航向角的差异
        for surface_id in incoming:
            surface_info = connection_manager.road_surfaces.get(surface_id)
            if surface_info and surface_info.get('end_heading') is not None:
                actual_heading = surface_info['end_heading']
                diff = calculate_heading_difference(actual_heading, unified_heading)
                print(f"    进入道路 {surface_id}: 实际 {math.degrees(actual_heading):.1f}°, 差异 {math.degrees(diff):.1f}°")
        
        for surface_id in outgoing:
            surface_info = connection_manager.road_surfaces.get(surface_id)
            if surface_info and surface_info.get('start_heading') is not None:
                actual_heading = surface_info['start_heading']
                diff = calculate_heading_difference(actual_heading, unified_heading)
                print(f"    离开道路 {surface_id}: 实际 {math.degrees(actual_heading):.1f}°, 差异 {math.degrees(diff):.1f}°")
    
    return {
        'gap_issues': len(gap_issues),
        'heading_issues': len(heading_issues),
        'total_surfaces': len(connection_manager.road_surfaces),
        'unified_nodes': len(connection_manager.node_headings)
    }

if __name__ == '__main__':
    results = test_connection_fixes()
    print(f"\n=== 测试结果摘要 ===")
    print(f"总道路面数: {results['total_surfaces']}")
    print(f"统一航向角节点数: {results['unified_nodes']}")
    print(f"位置间隙问题: {results['gap_issues']}")
    print(f"航向角不匹配问题: {results['heading_issues']}")