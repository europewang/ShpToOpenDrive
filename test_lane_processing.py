#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Lane.shp处理逻辑
验证新的车道面构建和几何转换功能
"""

import os
import sys
import json
import logging
from pathlib import Path

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from main import ShpToOpenDriveConverter
from shp_reader import ShapefileReader
from geometry_converter import GeometryConverter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_lane_shp_reading():
    """测试Lane.shp文件读取功能"""
    print("\n=== 测试Lane.shp文件读取 ===")
    
    lane_shp_path = "e:\\Code\\ShpToOpenDrive\\data\\testODsample\\wh2000\\Lane.shp"
    
    if not os.path.exists(lane_shp_path):
        print(f"错误：Lane.shp文件不存在 {lane_shp_path}")
        return False
    
    try:
        # 创建shapefile读取器
        reader = ShapefileReader(lane_shp_path)
        
        # 加载shapefile
        success = reader.load_shapefile()
        if not success:
            print("错误：无法加载Lane.shp文件")
            return False
        
        print(f"成功加载Lane.shp文件，包含 {len(reader.gdf)} 条记录")
        
        # 检查是否为Lane格式
        is_lane_format = reader._is_lane_shapefile()
        print(f"Lane格式检测结果: {is_lane_format}")
        
        if is_lane_format:
            # 提取Lane几何数据
            roads_geometries = reader.extract_lane_geometries()
            print(f"提取到 {len(roads_geometries)} 条道路的车道数据")
            
            # 显示第一条道路的详细信息
            if roads_geometries:
                first_road = roads_geometries[0]
                print(f"\n第一条道路信息:")
                print(f"  RoadID: {first_road['road_id']}")
                print(f"  车道数量: {len(first_road['lanes'])}")
                print(f"  车道面数量: {len(first_road['lane_surfaces'])}")
                
                # 显示车道面信息
                if first_road['lanes']:
                    first_lane = first_road['lanes'][0]
                    print(f"  第一个车道面ID: {first_lane.get('surface_id', 'N/A')}")
                    print(f"  左边界索引: {first_lane['left_boundary']['index']}")
                    print(f"  右边界索引: {first_lane['right_boundary']['index']}")
                    
                    # 显示所有车道面的边界索引
                    surface_ids = [lane['surface_id'] for lane in first_road['lanes']]
                    print(f"  车道面IDs: {surface_ids}")
        
        return True
        
    except Exception as e:
        print(f"测试失败: {e}")
        logger.exception("Lane.shp读取测试异常")
        return False

def test_lane_geometry_conversion():
    """测试车道面几何转换功能"""
    print("\n=== 测试车道面几何转换 ===")
    
    try:
        # 创建几何转换器
        converter = GeometryConverter(tolerance=0.5)
        
        # 模拟车道面数据
        mock_lane_surfaces = [
            {
                'surface_id': '0_1',
                'left_boundary': {
                    'index': 0,
                    'coordinates': [(0, 0), (10, 0), (20, 2), (30, 5)],
                    'geometry': None
                },
                'right_boundary': {
                    'index': 1,
                    'coordinates': [(0, 3), (10, 3.5), (20, 5), (30, 8)],
                    'geometry': None
                }
            }
        ]
        
        # 转换车道面几何
        converted_surfaces = converter.convert_lane_surface_geometry(mock_lane_surfaces)
        
        if converted_surfaces:
            print(f"成功转换 {len(converted_surfaces)} 个车道面")
            
            surface = converted_surfaces[0]
            print(f"\n车道面 {surface['surface_id']} 转换结果:")
            print(f"  中心线几何段数量: {len(surface['center_segments'])}")
            print(f"  宽度变化点数量: {len(surface['width_profile'])}")
            
            # 显示宽度变化
            width_profile = surface['width_profile']
            print(f"  起始宽度: {width_profile[0]['width']:.2f}m")
            print(f"  结束宽度: {width_profile[-1]['width']:.2f}m")
            
            return True
        else:
            print("车道面几何转换失败")
            return False
            
    except Exception as e:
        print(f"测试失败: {e}")
        logger.exception("车道面几何转换测试异常")
        return False

def test_full_conversion():
    """测试完整的Lane.shp转换流程"""
    print("\n=== 测试完整转换流程 ===")
    
    lane_shp_path = "e:\\Code\\ShpToOpenDrive\\data\\testODsample\\wh2000\\Lane.shp"
    output_path = "e:\\Code\\ShpToOpenDrive\\output\\test_lane_output.xodr"
    
    if not os.path.exists(lane_shp_path):
        print(f"错误：Lane.shp文件不存在 {lane_shp_path}")
        return False
    
    try:
        # 创建输出目录
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 加载Lane格式配置
        config_path = "e:\\Code\\ShpToOpenDrive\\config\\lane_format.json"
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print("使用Lane格式专用配置")
        else:
            config = {}
            print("使用默认配置")
        
        # 创建转换器
        converter = ShpToOpenDriveConverter(config)
        
        # 执行转换
        print(f"开始转换: {lane_shp_path} -> {output_path}")
        success = converter.convert(lane_shp_path, output_path)
        
        if success:
            print("转换成功完成！")
            
            # 显示转换统计
            stats = converter.get_conversion_stats()
            print(f"\n转换统计:")
            print(f"  输入道路数: {stats['input_roads']}")
            print(f"  输出道路数: {stats['output_roads']}")
            print(f"  总长度: {stats['total_length']:.2f}m")
            print(f"  转换时间: {stats['conversion_time']:.2f}s")
            
            if stats['warnings']:
                print(f"  警告数量: {len(stats['warnings'])}")
            
            if stats['errors']:
                print(f"  错误数量: {len(stats['errors'])}")
            
            # 检查输出文件
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"  输出文件大小: {file_size} bytes")
            
            return True
        else:
            print("转换失败")
            return False
            
    except Exception as e:
        print(f"测试失败: {e}")
        logger.exception("完整转换测试异常")
        return False

def main():
    """主测试函数"""
    print("Lane.shp处理逻辑测试")
    print("=" * 50)
    
    test_results = []
    
    # 运行各项测试
    test_results.append(("Lane.shp文件读取", test_lane_shp_reading()))
    test_results.append(("车道面几何转换", test_lane_geometry_conversion()))
    test_results.append(("完整转换流程", test_full_conversion()))
    
    # 显示测试结果汇总
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    
    all_passed = True
    for test_name, result in test_results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {test_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n总体结果:", "✓ 所有测试通过" if all_passed else "✗ 部分测试失败")
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())