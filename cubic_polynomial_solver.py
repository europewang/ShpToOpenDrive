#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三次多项式边界条件求解详细示例
演示如何严格满足所有8个边界条件
"""

import numpy as np
import math
import matplotlib.pyplot as plt

def solve_cubic_polynomial_constraints():
    """
    详细演示三次多项式如何严格满足所有边界条件
    
    三次多项式形式：
    u(t) = au + bu*t + cu*t² + du*t³
    v(t) = av + bv*t + cv*t² + dv*t³
    
    导数形式：
    u'(t) = bu + 2*cu*t + 3*du*t²
    v'(t) = bv + 2*cv*t + 3*dv*t²
    """
    
    print("=== 三次多项式边界条件求解详细过程 ===\n")
    
    # 设定边界条件（示例数据）
    print("1. 设定边界条件：")
    
    # 起点位置（局部坐标系原点）
    start_u, start_v = 0.0, 0.0
    print(f"   起点位置: u(0) = {start_u}, v(0) = {start_v}")
    
    # 终点位置
    end_u, end_v = 100.0, 20.0
    print(f"   终点位置: u(1) = {end_u}, v(1) = {end_v}")
    
    # 起点切线方向（局部坐标系中，起点沿u轴方向）
    start_tangent_u, start_tangent_v = 1.0, 0.0
    total_length = 105.0  # 曲线总长度
    print(f"   起点切线方向: ({start_tangent_u}, {start_tangent_v})")
    print(f"   曲线总长度: {total_length}")
    
    # 终点切线方向（假设终点航向角相对起点有15度偏转）
    heading_diff = math.radians(15)  # 15度转弧度
    end_tangent_u = math.cos(heading_diff)
    end_tangent_v = math.sin(heading_diff)
    print(f"   终点切线方向: ({end_tangent_u:.6f}, {end_tangent_v:.6f})")
    print(f"   终点航向角偏差: {math.degrees(heading_diff)}°\n")
    
    # 第一步：直接确定前4个系数
    print("2. 第一步：根据起点约束直接确定前4个系数")
    print("   约束条件：")
    print("   - u(0) = au = 0  =>  au = 0")
    print("   - v(0) = av = 0  =>  av = 0")
    print("   - u'(0) = bu = start_tangent_u * total_length")
    print("   - v'(0) = bv = start_tangent_v * total_length")
    
    au = 0.0
    av = 0.0
    bu = start_tangent_u * total_length
    bv = start_tangent_v * total_length
    
    print(f"   结果：")
    print(f"   au = {au}")
    print(f"   av = {av}")
    print(f"   bu = {bu}")
    print(f"   bv = {bv}\n")
    
    # 第二步：求解剩余4个系数
    print("3. 第二步：根据终点约束求解剩余4个系数")
    print("   剩余约束条件：")
    print("   - u(1) = bu + cu + du = end_u")
    print("   - u'(1) = bu + 2*cu + 3*du = end_tangent_u * total_length")
    print("   - v(1) = bv + cv + dv = end_v")
    print("   - v'(1) = bv + 2*cv + 3*dv = end_tangent_v * total_length")
    
    # 构建u方向的线性方程组
    print("\n   3.1 求解u方向系数 (cu, du)：")
    print("   线性方程组：")
    print("   [1  1] [cu]   [end_u - bu]")
    print("   [2  3] [du] = [end_tangent_u * total_length - bu]")
    
    A_u = np.array([[1, 1], [2, 3]])
    b_u = np.array([end_u - bu, end_tangent_u * total_length - bu])
    
    print(f"   A_u = {A_u}")
    print(f"   b_u = [{end_u - bu:.6f}, {end_tangent_u * total_length - bu:.6f}]")
    
    cu, du = np.linalg.solve(A_u, b_u)
    print(f"   解得：cu = {cu:.6f}, du = {du:.6f}")
    
    # 构建v方向的线性方程组
    print("\n   3.2 求解v方向系数 (cv, dv)：")
    print("   线性方程组：")
    print("   [1  1] [cv]   [end_v - bv]")
    print("   [2  3] [dv] = [end_tangent_v * total_length - bv]")
    
    A_v = np.array([[1, 1], [2, 3]])
    b_v = np.array([end_v - bv, end_tangent_v * total_length - bv])
    
    print(f"   A_v = {A_v}")
    print(f"   b_v = [{end_v - bv:.6f}, {end_tangent_v * total_length - bv:.6f}]")
    
    cv, dv = np.linalg.solve(A_v, b_v)
    print(f"   解得：cv = {cv:.6f}, dv = {dv:.6f}")
    
    # 验证所有约束条件
    print("\n4. 验证所有约束条件是否严格满足：")
    
    # 定义多项式函数
    def u_poly(t):
        return au + bu*t + cu*t**2 + du*t**3
    
    def v_poly(t):
        return av + bv*t + cv*t**2 + dv*t**3
    
    def u_derivative(t):
        return bu + 2*cu*t + 3*du*t**2
    
    def v_derivative(t):
        return bv + 2*cv*t + 3*dv*t**2
    
    # 验证起点约束
    print("   起点约束验证：")
    u_0 = u_poly(0)
    v_0 = v_poly(0)
    u_prime_0 = u_derivative(0)
    v_prime_0 = v_derivative(0)
    
    print(f"   u(0) = {u_0:.6f} (期望: {start_u}) ✓" if abs(u_0 - start_u) < 1e-10 else f"   u(0) = {u_0:.6f} (期望: {start_u}) ✗")
    print(f"   v(0) = {v_0:.6f} (期望: {start_v}) ✓" if abs(v_0 - start_v) < 1e-10 else f"   v(0) = {v_0:.6f} (期望: {start_v}) ✗")
    print(f"   u'(0) = {u_prime_0:.6f} (期望: {start_tangent_u * total_length:.6f}) ✓" if abs(u_prime_0 - start_tangent_u * total_length) < 1e-10 else f"   u'(0) = {u_prime_0:.6f} (期望: {start_tangent_u * total_length:.6f}) ✗")
    print(f"   v'(0) = {v_prime_0:.6f} (期望: {start_tangent_v * total_length:.6f}) ✓" if abs(v_prime_0 - start_tangent_v * total_length) < 1e-10 else f"   v'(0) = {v_prime_0:.6f} (期望: {start_tangent_v * total_length:.6f}) ✗")
    
    # 验证终点约束
    print("\n   终点约束验证：")
    u_1 = u_poly(1)
    v_1 = v_poly(1)
    u_prime_1 = u_derivative(1)
    v_prime_1 = v_derivative(1)
    
    print(f"   u(1) = {u_1:.6f} (期望: {end_u}) ✓" if abs(u_1 - end_u) < 1e-10 else f"   u(1) = {u_1:.6f} (期望: {end_u}) ✗")
    print(f"   v(1) = {v_1:.6f} (期望: {end_v}) ✓" if abs(v_1 - end_v) < 1e-10 else f"   v(1) = {v_1:.6f} (期望: {end_v}) ✗")
    print(f"   u'(1) = {u_prime_1:.6f} (期望: {end_tangent_u * total_length:.6f}) ✓" if abs(u_prime_1 - end_tangent_u * total_length) < 1e-10 else f"   u'(1) = {u_prime_1:.6f} (期望: {end_tangent_u * total_length:.6f}) ✗")
    print(f"   v'(1) = {v_prime_1:.6f} (期望: {end_tangent_v * total_length:.6f}) ✓" if abs(v_prime_1 - end_tangent_v * total_length) < 1e-10 else f"   v'(1) = {v_prime_1:.6f} (期望: {end_tangent_v * total_length:.6f}) ✗")
    
    # 总结
    print("\n5. 最终多项式系数：")
    print(f"   u(t) = {au:.6f} + {bu:.6f}*t + {cu:.6f}*t² + {du:.6f}*t³")
    print(f"   v(t) = {av:.6f} + {bv:.6f}*t + {cv:.6f}*t² + {dv:.6f}*t³")
    
    # 绘制曲线
    print("\n6. 绘制曲线图...")
    t_values = np.linspace(0, 1, 100)
    u_values = [u_poly(t) for t in t_values]
    v_values = [v_poly(t) for t in t_values]
    
    plt.figure(figsize=(12, 8))
    
    # 子图1：曲线形状
    plt.subplot(2, 2, 1)
    plt.plot(u_values, v_values, 'b-', linewidth=2, label='三次多项式曲线')
    plt.plot([start_u, end_u], [start_v, end_v], 'ro', markersize=8, label='起点/终点')
    
    # 绘制切线方向
    scale = 20
    plt.arrow(start_u, start_v, start_tangent_u * scale, start_tangent_v * scale, 
              head_width=2, head_length=3, fc='green', ec='green', label='起点切线')
    plt.arrow(end_u, end_v, end_tangent_u * scale, end_tangent_v * scale, 
              head_width=2, head_length=3, fc='red', ec='red', label='终点切线')
    
    plt.xlabel('u')
    plt.ylabel('v')
    plt.title('三次多项式曲线')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.axis('equal')
    
    # 子图2：u(t)函数
    plt.subplot(2, 2, 2)
    plt.plot(t_values, u_values, 'b-', linewidth=2)
    plt.plot([0, 1], [start_u, end_u], 'ro', markersize=8)
    plt.xlabel('t')
    plt.ylabel('u(t)')
    plt.title('u方向多项式')
    plt.grid(True, alpha=0.3)
    
    # 子图3：v(t)函数
    plt.subplot(2, 2, 3)
    plt.plot(t_values, v_values, 'g-', linewidth=2)
    plt.plot([0, 1], [start_v, end_v], 'ro', markersize=8)
    plt.xlabel('t')
    plt.ylabel('v(t)')
    plt.title('v方向多项式')
    plt.grid(True, alpha=0.3)
    
    # 子图4：导数函数
    plt.subplot(2, 2, 4)
    u_prime_values = [u_derivative(t) for t in t_values]
    v_prime_values = [v_derivative(t) for t in t_values]
    plt.plot(t_values, u_prime_values, 'b-', linewidth=2, label="u'(t)")
    plt.plot(t_values, v_prime_values, 'g-', linewidth=2, label="v'(t)")
    plt.plot([0, 1], [u_prime_0, u_prime_1], 'bo', markersize=8)
    plt.plot([0, 1], [v_prime_0, v_prime_1], 'go', markersize=8)
    plt.xlabel('t')
    plt.ylabel("导数值")
    plt.title('导数函数')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('cubic_polynomial_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    return {
        'coefficients': {
            'au': au, 'bu': bu, 'cu': cu, 'du': du,
            'av': av, 'bv': bv, 'cv': cv, 'dv': dv
        },
        'verification': {
            'start_position': (u_0, v_0),
            'end_position': (u_1, v_1),
            'start_tangent': (u_prime_0, v_prime_0),
            'end_tangent': (u_prime_1, v_prime_1)
        }
    }

def demonstrate_matrix_solution():
    """
    演示矩阵求解的数学原理
    """
    print("\n=== 矩阵求解的数学原理 ===\n")
    
    print("对于三次多项式 u(t) = au + bu*t + cu*t² + du*t³")
    print("我们有以下约束：")
    print("1. u(0) = au = 0")
    print("2. u'(0) = bu = start_tangent_u * total_length")
    print("3. u(1) = au + bu + cu + du = end_u")
    print("4. u'(1) = bu + 2*cu + 3*du = end_tangent_u * total_length")
    print()
    
    print("由约束1和2，我们得到：au = 0, bu = start_tangent_u * total_length")
    print("将这些代入约束3和4：")
    print("3. bu + cu + du = end_u  =>  cu + du = end_u - bu")
    print("4. bu + 2*cu + 3*du = end_tangent_u * total_length  =>  2*cu + 3*du = end_tangent_u * total_length - bu")
    print()
    
    print("这形成了一个2×2线性方程组：")
    print("┌       ┐ ┌    ┐   ┌                                    ┐")
    print("│ 1   1 │ │ cu │   │ end_u - bu                         │")
    print("│ 2   3 │ │ du │ = │ end_tangent_u * total_length - bu  │")
    print("└       ┘ └    ┘   └                                    ┘")
    print()
    
    print("矩阵A的行列式 = 1*3 - 1*2 = 1 ≠ 0，所以矩阵可逆，有唯一解")
    print()
    
    print("使用克拉默法则求解：")
    print("cu = det(A1) / det(A)")
    print("du = det(A2) / det(A)")
    print()
    
    print("其中：")
    print("det(A) = 1")
    print("det(A1) = (end_u - bu) * 3 - 1 * (end_tangent_u * total_length - bu)")
    print("        = 3*(end_u - bu) - (end_tangent_u * total_length - bu)")
    print("det(A2) = 1 * (end_tangent_u * total_length - bu) - 2 * (end_u - bu)")
    print("        = (end_tangent_u * total_length - bu) - 2*(end_u - bu)")

if __name__ == "__main__":
    # 运行主要演示
    result = solve_cubic_polynomial_constraints()
    
    # 演示矩阵求解原理
    demonstrate_matrix_solution()
    
    print("\n=== 总结 ===")
    print("三次多项式的优势：")
    print("✓ 8个自由度完全匹配8个边界约束")
    print("✓ 可以严格满足起点和终点的位置和切线约束")
    print("✓ 线性方程组有唯一解，数值稳定")
    print("✓ 适合精确的几何建模需求")