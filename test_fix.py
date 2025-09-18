#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试坐标解包修复
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from shp_reader import ShapefileReader
from geometry_converter import GeometryConverter

def test_coordinate_fix():
    """测试坐标解包修复"""
    try:
        print("开始测试坐标解包修复...")
        
        # 读取shapefile
        reader = ShapefileReader("data/CenterLane.shp")
        if not reader.load_shapefile():
            print("❌ 加载shapefile失败")
            return False
        
        print("✅ 成功加载shapefile")
        
        # 提取道路几何
        roads = reader.extract_road_geometries()
        if not roads:
            print("❌ 提取道路几何失败")
            return False
        
        print(f"✅ 成功提取 {len(roads)} 条道路")
        
        # 测试几何转换
        converter = GeometryConverter()
        for i, road in enumerate(roads[:3]):  # 只测试前3条道路
            coordinates = road['coordinates']
            print(f"道路 {i+1}: {len(coordinates)} 个坐标点")
            
            # 检查坐标格式
            if coordinates:
                first_coord = coordinates[0]
                print(f"  第一个坐标: {first_coord} (类型: {type(first_coord)})")
                
                # 尝试转换几何
                segments = converter.convert_road_geometry(coordinates)
                if segments:
                    print(f"  ✅ 成功转换为 {len(segments)} 个几何段")
                else:
                    print(f"  ❌ 几何转换失败")
                    return False
        
        print("\n🎉 所有测试通过！坐标解包修复成功！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_coordinate_fix()
    sys.exit(0 if success else 1)
