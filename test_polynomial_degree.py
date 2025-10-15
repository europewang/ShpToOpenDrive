#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试多项式度数限制是否已解除
"""

import numpy as np
import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from geometry_converter import GeometryConverter

def test_polynomial_degree_limit():
    """测试多项式度数限制"""
    print("=== 测试多项式度数限制 ===\n")
    
    # 创建一个复杂的曲线数据（足够多的点来支持高阶多项式）
    t = np.linspace(0, 1, 20)  # 20个点
    # 创建一个复杂的曲线：包含多个频率的正弦波
    x = t * 100
    y = 10 * np.sin(2 * np.pi * t) + 5 * np.sin(4 * np.pi * t) + 2 * np.sin(8 * np.pi * t)
    
    coordinates = list(zip(x, y))
    
    # 测试不同的polynomial_degree设置
    test_degrees = [3, 4, 5, 6]
    
    for degree in test_degrees:
        print(f"测试 polynomial_degree = {degree}")
        
        # 创建GeometryConverter实例
        converter = GeometryConverter(
            tolerance=0.1,
            curve_fitting_mode="parampoly3",
            polynomial_degree=degree,
            curve_smoothness=0.5
        )
        
        # 创建足够的参数点
        arc_lengths = converter._calculate_arc_lengths(coordinates)
        total_length = arc_lengths[-1]
        t_params = arc_lengths / total_length
        
        # 转换为局部坐标
        start_heading = converter._calculate_precise_heading(coordinates[:3])
        start_x, start_y = coordinates[0]
        cos_hdg = np.cos(start_heading)
        sin_hdg = np.sin(start_heading)
        
        local_u = np.zeros(len(coordinates))
        local_v = np.zeros(len(coordinates))
        
        for i in range(len(coordinates)):
            dx = x[i] - start_x
            dy = y[i] - start_y
            local_u[i] = dx * cos_hdg + dy * sin_hdg
            local_v[i] = -dx * sin_hdg + dy * cos_hdg
        
        # 测试_select_optimal_polynomial_degree方法
        optimal_degree = converter._select_optimal_polynomial_degree(t_params, local_u, local_v)
        
        print(f"  设置的polynomial_degree: {degree}")
        print(f"  选择的optimal_degree: {optimal_degree}")
        print(f"  数据点数量: {len(coordinates)}")
        print(f"  理论最大度数: {len(coordinates) - 1}")
        
        # 验证是否能使用高阶多项式
        if optimal_degree > 3:
            print(f"  ✓ 成功选择了高于3的多项式度数: {optimal_degree}")
        else:
            print(f"  - 选择的度数仍为: {optimal_degree}")
        
        print()

if __name__ == "__main__":
    test_polynomial_degree_limit()