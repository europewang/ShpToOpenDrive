#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试TestLane.shp文件的脚本
"""

import sys
import os
from pathlib import Path

# 添加src目录到路径
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from shp_reader import ShapefileReader
from geometry_converter import GeometryConverter
from opendrive_generator import OpenDriveGenerator
from main import ShpToOpenDriveConverter

def test_testlane_shp():
    """测试TestLane.shp文件"""
    
    # 输入文件路径
    input_file = r"E:\Code\ShpToOpenDrive\data\testODsample\LaneTest.shp"
    output_file = r"e:\Code\ShpToOpenDrive\output\testlane_output.xodr"
    
    print("=" * 60)
    print("测试TestLane.shp文件")
    print("=" * 60)
    
    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"错误：输入文件不存在 - {input_file}")
        return False
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 步骤1：读取shapefile
        print("\n步骤1：读取shapefile文件...")
        reader = ShapefileReader(input_file)
        reader.load_shapefile()
        
        # 检查文件格式
        print(f"文件格式检查：")
        print(f"  - 是否为Lane格式: {reader._is_lane_shapefile()}")
        
        # 显示基本信息
        if reader.gdf is not None:
            print(f"\n基本信息：")
            print(f"  - 记录数量: {len(reader.gdf)}")
            print(f"  - 字段列表: {list(reader.gdf.columns)}")
            print(f"  - 坐标系统: {reader.gdf.crs}")
            
            # 显示前3条记录的属性
            print(f"\n前3条记录的属性：")
            for i, (idx, row) in enumerate(reader.gdf.head(3).iterrows()):
                print(f"  记录 {i+1}:")
                for col in reader.gdf.columns:
                    if col != 'geometry':
                        print(f"    {col}: {row[col]}")
                print()
        
        # 步骤2：读取几何数据
        print("\n步骤2：读取几何数据...")
        roads_geometries = reader.extract_road_geometries()
        
        if roads_geometries:
            print(f"成功读取 {len(roads_geometries)} 条道路几何数据")
            
            # 显示每条道路的详细坐标信息
            for road_idx, road in enumerate(roads_geometries):
                print(f"\n=== 道路 {road_idx + 1} (ID: {road.get('road_id', 'N/A')}) ===")
                print(f"车道数量: {len(road.get('lanes', []))}")
                print(f"车道面数量: {len(road.get('lane_surfaces', []))}")
                
                # 显示每个车道面的坐标
                for lane_idx, lane_surface in enumerate(road.get('lane_surfaces', [])):
                    print(f"\n--- 车道面 {lane_idx + 1} ---")
                    
                    # 显示左边界坐标和index
                    if lane_surface.get('left_boundary'):
                        left_boundary = lane_surface['left_boundary']
                        left_index = left_boundary.get('index', 'N/A')
                        left_coords = left_boundary.get('coordinates', [])
                        print(f"左边界 (index: {left_index}) 坐标 ({len(left_coords)} 个点):")
                        for i, point in enumerate(left_coords):
                            print(f"  点{i+1}: ({point[0]:.6f}, {point[1]:.6f})")
                    
                    # 显示右边界坐标和index
                    if lane_surface.get('right_boundary'):
                        right_boundary = lane_surface['right_boundary']
                        right_index = right_boundary.get('index', 'N/A')
                        right_coords = right_boundary.get('coordinates', [])
                        print(f"右边界 (index: {right_index}) 坐标 ({len(right_coords)} 个点):")
                        for i, point in enumerate(right_coords):
                            print(f"  点{i+1}: ({point[0]:.6f}, {point[1]:.6f})")
                    
                    # 显示中心线坐标
                    if lane_surface.get('center_line'):
                        center_coords = lane_surface['center_line']
                        print(f"中心线坐标 ({len(center_coords)} 个点):")
                        for i, point in enumerate(center_coords):
                            print(f"  点{i+1}: ({point[0]:.6f}, {point[1]:.6f})")
                    
                    # 如果没有中心线但有左右边界，显示计算的中心线
                    elif (lane_surface.get('left_boundary', {}).get('coordinates') and 
                          lane_surface.get('right_boundary', {}).get('coordinates')):
                        left_coords = lane_surface['left_boundary']['coordinates']
                        right_coords = lane_surface['right_boundary']['coordinates']
                        print(f"计算的中心线坐标:")
                        min_len = min(len(left_coords), len(right_coords))
                        for i in range(min_len):
                            left_pt = left_coords[i]
                            right_pt = right_coords[i]
                            center_x = (left_pt[0] + right_pt[0]) / 2
                            center_y = (left_pt[1] + right_pt[1]) / 2
                            print(f"  点{i+1}: ({center_x:.6f}, {center_y:.6f})")
        else:
            print("未能读取到几何数据")
        
        # 步骤3：执行完整转换
        print("\n步骤3：执行完整转换...")
        
        # 启用详细日志
        import logging
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
        
        converter = ShpToOpenDriveConverter()
        
        try:
            success = converter.convert(input_file, output_file)
            
            if success:
                print(f"\n✓ 转换成功！")
                print(f"输出文件: {output_file}")
                
                # 检查输出文件大小
                if os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    print(f"输出文件大小: {file_size} 字节")
                    
                return True
            else:
                print(f"\n✗ 转换失败！")
                # 尝试获取转换器的错误信息
                if hasattr(converter, 'last_error'):
                    print(f"错误信息: {converter.last_error}")
                return False
                
        except Exception as conv_e:
            print(f"\n✗ 转换过程中发生异常: {str(conv_e)}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"\n错误：{str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_testlane_shp()
    if success:
        print("\n=" * 60)
        print("测试完成 - 成功")
        print("=" * 60)
    else:
        print("\n=" * 60)
        print("测试完成 - 失败")
        print("=" * 60)
        sys.exit(1)