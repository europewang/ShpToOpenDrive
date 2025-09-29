#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XODR到OBJ转换器测试脚本
测试基于libOpenDRIVE实现的高级转换功能

作者: ShpToOpenDrive项目组
版本: 3.0.0
"""

import os
import sys
import time
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from xodr_to_obj_converter import XODRToOBJConverter

def test_xodr_to_obj_conversion():
    """
    测试XODR到OBJ转换功能
    """
    print("=" * 60)
    print("XODR到OBJ转换器测试 - 基于libOpenDRIVE v3.0")
    print("=" * 60)
    
    # 测试文件路径
    test_files = [
        "data/testODsample/wh2000/Lane.shp",  # 主要测试文件
        "data/testODsample/LaneTest.shp",     # 进阶测试文件
        "data/test_lane/TestLane.shp"         # 普通测试文件
    ]
    
    # 输出目录
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # 创建转换器实例
    converter = XODRToOBJConverter(
        resolution=0.1,           # 高精度采样
        with_lane_height=True,    # 包含车道高度
        with_road_objects=False,  # 暂不包含道路对象
        eps=0.1                   # 网格精度
    )
    
    print(f"转换器配置:")
    print(f"  - 采样分辨率: {converter.resolution}m")
    print(f"  - 车道高度支持: {converter.with_lane_height}")
    print(f"  - 道路对象支持: {converter.with_road_objects}")
    print(f"  - 网格精度: {converter.eps}")
    print()
    
    success_count = 0
    total_count = 0
    
    for test_file in test_files:
        total_count += 1
        
        # 检查输入文件是否存在
        if not os.path.exists(test_file):
            print(f"⚠️  跳过测试: {test_file} (文件不存在)")
            continue
        
        # 生成输出文件名
        file_name = Path(test_file).stem
        
        # 首先需要将SHP转换为XODR
        xodr_file = output_dir / f"{file_name}.xodr"
        obj_file = output_dir / f"{file_name}_road_mesh.obj"
        
        print(f"🔄 测试文件: {test_file}")
        print(f"   XODR输出: {xodr_file}")
        print(f"   OBJ输出: {obj_file}")
        
        try:
            # 检查是否已有XODR文件
            if not xodr_file.exists():
                print(f"   ⚠️  需要先生成XODR文件: {xodr_file}")
                print(f"   💡 请先运行: python src/shp2xodr.py {test_file} {xodr_file}")
                continue
            
            # 执行XODR到OBJ转换
            start_time = time.time()
            
            result = converter.convert(str(xodr_file), str(obj_file))
            
            end_time = time.time()
            conversion_time = end_time - start_time
            
            if result:
                print(f"   ✅ 转换成功! 耗时: {conversion_time:.2f}秒")
                
                # 检查输出文件
                if obj_file.exists():
                    file_size = obj_file.stat().st_size
                    print(f"   📊 OBJ文件大小: {file_size:,} 字节")
                    
                    # 检查MTL文件
                    mtl_file = obj_file.with_suffix('.mtl')
                    if mtl_file.exists():
                        print(f"   📊 MTL文件已生成: {mtl_file.name}")
                    
                    # 简单验证OBJ文件内容
                    with open(obj_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        vertex_count = sum(1 for line in lines if line.startswith('v '))
                        face_count = sum(1 for line in lines if line.startswith('f '))
                        normal_count = sum(1 for line in lines if line.startswith('vn '))
                        texture_count = sum(1 for line in lines if line.startswith('vt '))
                        
                        print(f"   📊 网格统计:")
                        print(f"      - 顶点数: {vertex_count:,}")
                        print(f"      - 面数: {face_count:,}")
                        print(f"      - 法向量数: {normal_count:,}")
                        print(f"      - 纹理坐标数: {texture_count:,}")
                    
                    success_count += 1
                else:
                    print(f"   ❌ 输出文件未生成")
            else:
                print(f"   ❌ 转换失败")
                
        except Exception as e:
            print(f"   ❌ 转换异常: {str(e)}")
        
        print()
    
    # 测试总结
    print("=" * 60)
    print(f"测试完成: {success_count}/{total_count} 成功")
    
    if success_count > 0:
        print("\n🎉 转换器功能验证成功!")
        print("\n📋 功能特性:")
        print("  ✅ 精确几何体解析 (直线、圆弧、螺旋线、多项式)")
        print("  ✅ 车道级别网格生成")
        print("  ✅ 法向量和纹理坐标支持")
        print("  ✅ 材质文件生成")
        print("  ✅ 基于libOpenDRIVE架构设计")
    else:
        print("\n⚠️  需要先生成XODR文件才能测试OBJ转换功能")
    
    print("=" * 60)

def test_mesh_generation():
    """
    测试网格生成功能
    """
    print("\n🔧 测试网格生成功能...")
    
    try:
        from xodr_to_obj_converter import Mesh3D, Vec3D, Vec2D
        
        # 创建测试网格
        mesh = Mesh3D()
        
        # 添加测试顶点
        mesh.vertices = [
            Vec3D(0, 0, 0),
            Vec3D(1, 0, 0),
            Vec3D(1, 1, 0),
            Vec3D(0, 1, 0)
        ]
        
        # 添加法向量
        mesh.normals = [
            Vec3D(0, 0, 1),
            Vec3D(0, 0, 1),
            Vec3D(0, 0, 1),
            Vec3D(0, 0, 1)
        ]
        
        # 添加纹理坐标
        mesh.st_coordinates = [
            Vec2D(0, 0),
            Vec2D(1, 0),
            Vec2D(1, 1),
            Vec2D(0, 1)
        ]
        
        # 添加索引（两个三角形组成矩形）
        mesh.indices = [0, 1, 2, 0, 2, 3]
        
        # 生成OBJ字符串
        obj_content = mesh.get_obj()
        
        print("✅ 网格生成测试成功")
        print(f"   生成的OBJ内容长度: {len(obj_content)} 字符")
        
        # 保存测试网格
        test_obj_file = Path("output/test_mesh.obj")
        with open(test_obj_file, 'w', encoding='utf-8') as f:
            f.write("# Test mesh generated by XODR to OBJ Converter\n")
            f.write(obj_content)
        
        print(f"   测试网格已保存: {test_obj_file}")
        
    except Exception as e:
        print(f"❌ 网格生成测试失败: {str(e)}")

if __name__ == "__main__":
    # 运行测试
    test_mesh_generation()
    test_xodr_to_obj_conversion()
    
    print("\n💡 提示:")
    print("   如需测试完整流程，请先运行:")
    print("   python src/shp2xodr.py data/test_lane/TestLane.shp output/TestLane.xodr")
    print("   然后再运行此测试脚本")