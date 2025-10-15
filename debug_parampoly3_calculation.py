#!/usr/bin/env python3
"""
分析ParamPoly3参数计算的具体过程
"""

import numpy as np
import math

def analyze_parampoly3_calculation():
    """分析ParamPoly3参数计算过程"""
    
    print("=== ParamPoly3参数计算分析 ===")
    
    # 道路3的实际数据
    start_heading = math.radians(15.74)  # 起点航向角
    end_heading = math.radians(0.0)      # 终点航向角
    total_length = 100.0                 # 道路长度
    
    print(f"起点航向角: {math.degrees(start_heading):.2f}°")
    print(f"终点航向角: {math.degrees(end_heading):.2f}°")
    print(f"道路长度: {total_length}")
    
    # 模拟代码中的计算过程
    print("\n=== 代码中的计算过程 ===")
    
    # 1. 起点切线方向（局部坐标系）
    start_tangent_u = 1.0  # 代码中强制设置为1.0
    start_tangent_v = 0.0  # 代码中强制设置为0.0
    
    print(f"起点切线方向（局部坐标系）: ({start_tangent_u}, {start_tangent_v})")
    
    # 2. 终点切线方向（局部坐标系）
    # 这需要从全局坐标系转换到局部坐标系
    end_tangent_global_u = math.cos(end_heading)
    end_tangent_global_v = math.sin(end_heading)
    
    # 转换到局部坐标系（相对于起点航向角）
    cos_start = math.cos(start_heading)
    sin_start = math.sin(start_heading)
    
    end_tangent_u = end_tangent_global_u * cos_start + end_tangent_global_v * sin_start
    end_tangent_v = -end_tangent_global_u * sin_start + end_tangent_global_v * cos_start
    
    print(f"终点切线方向（全局坐标系）: ({end_tangent_global_u:.6f}, {end_tangent_global_v:.6f})")
    print(f"终点切线方向（局部坐标系）: ({end_tangent_u:.6f}, {end_tangent_v:.6f})")
    
    # 3. 计算bU和bV
    bu = start_tangent_u * total_length
    bv = start_tangent_v * total_length
    
    print(f"\n计算的bU: {bu}")
    print(f"计算的bV: {bv}")
    
    # 4. 实际XODR文件中的值
    actual_bu = 96.24915789807447
    actual_bv = -27.13115559484204
    
    print(f"\n实际XODR中的bU: {actual_bu}")
    print(f"实际XODR中的bV: {actual_bv}")
    
    # 5. 分析差异
    print(f"\nbU差异: {actual_bu - bu}")
    print(f"bV差异: {actual_bv - bv}")
    
    # 6. 分析实际切线角度
    actual_tangent_angle = math.atan2(actual_bv, actual_bu)
    expected_tangent_angle = math.atan2(bv, bu)
    
    print(f"\n实际切线角度: {math.degrees(actual_tangent_angle):.2f}°")
    print(f"期望切线角度: {math.degrees(expected_tangent_angle):.2f}°")
    
    # 7. 分析全局坐标系中的切线角度
    actual_global_angle = actual_tangent_angle + start_heading
    expected_global_angle = expected_tangent_angle + start_heading
    
    print(f"\n实际全局切线角度: {math.degrees(actual_global_angle):.2f}°")
    print(f"期望全局切线角度: {math.degrees(expected_global_angle):.2f}°")
    
    # 8. 问题分析
    print("\n=== 问题分析 ===")
    
    if abs(actual_bu - bu) > 0.1 or abs(actual_bv - bv) > 0.1:
        print("❌ bU和bV的计算与实际值不符！")
        print("可能的原因：")
        print("1. total_length的计算有误")
        print("2. 起点切线方向的设置有误")
        print("3. 坐标系转换有误")
        
        # 反推正确的起点切线方向
        correct_start_tangent_u = actual_bu / total_length
        correct_start_tangent_v = actual_bv / total_length
        
        print(f"\n反推的正确起点切线方向: ({correct_start_tangent_u:.6f}, {correct_start_tangent_v:.6f})")
        
        correct_tangent_angle = math.atan2(correct_start_tangent_v, correct_start_tangent_u)
        print(f"反推的正确切线角度: {math.degrees(correct_tangent_angle):.2f}°")
        
        # 检查这个角度是否合理
        if abs(correct_tangent_angle) < 0.1:  # 接近0度
            print("✅ 反推的切线角度接近0°，符合局部坐标系的预期")
        else:
            print("❌ 反推的切线角度不是0°，说明局部坐标系定义有问题")
    else:
        print("✅ bU和bV的计算正确")

if __name__ == "__main__":
    analyze_parampoly3_calculation()