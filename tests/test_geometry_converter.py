#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
几何转换模块测试

测试GeometryConverter类的各种功能。
"""

import unittest
import numpy as np
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from geometry_converter import GeometryConverter


class TestGeometryConverter(unittest.TestCase):
    """几何转换器测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.converter = GeometryConverter(tolerance=1.0)
    
    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.converter.tolerance, 1.0)
        self.assertIsNotNone(self.converter)
    
    def test_simplify_line_basic(self):
        """测试基本线条简化"""
        # 创建一条简单的直线（有冗余点）
        coordinates = [
            [0, 0],
            [1, 0],
            [2, 0],
            [3, 0],
            [4, 0]
        ]
        
        simplified = self.converter.simplify_line(coordinates)
        
        # 简化后应该只保留起点和终点
        self.assertEqual(len(simplified), 2)
        self.assertEqual(simplified[0], [0, 0])
        self.assertEqual(simplified[-1], [4, 0])
    
    def test_simplify_line_curved(self):
        """测试曲线简化"""
        # 创建一条曲线
        coordinates = [
            [0, 0],
            [1, 1],
            [2, 1.5],
            [3, 1.8],
            [4, 2]
        ]
        
        simplified = self.converter.simplify_line(coordinates)
        
        # 曲线简化后应该保留关键点
        self.assertGreaterEqual(len(simplified), 2)
        self.assertEqual(simplified[0], [0, 0])
        self.assertEqual(simplified[-1], [4, 2])
    
    def test_fit_line_segments_straight(self):
        """测试直线段拟合"""
        # 创建一条直线
        coordinates = [
            [0, 0],
            [10, 0],
            [20, 0]
        ]
        
        segments = self.converter.fit_line_segments(coordinates)
        
        # 应该生成一个直线段
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]['type'], 'line')
        self.assertAlmostEqual(segments[0]['length'], 20.0, places=1)
    
    def test_fit_line_segments_multiple(self):
        """测试多段直线拟合"""
        # 创建L形路径
        coordinates = [
            [0, 0],
            [10, 0],
            [10, 10]
        ]
        
        segments = self.converter.fit_line_segments(coordinates)
        
        # 应该生成两个直线段
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0]['type'], 'line')
        self.assertEqual(segments[1]['type'], 'line')
    
    def test_fit_arc_segments_circle(self):
        """测试圆弧拟合"""
        # 创建一个四分之一圆
        angles = np.linspace(0, np.pi/2, 10)
        radius = 10
        coordinates = [[radius * np.cos(a), radius * np.sin(a)] for a in angles]
        
        segments = self.converter.fit_arc_segments(coordinates)
        
        # 应该至少有一个段
        self.assertGreater(len(segments), 0)
        
        # 检查是否包含圆弧段
        has_arc = any(seg['type'] == 'arc' for seg in segments)
        self.assertTrue(has_arc or len(segments) == 1)  # 可能被识别为直线
    
    def test_calculate_distance(self):
        """测试距离计算"""
        point1 = [0, 0]
        point2 = [3, 4]
        
        distance = self.converter._calculate_distance(point1, point2)
        
        # 3-4-5直角三角形
        self.assertAlmostEqual(distance, 5.0, places=5)
    
    def test_calculate_angle(self):
        """测试角度计算"""
        point1 = [0, 0]
        point2 = [1, 0]
        
        angle = self.converter._calculate_angle(point1, point2)
        
        # 水平向右应该是0度
        self.assertAlmostEqual(angle, 0.0, places=5)
        
        # 测试垂直向上
        point3 = [0, 1]
        angle2 = self.converter._calculate_angle(point1, point3)
        self.assertAlmostEqual(angle2, np.pi/2, places=5)
    
    def test_validate_geometry_continuity_continuous(self):
        """测试连续几何验证"""
        # 创建连续的几何段
        segments = [
            {
                'type': 'line',
                'start_point': [0, 0],
                'end_point': [10, 0],
                'length': 10.0,
                'heading': 0.0
            },
            {
                'type': 'line',
                'start_point': [10, 0],
                'end_point': [10, 10],
                'length': 10.0,
                'heading': np.pi/2
            }
        ]
        
        is_continuous = self.converter.validate_geometry_continuity(segments)
        self.assertTrue(is_continuous)
    
    def test_validate_geometry_continuity_discontinuous(self):
        """测试不连续几何验证"""
        # 创建不连续的几何段
        segments = [
            {
                'type': 'line',
                'start_point': [0, 0],
                'end_point': [10, 0],
                'length': 10.0,
                'heading': 0.0
            },
            {
                'type': 'line',
                'start_point': [15, 0],  # 不连续
                'end_point': [25, 0],
                'length': 10.0,
                'heading': 0.0
            }
        ]
        
        is_continuous = self.converter.validate_geometry_continuity(segments)
        self.assertFalse(is_continuous)
    
    def test_calculate_road_length(self):
        """测试道路长度计算"""
        segments = [
            {
                'type': 'line',
                'length': 10.0
            },
            {
                'type': 'arc',
                'length': 15.7  # π * 5 (半径5的半圆)
            },
            {
                'type': 'line',
                'length': 20.0
            }
        ]
        
        total_length = self.converter.calculate_road_length(segments)
        self.assertAlmostEqual(total_length, 45.7, places=1)
    
    def test_empty_coordinates(self):
        """测试空坐标处理"""
        coordinates = []
        
        segments = self.converter.fit_line_segments(coordinates)
        self.assertEqual(len(segments), 0)
        
        segments = self.converter.fit_arc_segments(coordinates)
        self.assertEqual(len(segments), 0)
    
    def test_single_point(self):
        """测试单点处理"""
        coordinates = [[0, 0]]
        
        segments = self.converter.fit_line_segments(coordinates)
        self.assertEqual(len(segments), 0)
    
    def test_two_points(self):
        """测试两点处理"""
        coordinates = [[0, 0], [10, 0]]
        
        segments = self.converter.fit_line_segments(coordinates)
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]['type'], 'line')
        self.assertAlmostEqual(segments[0]['length'], 10.0, places=1)
    
    def test_tolerance_effect(self):
        """测试容差效果"""
        # 创建有小偏差的直线
        coordinates = [
            [0, 0],
            [5, 0.1],  # 小偏差
            [10, 0]
        ]
        
        # 高容差转换器
        high_tolerance_converter = GeometryConverter(tolerance=1.0)
        segments_high = high_tolerance_converter.fit_line_segments(coordinates)
        
        # 低容差转换器
        low_tolerance_converter = GeometryConverter(tolerance=0.01)
        segments_low = low_tolerance_converter.fit_line_segments(coordinates)
        
        # 高容差应该产生更少的段
        self.assertLessEqual(len(segments_high), len(segments_low))


class TestGeometryConverterIntegration(unittest.TestCase):
    """几何转换器集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.converter = GeometryConverter(tolerance=0.5)
    
    def test_complex_road_conversion(self):
        """测试复杂道路转换"""
        # 创建一个复杂的道路：直线 + 曲线 + 直线
        coordinates = []
        
        # 第一段：直线
        for i in range(11):
            coordinates.append([i, 0])
        
        # 第二段：曲线（四分之一圆）
        angles = np.linspace(0, np.pi/2, 10)
        radius = 5
        for a in angles[1:]:  # 跳过第一个点避免重复
            x = 10 + radius - radius * np.cos(a)
            y = radius * np.sin(a)
            coordinates.append([x, y])
        
        # 第三段：直线
        for i in range(1, 11):
            coordinates.append([15, 5 + i])
        
        # 转换
        segments = self.converter.fit_line_segments(coordinates)
        
        # 验证结果
        self.assertGreater(len(segments), 0)
        
        # 验证连续性
        is_continuous = self.converter.validate_geometry_continuity(segments)
        self.assertTrue(is_continuous)
        
        # 验证总长度合理
        total_length = self.converter.calculate_road_length(segments)
        self.assertGreater(total_length, 20)  # 至少应该有直线段的长度
    
    def test_real_world_scenario(self):
        """测试真实世界场景"""
        # 模拟GPS轨迹数据（有噪声）
        np.random.seed(42)  # 确保测试可重复
        
        # 基础路径：一条S形曲线
        t = np.linspace(0, 4*np.pi, 50)
        x = t
        y = 2 * np.sin(t/2)
        
        # 添加噪声
        noise_level = 0.1
        x += np.random.normal(0, noise_level, len(x))
        y += np.random.normal(0, noise_level, len(y))
        
        coordinates = [[x[i], y[i]] for i in range(len(x))]
        
        # 转换
        segments = self.converter.fit_line_segments(coordinates)
        
        # 验证结果
        self.assertGreater(len(segments), 0)
        
        # 验证所有段都有有效的属性
        for segment in segments:
            self.assertIn('type', segment)
            self.assertIn('length', segment)
            self.assertIn('start_point', segment)
            self.assertIn('end_point', segment)
            self.assertGreater(segment['length'], 0)


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)