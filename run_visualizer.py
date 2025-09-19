#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3D可视化器启动脚本

这个脚本提供了一个简单的方式来启动ShpToOpenDrive的3D可视化功能。

使用方法:
    python run_visualizer.py

作者: ShpToOpenDrive项目组
版本: 1.0.0
"""

import sys
import os
from pathlib import Path

# 添加src目录到Python路径
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def main():
    """
    主函数 - 启动3D可视化器
    """
    try:
        print("正在启动ShpToOpenDrive 3D可视化器...")
        print("="*50)
        print("功能特性:")
        print("- 支持SHP和OpenDRIVE文件导入")
        print("- 实时3D渲染和交互")
        print("- 多种格式导出(PLY, OBJ, STL, PCD)")
        print("- 道路统计信息显示")
        print("="*50)
        
        # 导入并启动可视化器
        from visualizer import RoadVisualizer
        
        # 创建可视化器实例
        visualizer = RoadVisualizer()
        
        print("可视化器已启动，请在GUI界面中操作...")
        
        # 可选：自动加载默认SHP文件
        # default_shp = "data/CenterLane.shp"
        # if os.path.exists(default_shp):
        #     print(f"自动加载测试文件: {default_shp}")
        #     try:
        #         from shp_reader import ShapefileReader
        #         reader = ShapefileReader(default_shp)
        #         visualizer.current_shp_data = reader.read_features()
        #         print(f"成功加载 {len(visualizer.current_shp_data)} 个道路特征")
        #     except Exception as e:
        #         print(f"自动加载失败: {e}")
        
        # 运行可视化器
        visualizer.run()
        
    except ImportError as e:
        print(f"导入错误: {str(e)}")
        print("请确保已安装所有必要的依赖包:")
        print("pip install -r requirements.txt")
        sys.exit(1)
        
    except Exception as e:
        print(f"启动失败: {str(e)}")
        print("请检查环境配置和依赖包安装")
        sys.exit(1)

if __name__ == "__main__":
    main()