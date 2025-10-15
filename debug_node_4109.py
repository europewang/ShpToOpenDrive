#!/usr/bin/env python3
"""
调试脚本：检查节点4109的斜率一致性调整问题
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from shp_reader import ShapefileReader
from geometry_converter import GeometryConverter
import math

def _calculate_heading(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """计算两点之间的航向角"""
    return math.atan2(p2[1] - p1[1], p2[0] - p1[0])

def debug_node_4109():
    """调试节点4109的斜率一致性"""
    
    # 读取测试数据
    shapefile_path = 'data/testODsample/LaneTest.shp'
    reader = ShapefileReader(shapefile_path)
    roads_data = reader.read_features()
    
    # 创建几何转换器
    converter = GeometryConverter()
    
    # 提取所有车道面
    lane_surfaces = []
    for road in roads_data:
        if 'lane_surfaces' in road:
            lane_surfaces.extend(road['lane_surfaces'])
    
    # 添加所有道路面到连接管理器
    for surface in lane_surfaces:
        surface_id = surface['surface_id']
        # 从attributes中获取SNodeID和ENodeID
        s_node_id = surface['attributes'].get('SNodeID')
        e_node_id = surface['attributes'].get('ENodeID')
        
        # 计算中心线和航向角
        left_coords = surface['left_boundary']['coordinates']
        right_coords = surface['right_boundary']['coordinates']
        center_line = reader._calculate_center_line(left_coords, right_coords)
        
        # 计算起点和终点航向角
        start_heading = None
        end_heading = None
        if len(center_line) >= 2:
            # 起点航向角（第一个点和第二个点）
            p1 = center_line[0]
            p2 = center_line[1]
            start_heading = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
            
            # 终点航向角（倒数第二个点和最后一个点）
            p1 = center_line[-2]
            p2 = center_line[-1]
            end_heading = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
        
        # 构建surface_data字典
        surface_data = {
            'surface_id': surface_id,
            'attributes': surface['attributes'],
            'left_boundary': surface['left_boundary'],
            'right_boundary': surface['right_boundary']
        }
        
        # 添加到连接管理器
        converter.connection_manager.add_road_surface(
            surface_data=surface_data,
            start_heading=start_heading,
            end_heading=end_heading
        )
    
    # 构建连接关系
    converter.connection_manager.build_connections()
    
    # 计算节点统一斜率
    # 移除手动调用，由build_connections自动执行
    
    # 应用斜率一致性调整
    # Slope consistency adjustment will be applied per surface later for debugging.
    
    # 检查节点4109
    node_id = '4109'
    print(f"=== 节点 {node_id} 的详细信息 ===")
    
    # 获取节点连接信息
    connections = converter.connection_manager.node_connections.get(node_id, {})
    incoming = connections.get('incoming', [])
    outgoing = connections.get('outgoing', [])
    
    print(f"进入节点 {node_id} 的道路面: {incoming}")
    print(f"离开节点 {node_id} 的道路面: {outgoing}")
    
    # 收集所有相关的航向角
    all_headings = []
    
    # 进入节点的道路面的终点航向角
    for surface_id in incoming:
        surface_info = converter.connection_manager.road_surfaces.get(surface_id)
        if surface_info and surface_info.get('end_heading') is not None:
            heading_deg = math.degrees(surface_info['end_heading'])
            all_headings.append(heading_deg)
            print(f"道路面 {surface_id} 终点航向角: {heading_deg:.2f}°")
    
    # 离开节点的道路面的起点航向角
    for surface_id in outgoing:
        surface_info = converter.connection_manager.road_surfaces.get(surface_id)
        if surface_info and surface_info.get('start_heading') is not None:
            heading_deg = math.degrees(surface_info['start_heading'])
            all_headings.append(heading_deg)
            print(f"道路面 {surface_id} 起点航向角: {heading_deg:.2f}°")
    
    # 计算平均航向角
    if all_headings:
        avg_heading = sum(all_headings) / len(all_headings)
        print(f"所有相关航向角的平均值: {avg_heading:.2f}°")
        
        # 检查节点统一斜率
        node_heading = converter.connection_manager.node_headings.get(node_id)
        if node_heading is not None:
            node_heading_deg = math.degrees(node_heading)
            print(f"节点 {node_id} 的统一斜率: {node_heading_deg:.2f}°")
            
            # 检查差异
            diff = abs(avg_heading - node_heading_deg)
            print(f"平均值与统一斜率的差异: {diff:.2f}°")
        else:
            print(f"节点 {node_id} 没有统一斜率数据")
    else:
        print(f"节点 {node_id} 没有相关的航向角数据")
    
    # 特别检查道路面 4043_2_3 和 4117_2_3
    print(f"\n=== 特别检查道路面 4043_2_3 和 4117_2_3 ===")
    
    for surface_id in ['4043_2_3', '4117_2_3']:
        surface_info = converter.connection_manager.road_surfaces.get(surface_id)
        if surface_info:
            s_node = surface_info.get('s_node_id')
            e_node = surface_info.get('e_node_id')
            start_heading = surface_info.get('start_heading')
            end_heading = surface_info.get('end_heading')
            
            print(f"道路面 {surface_id}:")
            print(f"  SNodeID: {s_node}")
            print(f"  ENodeID: {e_node}")
            if start_heading is not None:
                print(f"  起点航向角: {math.degrees(start_heading):.2f}°")
            if end_heading is not None:
                print(f"  终点航向角: {math.degrees(end_heading):.2f}°")

if __name__ == "__main__":
    debug_node_4109()