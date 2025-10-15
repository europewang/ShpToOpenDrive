#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import numpy as np

def analyze_coordinate_transform_issue():
    """分析坐标系转换问题"""
    
    print("=== ParamPoly3坐标系转换问题分析 ===")
    
    # 模拟道路3的情况
    start_heading = math.radians(15.74)  # 道路3的起点航向角（弧度）
    print(f"道路3起点航向角: {math.degrees(start_heading):.2f}°")
    
    # 在当前代码中的处理方式
    print("\n=== 当前代码的处理方式 ===")
    
    # 1. 起点切线方向设置
    start_tangent_u = 1.0  # 代码中强制设置为(1, 0)
    start_tangent_v = 0.0
    print(f"起点切线方向（局部坐标系）: ({start_tangent_u}, {start_tangent_v})")
    
    # 2. 转换到全局坐标系
    global_tangent_x = start_tangent_u * math.cos(start_heading) - start_tangent_v * math.sin(start_heading)
    global_tangent_y = start_tangent_u * math.sin(start_heading) + start_tangent_v * math.cos(start_heading)
    global_tangent_angle = math.atan2(global_tangent_y, global_tangent_x)
    
    print(f"转换到全局坐标系: ({global_tangent_x:.6f}, {global_tangent_y:.6f})")
    print(f"全局坐标系切线角度: {math.degrees(global_tangent_angle):.2f}°")
    print(f"与起点航向角的差异: {math.degrees(global_tangent_angle - start_heading):.2f}°")
    
    print("\n=== 问题分析 ===")
    print("问题1: 起点切线方向被强制设置为(1, 0)")
    print("       这意味着在局部坐标系中，切线总是沿着u轴方向")
    print("       但这与ParamPoly3的实际计算不符")
    
    print("\n问题2: ParamPoly3的bU和bV系数")
    print("       bU = start_tangent_u * total_length = 1.0 * total_length")
    print("       bV = start_tangent_v * total_length = 0.0 * total_length")
    print("       这导致ParamPoly3在t=0处的导数为(bU, bV) = (total_length, 0)")
    
    print("\n问题3: 局部坐标系的定义")
    print("       局部坐标系的u轴应该沿着起点航向角方向")
    print("       但ParamPoly3的导数计算是在参数坐标系中进行的")
    print("       这两个坐标系可能不一致")
    
    print("\n=== 正确的处理方式 ===")
    print("方案1: 修正起点切线方向计算")
    print("       起点切线方向应该在参数坐标系中表示")
    print("       而不是强制设置为(1, 0)")
    
    print("\n方案2: 修正bU和bV的计算")
    print("       bU和bV应该反映实际的切线方向")
    print("       而不是假设切线总是沿着u轴")
    
    # 验证当前XODR文件中的参数
    print("\n=== 当前XODR文件中的参数验证 ===")
    
    # 从实际XODR文件中读取的道路3的bU和bV值
    bU = 96.24915789807447  # 从XODR文件中读取的bU值
    bV = -27.13115559484204  # 从XODR文件中读取的bV值
    
    print(f"XODR中的bU: {bU}")
    print(f"XODR中的bV: {bV}")
    
    # 计算实际的切线角度
    actual_tangent_angle = math.atan2(bV, bU) if bU != 0 or bV != 0 else 0.0
    print(f"实际切线角度（参数坐标系）: {math.degrees(actual_tangent_angle):.2f}°")
    
    # 转换到全局坐标系
    actual_global_angle = actual_tangent_angle + start_heading
    print(f"实际全局切线角度: {math.degrees(actual_global_angle):.2f}°")
    print(f"与起点航向角的差异: {math.degrees(actual_global_angle - start_heading):.2f}°")

if __name__ == "__main__":
    analyze_coordinate_transform_issue()