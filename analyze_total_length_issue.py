#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析total_length计算问题
"""

import numpy as np
import xml.etree.ElementTree as ET

def analyze_road_3_total_length():
    """分析Road 3的total_length计算问题"""
    
    # 从XODR文件中读取Road 3的实际数据
    xodr_file = "E:/Code/ShpToOpenDrive/output/output.xodr"
    
    try:
        tree = ET.parse(xodr_file)
        root = tree.getroot()
        
        # 查找Road 3
        road_3 = None
        for road in root.findall('.//road[@id="3"]'):
            road_3 = road
            break
        
        if road_3 is None:
            print("未找到Road 3")
            return
        
        # 获取Road 3的长度
        road_length = float(road_3.get('length', 0))
        print(f"Road 3 XODR长度: {road_length}")
        
        # 获取ParamPoly3参数
        geometry = road_3.find('.//geometry')
        parampoly3 = road_3.find('.//geometry/paramPoly3')
        if parampoly3 is not None and geometry is not None:
            geometry_length = float(geometry.get('length', 0))
            
            au = float(parampoly3.get('aU', 0))
            bu = float(parampoly3.get('bU', 0))
            cu = float(parampoly3.get('cU', 0))
            du = float(parampoly3.get('dU', 0))
            
            av = float(parampoly3.get('aV', 0))
            bv = float(parampoly3.get('bV', 0))
            cv = float(parampoly3.get('cV', 0))
            dv = float(parampoly3.get('dV', 0))
            
            print(f"Geometry长度: {geometry_length}")
            print(f"ParamPoly3参数:")
            print(f"  aU={au}, bU={bu}, cU={cu}, dU={du}")
            print(f"  aV={av}, bV={bv}, cV={cv}, dV={dv}")
            
            # 计算起始切线角度
            start_tangent_angle = np.arctan2(bv, bu) * 180 / np.pi
            print(f"起始切线角度: {start_tangent_angle:.2f}°")
            
            # 分析问题
            print("\n=== 问题分析 ===")
            print(f"1. 代码计算的total_length应该是: {geometry_length}")
            print(f"2. 代码设置的bU应该是: {geometry_length} (因为start_tangent_u=1.0)")
            print(f"3. 实际XODR的bU是: {bu}")
            print(f"4. 差异: {abs(geometry_length - bu):.3f}")
            
            if abs(geometry_length - bu) > 0.1:
                print("❌ total_length计算存在问题!")
                print("可能原因:")
                print("- 弧长计算方法不准确")
                print("- 坐标系转换导致的长度变化")
                print("- 参数化过程中的数值误差")
            else:
                print("✅ total_length计算正确")
                print("问题可能在于:")
                print("- 起始切线方向设置")
                print("- 边界约束求解算法")
        
        # 模拟代码的弧长计算
        print("\n=== 模拟弧长计算 ===")
        
        # 这里需要Road 3的原始坐标点，我们从调试信息中获取
        # 假设的坐标点（需要从实际数据中获取）
        sample_coords = [
            (0.0, 0.0),
            (25.0, 5.0),
            (50.0, 8.0),
            (75.0, 10.0),
            (100.0, 12.0)
        ]
        
        # 计算弧长
        arc_lengths = np.zeros(len(sample_coords))
        for i in range(1, len(sample_coords)):
            dx = sample_coords[i][0] - sample_coords[i-1][0]
            dy = sample_coords[i][1] - sample_coords[i-1][1]
            arc_lengths[i] = arc_lengths[i-1] + np.sqrt(dx*dx + dy*dy)
        
        calculated_total_length = arc_lengths[-1]
        print(f"模拟计算的total_length: {calculated_total_length:.3f}")
        print(f"与XODR几何长度的差异: {abs(calculated_total_length - geometry_length):.3f}")
        
    except Exception as e:
        print(f"分析过程中出错: {e}")

def analyze_boundary_constraints_logic():
    """分析边界约束求解逻辑"""
    print("\n=== 边界约束求解逻辑分析 ===")
    
    # 模拟_solve_boundary_constraints的计算过程
    print("当前代码逻辑:")
    print("1. start_tangent_u = 1.0, start_tangent_v = 0.0")
    print("2. bU = start_tangent_u * total_length = 1.0 * total_length")
    print("3. bV = start_tangent_v * total_length = 0.0 * total_length = 0.0")
    
    print("\n实际XODR数据显示:")
    print("1. bU ≠ total_length")
    print("2. bV ≠ 0.0")
    
    print("\n可能的问题:")
    print("1. 起始切线方向在局部坐标系中不是(1.0, 0.0)")
    print("2. total_length计算不准确")
    print("3. 边界约束求解算法有误")
    print("4. 坐标系转换存在问题")

if __name__ == "__main__":
    print("分析Road 3的total_length计算问题")
    print("=" * 50)
    
    analyze_road_3_total_length()
    analyze_boundary_constraints_logic()
    
    print("\n建议的修复方向:")
    print("1. 检查弧长计算的准确性")
    print("2. 验证局部坐标系转换")
    print("3. 重新审视边界约束求解算法")
    print("4. 确保起始切线方向计算正确")