#!/usr/bin/env python3
"""
三次多项式约束分析
演示为什么三次多项式可以同时满足所有约束条件
"""

import numpy as np
import math

def analyze_cubic_constraints():
    """分析三次多项式的约束满足能力"""
    
    print("=== 三次多项式约束分析 ===\n")
    
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
    
    # 步骤2：求解cu, du以满足终点约束
    # 对于三次多项式：u(t) = au + bu*t + cu*t² + du*t³
    # 约束条件：
    # u(1) = bu + cu + du = end_u
    # u'(1) = bu + 2*cu + 3*du = end_tangent_u * total_length
    
    expected_end_tangent_u = end_tangent_u * total_length
    expected_end_tangent_v = end_tangent_v * total_length
    
    # 求解2x2线性方程组
    # [1  1] [cu]   [end_u - bu]
    # [2  3] [du] = [end_tangent_u * length - bu]
    
    A_u = np.array([[1, 1], [2, 3]])
    b_u = np.array([end_u - bu, expected_end_tangent_u - bu])
    
    try:
        cu, du = np.linalg.solve(A_u, b_u)
        print(f"步骤2 - 求解u方向系数：")
        print(f"线性方程组 A_u:")
        print(A_u)
        print(f"右侧向量 b_u: {b_u}")
        print(f"解: cu = {cu:.3f}, du = {du:.3f}")
        print()
    except np.linalg.LinAlgError:
        print("错误：线性方程组奇异，无法求解")
        return
    
    # 同样求解v方向
    A_v = np.array([[1, 1], [2, 3]])
    b_v = np.array([end_v - bv, expected_end_tangent_v - bv])
    
    try:
        cv, dv = np.linalg.solve(A_v, b_v)
        print(f"步骤3 - 求解v方向系数：")
        print(f"线性方程组 A_v:")
        print(A_v)
        print(f"右侧向量 b_v: {b_v}")
        print(f"解: cv = {cv:.3f}, dv = {dv:.3f}")
        print()
    except np.linalg.LinAlgError:
        print("错误：线性方程组奇异，无法求解")
        return
    
    # 验证所有约束条件
    print("=== 约束验证 ===")
    
    # 验证起点位置
    u_0 = au
    v_0 = av
    print(f"1. 起点位置约束:")
    print(f"   u(0) = {u_0} (期望: 0)")
    print(f"   v(0) = {v_0} (期望: 0)")
    print(f"   ✓ 满足" if abs(u_0) < 1e-10 and abs(v_0) < 1e-10 else "   ✗ 不满足")
    print()
    
    # 验证起点切线
    u_prime_0 = bu
    v_prime_0 = bv
    expected_u_prime_0 = start_tangent_u * total_length
    expected_v_prime_0 = start_tangent_v * total_length
    print(f"2. 起点切线约束:")
    print(f"   u'(0) = {u_prime_0} (期望: {expected_u_prime_0})")
    print(f"   v'(0) = {v_prime_0} (期望: {expected_v_prime_0})")
    tangent_0_ok = abs(u_prime_0 - expected_u_prime_0) < 1e-10 and abs(v_prime_0 - expected_v_prime_0) < 1e-10
    print(f"   ✓ 满足" if tangent_0_ok else "   ✗ 不满足")
    print()
    
    # 验证终点位置
    u_1 = bu + cu + du
    v_1 = bv + cv + dv
    print(f"3. 终点位置约束:")
    print(f"   u(1) = {u_1:.3f} (期望: {end_u})")
    print(f"   v(1) = {v_1:.3f} (期望: {end_v})")
    position_1_ok = abs(u_1 - end_u) < 1e-10 and abs(v_1 - end_v) < 1e-10
    print(f"   ✓ 满足" if position_1_ok else "   ✗ 不满足")
    print()
    
    # 验证终点切线
    u_prime_1 = bu + 2*cu + 3*du
    v_prime_1 = bv + 2*cv + 3*dv
    print(f"4. 终点切线约束:")
    print(f"   u'(1) = {u_prime_1:.3f} (期望: {expected_end_tangent_u})")
    print(f"   v'(1) = {v_prime_1:.3f} (期望: {expected_end_tangent_v})")
    tangent_1_ok = abs(u_prime_1 - expected_end_tangent_u) < 1e-10 and abs(v_prime_1 - expected_end_tangent_v) < 1e-10
    print(f"   ✓ 满足" if tangent_1_ok else "   ✗ 不满足")
    print()
    
    # 自由度分析
    print("=== 自由度分析 ===")
    print("三次多项式 u(t) = au + bu*t + cu*t² + du*t³ 有4个系数：au, bu, cu, du")
    print("同样，v(t) = av + bv*t + cv*t² + dv*t³ 有4个系数：av, bv, cv, dv")
    print("总共8个自由度")
    print()
    
    print("约束条件：")
    print("1. u(0) = 0  →  au = 0")
    print("2. v(0) = 0  →  av = 0")
    print("3. u'(0) = start_tangent_u  →  bu = start_tangent_u * length")
    print("4. v'(0) = start_tangent_v  →  bv = start_tangent_v * length")
    print("5. u(1) = end_u  →  bu + cu + du = end_u")
    print("6. v(1) = end_v  →  bv + cv + dv = end_v")
    print("7. u'(1) = end_tangent_u  →  bu + 2*cu + 3*du = end_tangent_u * length")
    print("8. v'(1) = end_tangent_v  →  bv + 2*cv + 3*dv = end_tangent_v * length")
    print()
    
    print("结论：8个约束条件，8个自由度 → 完全确定的系统！")
    print("前4个约束确定了au, av, bu, bv")
    print("后4个约束形成两个独立的2x2线性方程组，可以唯一确定cu, du, cv, dv")
    print()
    
    # 总结
    all_satisfied = tangent_0_ok and position_1_ok and tangent_1_ok
    print("=== 总结 ===")
    if all_satisfied:
        print("✓ 三次多项式可以严格满足所有约束条件！")
        print("这就是为什么我们在代码中优先选择三次多项式的原因。")
    else:
        print("✗ 存在约束冲突，需要检查计算。")
    
    print(f"\n最终多项式系数：")
    print(f"u(t) = {au} + {bu:.3f}*t + {cu:.3f}*t² + {du:.3f}*t³")
    print(f"v(t) = {av} + {bv:.3f}*t + {cv:.3f}*t² + {dv:.3f}*t³")

if __name__ == "__main__":
    analyze_cubic_constraints()