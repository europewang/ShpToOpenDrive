#!/usr/bin/env python3
"""
二次多项式约束分析
演示为什么二次多项式无法同时满足所有4个约束条件
"""

import numpy as np
import math

def analyze_quadratic_constraints():
    """分析二次多项式的约束冲突"""
    
    print("=== 二次多项式约束分析 ===\n")
    
    # 示例参数
    start_tangent_u = 1.0  # 起点切线方向（单位向量）
    start_tangent_v = 0.0
    end_u = 100.0          # 终点位置
    end_v = 10.0
    end_tangent_u = 0.8    # 终点切线方向（单位向量）
    end_tangent_v = 0.6
    total_length = 100.0   # 曲线总长度
    
    print(f"给定约束条件：")
    print(f"起点位置: (0, 0)")
    print(f"起点切线: ({start_tangent_u}, {start_tangent_v})")
    print(f"终点位置: ({end_u}, {end_v})")
    print(f"终点切线: ({end_tangent_u}, {end_tangent_v})")
    print(f"曲线长度: {total_length}")
    print()
    
    # 步骤1：强制满足起点约束
    au = av = 0.0  # 起点位置约束
    bu = start_tangent_u * total_length  # 起点切线约束
    bv = start_tangent_v * total_length
    
    print(f"步骤1 - 满足起点约束：")
    print(f"au = {au}, av = {av}")
    print(f"bu = {bu}, bv = {bv}")
    print()
    
    # 步骤2：强制满足终点位置约束
    cu = end_u - bu  # 从 u(1) = bu + cu = end_u 得出
    cv = end_v - bv  # 从 v(1) = bv + cv = end_v 得出
    
    print(f"步骤2 - 满足终点位置约束：")
    print(f"cu = {cu}, cv = {cv}")
    print()
    
    # 步骤3：检查终点切线约束是否满足
    actual_end_tangent_u = bu + 2 * cu  # u'(1) = bu + 2*cu
    actual_end_tangent_v = bv + 2 * cv  # v'(1) = bv + 2*cv
    
    expected_end_tangent_u = end_tangent_u * total_length
    expected_end_tangent_v = end_tangent_v * total_length
    
    print(f"步骤3 - 检查终点切线约束：")
    print(f"期望的终点切线: ({expected_end_tangent_u}, {expected_end_tangent_v})")
    print(f"实际的终点切线: ({actual_end_tangent_u}, {actual_end_tangent_v})")
    
    error_u = abs(actual_end_tangent_u - expected_end_tangent_u)
    error_v = abs(actual_end_tangent_v - expected_end_tangent_v)
    
    print(f"切线误差: ({error_u:.3f}, {error_v:.3f})")
    print()
    
    # 分析自由度
    print("=== 自由度分析 ===")
    print("二次多项式 u(t) = au + bu*t + cu*t² 有3个系数：au, bu, cu")
    print("同样，v(t) = av + bv*t + cv*t² 有3个系数：av, bv, cv")
    print("总共6个自由度")
    print()
    
    print("约束条件：")
    print("1. u(0) = 0  →  au = 0")
    print("2. v(0) = 0  →  av = 0")
    print("3. u'(0) = start_tangent_u  →  bu = start_tangent_u * length")
    print("4. v'(0) = start_tangent_v  →  bv = start_tangent_v * length")
    print("5. u(1) = end_u  →  bu + cu = end_u  →  cu = end_u - bu")
    print("6. v(1) = end_v  →  bv + cv = end_v  →  cv = end_v - bv")
    print("7. u'(1) = end_tangent_u  →  bu + 2*cu = end_tangent_u * length")
    print("8. v'(1) = end_tangent_v  →  bv + 2*cv = end_tangent_v * length")
    print()
    
    print("问题：我们有8个约束条件，但只有6个自由度！")
    print("前6个约束已经完全确定了所有系数，第7、8个约束可能无法满足。")
    print()
    
    # 验证冲突
    print("=== 冲突验证 ===")
    print("从约束5得到：cu = end_u - bu")
    print("从约束7得到：cu = (end_tangent_u * length - bu) / 2")
    print()
    
    cu_from_position = end_u - bu
    cu_from_tangent = (expected_end_tangent_u - bu) / 2
    
    print(f"位置约束要求：cu = {cu_from_position}")
    print(f"切线约束要求：cu = {cu_from_tangent}")
    print(f"两者差异：{abs(cu_from_position - cu_from_tangent):.3f}")
    
    if abs(cu_from_position - cu_from_tangent) > 1e-6:
        print("结论：约束冲突！无法同时满足终点位置和终点切线约束。")
    else:
        print("结论：约束兼容，可以同时满足。")

if __name__ == "__main__":
    analyze_quadratic_constraints()