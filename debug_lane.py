#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lane.shp调试脚本
用于调试Lane.shp文件的转换过程
"""

import sys
import os
import json
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from main import ShpToOpenDriveConverter
from shp_reader import ShapefileReader

def debug_lane_conversion():
    """
    调试Lane.shp文件转换过程
    在需要查看数据的地方设置断点
    """
    
    # 输入文件路径
    input_shp = r"E:\Code\ShpToOpenDrive\data\testODsample\wh2000\Lane.shp"
    output_xodr = r"E:\Code\ShpToOpenDrive\debug_output.xodr"
    config_file = r"E:\Code\ShpToOpenDrive\config\lane_format.json"
    
    print(f"开始调试Lane.shp文件: {input_shp}")
    
    # 1. 加载配置文件
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    print(f"配置加载完成: {config}")
    # 在此处设置断点查看配置内容
    
    # 2. 创建转换器
    converter = ShpToOpenDriveConverter(config)
    print(f"转换器创建完成")
    
    # 3. 创建Shapefile读取器
    reader = ShapefileReader(input_shp)
    print(f"Shapefile读取器创建完成")
    
    # 4. 加载shapefile文件
    if not reader.load_shapefile():
        print("加载shapefile失败")
        return
    print(f"Shapefile文件加载完成")
    
    # 5. 检查是否为Lane格式
    is_lane_format = reader._is_lane_shapefile()
    print(f"是否为Lane格式: {is_lane_format}")
    # 在此处设置断点查看格式检测结果
    
    # 6. 读取几何数据
    geometries = reader.extract_lane_geometries()
    print(f"读取到 {len(geometries)} 条道路")
    # 在此处设置断点查看几何数据
    
    # 7. 检查第一条数据的结构
    if geometries:
        first_road = geometries[0]
        print(f"第一条道路数据: {first_road}")
        # 在此处设置断点查看第一条数据的详细结构
        
        # 检查车道信息
        if 'lanes' in first_road:
            lanes = first_road['lanes']
            print(f"车道数量: {len(lanes)}")
            if lanes:
                print(f"第一条车道: {lanes[0]}")
            # 在此处设置断点查看车道信息
    
    # 8. 执行转换
    try:
        converter.convert(input_shp, output_xodr)
        print(f"转换完成，输出文件: {output_xodr}")
    except Exception as e:
        print(f"转换过程中出现错误: {e}")
        # 在此处设置断点查看错误详情
        raise
    
    print("调试完成")

if __name__ == "__main__":
    debug_lane_conversion()