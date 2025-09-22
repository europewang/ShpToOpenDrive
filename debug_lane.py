#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试Lane.shp处理逻辑
"""

import os
import sys
import logging

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from shp_reader import ShapefileReader

# 配置日志 - 输出到文件
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug_output.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def debug_lane_processing():
    """调试Lane.shp处理过程"""
    print("开始调试Lane.shp处理逻辑")
    print("=" * 50)
    
    lane_shp_path = "e:\\Code\\ShpToOpenDrive\\data\\testODsample\\wh2000\\Lane.shp"
    
    if not os.path.exists(lane_shp_path):
        print(f"错误：Lane.shp文件不存在 {lane_shp_path}")
        return
    
    try:
        # 创建shapefile读取器
        reader = ShapefileReader(lane_shp_path)
        
        # 加载shapefile
        success = reader.load_shapefile()
        if not success:
            print("错误：无法加载Lane.shp文件")
            return
        
        print(f"成功加载Lane.shp文件，包含 {len(reader.gdf)} 条记录")
        
        # 检查前几条记录的RoadID和Index
        print("\n前10条记录的RoadID和Index:")
        for i in range(min(10, len(reader.gdf))):
            row = reader.gdf.iloc[i]
            print(f"  记录{i}: RoadID={row['RoadID']}, Index={row['Index']}")
        
        # 提取Lane几何数据（只处理前3个RoadID）
        print("\n开始提取车道数据...")
        roads_geometries = reader.extract_lane_geometries()
        
        print(f"\n提取完成，共 {len(roads_geometries)} 条道路")
        
        # 显示前3条道路的详细信息
        for i, road in enumerate(roads_geometries[:3]):
            print(f"\n道路 {i+1}:")
            print(f"  RoadID: {road['road_id']}")
            print(f"  车道数量: {len(road['lanes'])}")
            print(f"  车道面数量: {len(road['lane_surfaces'])}")
            
            if road['lanes']:
                print(f"  车道面IDs: {[lane['surface_id'] for lane in road['lanes']]}")
        
    except Exception as e:
        print(f"调试失败: {e}")
        logger.exception("调试异常")

if __name__ == "__main__":
    debug_lane_processing()