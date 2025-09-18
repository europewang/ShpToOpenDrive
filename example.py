#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例脚本：Shapefile到OpenDrive转换

演示如何使用ShpToOpenDriveConverter进行文件转换。
"""

import os
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.main import ShpToOpenDriveConverter


def example_basic_conversion():
    """基本转换示例"""
    print("=== 基本转换示例 ===")
    
    # 输入输出路径（请根据实际情况修改）
    input_shapefile = "data/roads.shp"  # 替换为你的shapefile路径
    output_opendrive = "output/roads.xodr"
    
    # 检查输入文件是否存在
    if not os.path.exists(input_shapefile):
        print(f"错误：输入文件不存在 {input_shapefile}")
        print("请将你的shapefile放在data/目录下，或修改路径")
        return False
    
    # 创建输出目录
    os.makedirs(os.path.dirname(output_opendrive), exist_ok=True)
    
    # 创建转换器
    converter = ShpToOpenDriveConverter()
    
    # 执行转换
    success = converter.convert(input_shapefile, output_opendrive)
    
    if success:
        print(f"转换成功！输出文件：{output_opendrive}")
        
        # 显示统计信息
        stats = converter.get_conversion_stats()
        print(f"输入道路数：{stats['input_roads']}")
        print(f"输出道路数：{stats['output_roads']}")
        print(f"总长度：{stats['total_length']:.2f} 米")
        print(f"转换时间：{stats['conversion_time']:.2f} 秒")
    else:
        print("转换失败！")
    
    return success


def example_custom_config():
    """自定义配置转换示例"""
    print("\n=== 自定义配置转换示例 ===")
    
    # 输入输出路径
    input_shapefile = "data/roads.shp"
    output_opendrive = "output/roads_custom.xodr"
    
    if not os.path.exists(input_shapefile):
        print(f"错误：输入文件不存在 {input_shapefile}")
        return False
    
    # 自定义配置
    custom_config = {
        'geometry_tolerance': 0.5,      # 更高精度
        'min_road_length': 5.0,         # 更短的最小长度
        'default_lane_width': 3.0,      # 更窄的车道
        'default_num_lanes': 2,         # 双车道
        'default_speed_limit': 60,      # 更高限速
        'use_arc_fitting': True,        # 使用圆弧拟合
        'coordinate_precision': 4,      # 更高坐标精度
    }
    
    # 创建输出目录
    os.makedirs(os.path.dirname(output_opendrive), exist_ok=True)
    
    # 创建转换器
    converter = ShpToOpenDriveConverter(custom_config)
    
    # 属性映射示例（根据你的shapefile属性调整）
    attribute_mapping = {
        'WIDTH': 'lane_width',      # 将WIDTH字段映射到车道宽度
        'LANES': 'num_lanes',       # 将LANES字段映射到车道数
        'SPEED': 'speed_limit',     # 将SPEED字段映射到限速
        'TYPE': 'road_type',        # 将TYPE字段映射到道路类型
    }
    
    # 执行转换
    success = converter.convert(
        input_shapefile, 
        output_opendrive, 
        attribute_mapping
    )
    
    if success:
        print(f"自定义配置转换成功！输出文件：{output_opendrive}")
        
        # 保存转换报告
        report_path = "output/conversion_report.json"
        converter.save_conversion_report(report_path)
        print(f"转换报告已保存：{report_path}")
    else:
        print("自定义配置转换失败！")
    
    return success


def example_batch_conversion():
    """批量转换示例"""
    print("\n=== 批量转换示例 ===")
    
    # 输入目录
    input_dir = "data/"
    output_dir = "output/batch/"
    
    if not os.path.exists(input_dir):
        print(f"错误：输入目录不存在 {input_dir}")
        return False
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 查找所有shapefile
    shapefiles = list(Path(input_dir).glob("*.shp"))
    
    if not shapefiles:
        print(f"在 {input_dir} 中没有找到shapefile")
        return False
    
    print(f"找到 {len(shapefiles)} 个shapefile")
    
    # 批量转换配置
    batch_config = {
        'geometry_tolerance': 1.0,
        'min_road_length': 10.0,
        'use_arc_fitting': False,
    }
    
    success_count = 0
    total_count = len(shapefiles)
    
    for shapefile in shapefiles:
        print(f"\n转换文件：{shapefile.name}")
        
        # 输出文件路径
        output_file = os.path.join(output_dir, f"{shapefile.stem}.xodr")
        
        # 创建新的转换器实例
        converter = ShpToOpenDriveConverter(batch_config)
        
        # 执行转换
        success = converter.convert(str(shapefile), output_file)
        
        if success:
            success_count += 1
            print(f"✓ 转换成功：{output_file}")
        else:
            print(f"✗ 转换失败：{shapefile.name}")
    
    print(f"\n批量转换完成：{success_count}/{total_count} 成功")
    return success_count > 0


def create_sample_data():
    """创建示例数据目录结构"""
    print("=== 创建示例数据目录 ===")
    
    # 创建目录
    directories = ['data', 'output', 'config']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"创建目录：{directory}/")
    
    # 创建示例配置文件
    config_file = "config/example_config.json"
    example_config = {
        "geometry_tolerance": 1.0,
        "min_road_length": 10.0,
        "default_lane_width": 3.5,
        "default_num_lanes": 1,
        "default_speed_limit": 50,
        "use_arc_fitting": False,
        "coordinate_precision": 3
    }
    
    import json
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(example_config, f, indent=2, ensure_ascii=False)
    
    print(f"创建示例配置文件：{config_file}")
    
    # 创建README文件
    readme_content = """# Shapefile到OpenDrive转换器使用说明

## 目录结构
- data/: 放置输入的shapefile文件
- output/: 转换后的OpenDrive文件输出目录
- config/: 配置文件目录

## 使用步骤
1. 将你的shapefile文件（.shp, .shx, .dbf等）放入data/目录
2. 运行 python example.py
3. 在output/目录查看生成的.xodr文件

## 配置说明
- geometry_tolerance: 几何拟合容差（米）
- min_road_length: 最小道路长度（米）
- default_lane_width: 默认车道宽度（米）
- default_num_lanes: 默认车道数
- default_speed_limit: 默认限速（km/h）
- use_arc_fitting: 是否使用圆弧拟合
- coordinate_precision: 坐标精度（小数位数）

## 属性映射
如果你的shapefile包含道路属性，可以通过attribute_mapping参数映射到OpenDrive属性：
- WIDTH -> lane_width
- LANES -> num_lanes  
- SPEED -> speed_limit
- TYPE -> road_type
"""
    
    with open("README.md", 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print("创建README.md文件")
    
    print("\n请将你的shapefile文件放入data/目录，然后运行转换示例")


def main():
    """主函数"""
    print("Shapefile到OpenDrive转换器示例")
    print("=" * 50)
    
    # 创建示例目录结构
    create_sample_data()
    
    # 检查是否有输入文件
    if not any(Path("data").glob("*.shp")):
        print("\n注意：data/目录中没有找到shapefile文件")
        print("请将你的.shp文件（及相关的.shx, .dbf文件）放入data/目录")
        print("然后重新运行此脚本")
        return
    
    # 运行转换示例
    try:
        # 基本转换
        example_basic_conversion()
        
        # 自定义配置转换
        example_custom_config()
        
        # 批量转换
        example_batch_conversion()
        
    except KeyboardInterrupt:
        print("\n用户中断转换")
    except Exception as e:
        print(f"\n转换过程出错：{e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()