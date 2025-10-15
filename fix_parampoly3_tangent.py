#!/usr/bin/env python3
"""
修复ParamPoly3切线方向问题
"""

import numpy as np
import math
import matplotlib.pyplot as plt
from matplotlib.patches import Arrow

def fix_parampoly3_tangent():
    """分析并修复ParamPoly3切线方向问题"""
    
    print("=== ParamPoly3切线方向修复方案 ===")
    
    # 道路3的实际数据
    start_heading = math.radians(15.74)  # 起点航向角
    end_heading = math.radians(0.0)      # 终点航向角
    total_length = 100.0                 # 道路长度
    
    print(f"起点航向角: {math.degrees(start_heading):.2f}°")
    print(f"终点航向角: {math.degrees(end_heading):.2f}°")
    print(f"道路长度: {total_length}")
    
    # 当前代码的计算方式
    print("\n=== 当前代码的计算方式 ===")
    
    # 起点切线方向（局部坐标系）
    start_tangent_u = 1.0
    start_tangent_v = 0.0
    
    # 计算bU和bV
    bu_current = start_tangent_u * total_length
    bv_current = start_tangent_v * total_length
    
    print(f"起点切线方向（局部坐标系）: ({start_tangent_u}, {start_tangent_v})")
    print(f"计算的bU: {bu_current}")
    print(f"计算的bV: {bv_current}")
    
    # 实际XODR文件中的值
    actual_bu = 96.24915789807447
    actual_bv = -27.13115559484204
    
    print(f"\n实际XODR中的bU: {actual_bu}")
    print(f"实际XODR中的bV: {actual_bv}")
    
    # 分析差异
    print(f"\nbU差异: {actual_bu - bu_current}")
    print(f"bV差异: {actual_bv - bv_current}")
    
    # 修复方案1：调整total_length
    print("\n=== 修复方案1：调整total_length ===")
    
    # 假设起点切线方向是正确的，但total_length有误
    adjusted_total_length = math.sqrt(actual_bu**2 + actual_bv**2)
    
    print(f"调整后的total_length: {adjusted_total_length}")
    
    # 检查这个调整是否合理
    if abs(adjusted_total_length - total_length) < 5.0:
        print("✅ 调整后的total_length与原始值接近，这可能是一个合理的修复")
    else:
        print("❌ 调整后的total_length与原始值相差较大，这可能不是问题的根本原因")
    
    # 修复方案2：调整起点切线方向
    print("\n=== 修复方案2：调整起点切线方向 ===")
    
    # 假设total_length是正确的，但起点切线方向有误
    adjusted_start_tangent_u = actual_bu / total_length
    adjusted_start_tangent_v = actual_bv / total_length
    
    print(f"调整后的起点切线方向: ({adjusted_start_tangent_u:.6f}, {adjusted_start_tangent_v:.6f})")
    
    # 计算调整后的切线角度
    adjusted_tangent_angle = math.atan2(adjusted_start_tangent_v, adjusted_start_tangent_u)
    print(f"调整后的切线角度: {math.degrees(adjusted_tangent_angle):.2f}°")
    
    # 检查这个角度是否与heading_diff一致
    heading_diff = end_heading - start_heading
    # 标准化角度差
    while heading_diff > math.pi:
        heading_diff -= 2 * math.pi
    while heading_diff < -math.pi:
        heading_diff += 2 * math.pi
    
    print(f"航向角差异: {math.degrees(heading_diff):.2f}°")
    
    if abs(math.degrees(adjusted_tangent_angle) - math.degrees(heading_diff)) < 1.0:
        print("✅ 调整后的切线角度与航向角差异一致，这可能是问题的根本原因")
    else:
        print("❌ 调整后的切线角度与航向角差异不一致")
    
    # 修复方案3：正确处理坐标系转换
    print("\n=== 修复方案3：正确处理坐标系转换 ===")
    
    # 在计算bU和bV时，需要考虑局部坐标系与参数坐标系的关系
    # 参数坐标系：t从0到1，导数为(bU, bV)
    # 局部坐标系：u轴沿start_heading方向，v轴垂直于start_heading方向
    
    print("在_solve_boundary_constraints方法中，应该：")
    print("1. 保持起点切线方向为(1.0, 0.0)，这是正确的")
    print("2. 确保total_length的计算正确")
    print("3. 检查多项式拟合过程中是否有其他因素影响了bU和bV的计算")
    
    # 可视化分析
    print("\n=== 可视化分析 ===")
    
    # 创建图形
    plt.figure(figsize=(10, 8))
    
    # 绘制局部坐标系
    plt.arrow(0, 0, 5, 0, head_width=0.5, head_length=1, fc='blue', ec='blue', label='u轴')
    plt.arrow(0, 0, 0, 5, head_width=0.5, head_length=1, fc='green', ec='green', label='v轴')
    
    # 绘制起点切线方向（当前代码）
    plt.arrow(0, 0, start_tangent_u*5, start_tangent_v*5, head_width=0.5, head_length=1, fc='red', ec='red', label='当前起点切线')
    
    # 绘制起点切线方向（实际XODR）
    plt.arrow(0, 0, adjusted_start_tangent_u*5, adjusted_start_tangent_v*5, head_width=0.5, head_length=1, fc='purple', ec='purple', label='实际起点切线')
    
    # 绘制终点切线方向
    end_tangent_u = math.cos(heading_diff)
    end_tangent_v = math.sin(heading_diff)
    plt.arrow(10, 0, end_tangent_u*5, end_tangent_v*5, head_width=0.5, head_length=1, fc='orange', ec='orange', label='终点切线')
    
    # 设置图形属性
    plt.grid(True)
    plt.axhline(y=0, color='k', linestyle='-', alpha=0.3)
    plt.axvline(x=0, color='k', linestyle='-', alpha=0.3)
    plt.legend()
    plt.title('ParamPoly3切线方向分析')
    plt.xlabel('u轴')
    plt.ylabel('v轴')
    plt.axis('equal')
    plt.xlim(-6, 15)
    plt.ylim(-6, 6)
    
    # 保存图形
    plt.savefig('parampoly3_tangent_analysis.png')
    print("已保存可视化分析图到parampoly3_tangent_analysis.png")
    
    # 提出修复建议
    print("\n=== 修复建议 ===")
    print("根据分析，最可能的问题是：")
    print("1. 在_solve_boundary_constraints方法中，起点切线方向的设置是正确的(1.0, 0.0)")
    print("2. 但在计算bU和bV时，没有正确考虑局部坐标系与参数坐标系的关系")
    print("3. 或者在多项式拟合过程中，有其他因素影响了bU和bV的计算")
    
    print("\n建议修改geometry_converter.py中的_solve_boundary_constraints方法：")
    print("1. 检查total_length的计算是否正确")
    print("2. 检查多项式拟合过程中是否有其他因素影响了bU和bV的计算")
    print("3. 确保局部坐标系与参数坐标系的一致性")

if __name__ == "__main__":
    fix_parampoly3_tangent()