#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XODR到OBJ转换脚本
基于libOpenDRIVE实现的OpenDRIVE到OBJ格式转换工具

功能特性:
- 精确几何体解析（直线、圆弧、螺旋线、多项式）
- 车道级别网格生成
- 法向量和纹理坐标支持
- 材质和分组管理
- 高性能转换引擎

作者: ShpToOpenDrive项目组
版本: 3.0.0
日期: 2024
"""

import sys
import os
import argparse
import time
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from xodr_to_obj_converter import XODRToOBJConverter


def main():
    """
    主函数：处理命令行参数并执行XODR到OBJ转换
    """
    parser = argparse.ArgumentParser(
        description='XODR到OBJ转换工具 - 基于libOpenDRIVE架构',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python xodr2obj.py input.xodr output.obj
  python xodr2obj.py input.xodr output.obj --resolution 0.1
  python xodr2obj.py input.xodr output.obj --resolution 0.5 --with-height
  python xodr2obj.py input.xodr output.obj --high-quality

输出文件:
  - output.obj: 3D网格模型文件
  - output.mtl: 材质定义文件
        """
    )
    
    # 必需参数
    parser.add_argument('input', help='输入的XODR文件路径')
    parser.add_argument('output', help='输出的OBJ文件路径')
    
    # 可选参数
    parser.add_argument('--resolution', '-r', type=float, default=0.5,
                       help='采样分辨率（米），默认0.5米')
    parser.add_argument('--with-height', action='store_true',
                       help='包含车道高度信息')
    parser.add_argument('--with-objects', action='store_true',
                       help='包含道路对象（实验性功能）')
    parser.add_argument('--eps', type=float, default=0.1,
                       help='网格生成精度，默认0.1米')
    parser.add_argument('--high-quality', action='store_true',
                       help='高质量模式（分辨率0.1米，包含高度信息）')
    parser.add_argument('--medium-quality', action='store_true', default=True,
                       help='中级质量模式（分辨率0.2米，不包含高度信息），默认启用')
    parser.add_argument('--low-quality', action='store_true',
                       help='低质量模式（分辨率0.5米，不包含高度信息）')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='显示详细输出信息')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='静默模式，只显示错误信息')
    
    args = parser.parse_args()
    
    # 质量模式设置
    if args.low_quality:
        args.resolution = 0.5
        args.with_height = False
        args.high_quality = False
        args.medium_quality = False
        if args.verbose:
            print("⚡ 启用低质量模式：分辨率0.5米，不包含高度信息")
    elif args.high_quality:
        args.resolution = 0.1
        args.with_height = True
        args.medium_quality = False
        if args.verbose:
            print("🎯 启用高质量模式：分辨率0.1米，包含高度信息")
    elif getattr(args, 'medium_quality', True):
        args.resolution = 0.2
        args.with_height = False
        args.high_quality = False
        if args.verbose:
            print("🔧 启用中级质量模式：分辨率0.2米，不包含高度信息")
    else:
        # 默认中级质量模式
        args.resolution = 0.2
        args.with_height = False
        if args.verbose:
            print("🔧 默认启用中级质量模式：分辨率0.2米，不包含高度信息")
    
    # 验证输入文件
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ 错误：输入文件不存在 - {args.input}")
        sys.exit(1)
    
    if not input_path.suffix.lower() == '.xodr':
        print(f"❌ 错误：输入文件必须是.xodr格式 - {args.input}")
        sys.exit(1)
    
    # 创建输出目录
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 显示转换信息
    if not args.quiet:
        print("=" * 60)
        print("XODR到OBJ转换工具 v3.0.0")
        print("基于libOpenDRIVE架构设计")
        print("=" * 60)
        print(f"📁 输入文件: {input_path}")
        print(f"📁 输出文件: {output_path}")
        print(f"⚙️  采样分辨率: {args.resolution}米")
        print(f"⚙️  车道高度: {'是' if args.with_height else '否'}")
        print(f"⚙️  道路对象: {'是' if args.with_objects else '否'}")
        print(f"⚙️  网格精度: {args.eps}米")
        print()
    
    try:
        # 创建转换器
        converter = XODRToOBJConverter(
            resolution=args.resolution,
            with_lane_height=args.with_height,
            with_road_objects=args.with_objects,
            eps=args.eps
        )
        
        if args.verbose:
            print("🔧 转换器已初始化")
            print(f"   - 分辨率: {converter.resolution}m")
            print(f"   - 车道高度: {converter.with_lane_height}")
            print(f"   - 道路对象: {converter.with_road_objects}")
            print(f"   - 网格精度: {converter.eps}m")
            print()
        
        # 执行转换
        if not args.quiet:
            print("🔄 开始转换...")
        
        start_time = time.time()
        success = converter.convert(str(input_path), str(output_path))
        end_time = time.time()
        
        conversion_time = end_time - start_time
        
        if success:
            if not args.quiet:
                print(f"✅ 转换成功！耗时: {conversion_time:.2f}秒")
                
                # 检查输出文件
                if output_path.exists():
                    file_size = output_path.stat().st_size
                    print(f"📊 OBJ文件大小: {file_size:,} 字节")
                    
                    # 检查MTL文件
                    mtl_path = output_path.with_suffix('.mtl')
                    if mtl_path.exists():
                        print(f"📊 MTL文件已生成: {mtl_path.name}")
                    
                    if args.verbose:
                        # 分析OBJ文件内容
                        try:
                            with open(output_path, 'r', encoding='utf-8') as f:
                                lines = f.readlines()
                                vertex_count = sum(1 for line in lines if line.startswith('v '))
                                face_count = sum(1 for line in lines if line.startswith('f '))
                                normal_count = sum(1 for line in lines if line.startswith('vn '))
                                texture_count = sum(1 for line in lines if line.startswith('vt '))
                                
                                print(f"📊 网格统计:")
                                print(f"   - 顶点数: {vertex_count:,}")
                                print(f"   - 面数: {face_count:,}")
                                print(f"   - 法向量数: {normal_count:,}")
                                print(f"   - 纹理坐标数: {texture_count:,}")
                        except Exception as e:
                            if args.verbose:
                                print(f"⚠️  无法分析OBJ文件内容: {e}")
                
                print()
                print("🎉 转换完成！")
                print(f"📁 输出文件: {output_path}")
                if mtl_path.exists():
                    print(f"📁 材质文件: {mtl_path}")
                print()
                print("💡 提示: 可以使用以下软件打开OBJ文件:")
                print("   - Blender (免费开源)")
                print("   - MeshLab (免费开源)")
                print("   - Autodesk Maya")
                print("   - 3ds Max")
                print("   - 或任何支持OBJ格式的3D软件")
            
            sys.exit(0)
        else:
            print("❌ 转换失败！")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  用户中断转换")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 转换过程中发生错误: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()