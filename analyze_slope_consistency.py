#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析xodr文件中道路连接处的斜率一致性
"""

import xml.etree.ElementTree as ET
import math

def analyze_xodr_slope_consistency(xodr_file):
    """分析xodr文件中道路连接处的斜率一致性"""
    
    print(f"\n=== 分析文件: {xodr_file} ===")
    
    # 解析XML文件
    tree = ET.parse(xodr_file)
    root = tree.getroot()
    
    roads = []
    
    # 提取每条道路的信息
    for road in root.findall('road'):
        road_id = road.get('id')
        length = float(road.get('length'))
        
        # 获取planView中的几何信息
        plan_view = road.find('planView')
        if plan_view is not None:
            geometry = plan_view.find('geometry')
            if geometry is not None:
                start_x = float(geometry.get('x'))
                start_y = float(geometry.get('y'))
                hdg = float(geometry.get('hdg'))  # 航向角（弧度）
                
                # 检查是否是ParamPoly3几何
                param_poly3 = geometry.find('paramPoly3')
                if param_poly3 is not None:
                    # ParamPoly3几何，需要计算实际终点
                    aU = float(param_poly3.get('aU'))
                    bU = float(param_poly3.get('bU'))
                    cU = float(param_poly3.get('cU'))
                    dU = float(param_poly3.get('dU'))
                    aV = float(param_poly3.get('aV'))
                    bV = float(param_poly3.get('bV'))
                    cV = float(param_poly3.get('cV'))
                    dV = float(param_poly3.get('dV'))
                    
                    # 在t=1处计算局部坐标
                    u_end = aU + bU + cU + dU
                    v_end = aV + bV + cV + dV
                    
                    # 转换为全局坐标
                    cos_hdg = math.cos(hdg)
                    sin_hdg = math.sin(hdg)
                    end_x = start_x + u_end * cos_hdg - v_end * sin_hdg
                    end_y = start_y + u_end * sin_hdg + v_end * cos_hdg
                    
                    # 计算终点航向角
                    # 对于ParamPoly3，终点航向角需要通过导数计算
                    du_dt = bU + 2*cU + 3*dU  # t=1处的u导数
                    dv_dt = bV + 2*cV + 3*dV  # t=1处的v导数
                    
                    # 局部航向角
                    local_end_hdg = math.atan2(dv_dt, du_dt)
                    # 全局航向角
                    end_hdg = hdg + local_end_hdg
                else:
                    # 直线几何
                    end_x = start_x + length * math.cos(hdg)
                    end_y = start_y + length * math.sin(hdg)
                    end_hdg = hdg  # 直线段起始和终点航向角相同
                
                road_info = {
                    'id': road_id,
                    'length': length,
                    'start_x': start_x,
                    'start_y': start_y,
                    'end_x': end_x,
                    'end_y': end_y,
                    'start_hdg': hdg,
                    'end_hdg': end_hdg,
                    'start_hdg_deg': math.degrees(hdg),
                    'end_hdg_deg': math.degrees(end_hdg)
                }
                
                roads.append(road_info)
    
    # 打印道路信息
    print("\n道路信息:")
    for road in roads:
        print(f"道路 {road['id']}:")
        print(f"  起点: ({road['start_x']:.2f}, {road['start_y']:.2f}), 航向角: {road['start_hdg_deg']:.2f}°")
        print(f"  终点: ({road['end_x']:.2f}, {road['end_y']:.2f}), 航向角: {road['end_hdg_deg']:.2f}°")
        print(f"  长度: {road['length']:.2f}m")
    
    # 分析连接点
    print("\n连接点分析:")
    tolerance = 0.1  # 位置容差
    
    connections = []
    
    for i, road1 in enumerate(roads):
        for j, road2 in enumerate(roads):
            if i >= j:  # 避免重复检查
                continue
                
            # 检查road1的终点是否与road2的起点连接
            if (abs(road1['end_x'] - road2['start_x']) < tolerance and 
                abs(road1['end_y'] - road2['start_y']) < tolerance):
                
                hdg_diff = abs(road1['end_hdg_deg'] - road2['start_hdg_deg'])
                # 处理角度周期性（0°和360°是同一个角度）
                if hdg_diff > 180:
                    hdg_diff = 360 - hdg_diff
                
                connection = {
                    'road1_id': road1['id'],
                    'road2_id': road2['id'],
                    'connection_point': (road1['end_x'], road1['end_y']),
                    'road1_end_hdg': road1['end_hdg_deg'],
                    'road2_start_hdg': road2['start_hdg_deg'],
                    'hdg_difference': hdg_diff,
                    'is_consistent': hdg_diff < 1.0  # 1度容差
                }
                
                connections.append(connection)
                
                print(f"连接点: 道路{road1['id']}终点 -> 道路{road2['id']}起点")
                print(f"  位置: ({road1['end_x']:.2f}, {road1['end_y']:.2f})")
                print(f"  道路{road1['id']}终点航向角: {road1['end_hdg_deg']:.2f}°")
                print(f"  道路{road2['id']}起点航向角: {road2['start_hdg_deg']:.2f}°")
                print(f"  航向角差异: {hdg_diff:.2f}°")
                print(f"  斜率一致性: {'✓ 一致' if connection['is_consistent'] else '✗ 不一致'}")
                print()
            
            # 检查road2的终点是否与road1的起点连接
            if (abs(road2['end_x'] - road1['start_x']) < tolerance and 
                abs(road2['end_y'] - road1['start_y']) < tolerance):
                
                hdg_diff = abs(road2['end_hdg_deg'] - road1['start_hdg_deg'])
                if hdg_diff > 180:
                    hdg_diff = 360 - hdg_diff
                
                connection = {
                    'road1_id': road2['id'],
                    'road2_id': road1['id'],
                    'connection_point': (road2['end_x'], road2['end_y']),
                    'road1_end_hdg': road2['end_hdg_deg'],
                    'road2_start_hdg': road1['start_hdg_deg'],
                    'hdg_difference': hdg_diff,
                    'is_consistent': hdg_diff < 1.0
                }
                
                connections.append(connection)
                
                print(f"连接点: 道路{road2['id']}终点 -> 道路{road1['id']}起点")
                print(f"  位置: ({road2['end_x']:.2f}, {road2['end_y']:.2f})")
                print(f"  道路{road2['id']}终点航向角: {road2['end_hdg_deg']:.2f}°")
                print(f"  道路{road1['id']}起点航向角: {road1['start_hdg_deg']:.2f}°")
                print(f"  航向角差异: {hdg_diff:.2f}°")
                print(f"  斜率一致性: {'✓ 一致' if connection['is_consistent'] else '✗ 不一致'}")
                print()
    
    # 总结
    print("\n=== 斜率一致性总结 ===")
    if not connections:
        print("未发现道路连接点")
    else:
        consistent_count = sum(1 for conn in connections if conn['is_consistent'])
        total_count = len(connections)
        print(f"总连接点数: {total_count}")
        print(f"斜率一致的连接点: {consistent_count}")
        print(f"斜率不一致的连接点: {total_count - consistent_count}")
        print(f"一致性比例: {consistent_count/total_count*100:.1f}%")
        
        if consistent_count == total_count:
            print("✓ 所有连接点的斜率都是一致的！")
        else:
            print("✗ 存在斜率不一致的连接点")
    
    return connections

if __name__ == '__main__':
    # 分析指定的xodr文件
    xodr_files = [
        "output/simple_test.xodr",
        # 可以添加更多文件
    ]
    
    for xodr_file in xodr_files:
        try:
            analyze_xodr_slope_consistency(xodr_file)
        except FileNotFoundError:
            print(f"文件未找到: {xodr_file}")
        except Exception as e:
            print(f"分析文件 {xodr_file} 时出错: {e}")