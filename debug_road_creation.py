import sys
sys.path.append('src')
from shp_reader import ShapefileReader
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('road_creation_debug.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

try:
    # 创建ShapefileReader实例
    reader = ShapefileReader('e:/Code/ShpToOpenDrive/data/testODsample/wh2000/Lane.shp')
    
    logger.info("开始调试道路创建过程...")
    
    # 先加载shapefile
    if not reader.load_shapefile():
        logger.error("无法加载shapefile文件")
        exit(1)
    
    # 提取几何数据（只处理前3个RoadID）
    roads = reader.extract_lane_geometries()
    
    logger.info(f"\n=== 道路创建结果总结 ===")
    logger.info(f"总共创建了 {len(roads)} 条道路")
    
    # 详细分析前3条道路
    for i, road in enumerate(roads[:3]):
        logger.info(f"\n--- 道路 {i+1} 详细信息 ---")
        logger.info(f"RoadID: {road['road_id']}")
        logger.info(f"车道数量: {road['lane_count']}")
        logger.info(f"车道面数量: {len(road['lane_surfaces'])}")
        
        # 显示车道面信息
        for j, surface in enumerate(road['lane_surfaces']):
            logger.info(f"  车道面 {j+1}: surface_id={surface['surface_id']}, 中心线点数={len(surface['center_line'])}, 宽度变化点数={len(surface['width_variations'])}")
        
        # 显示车道边界信息
        logger.info(f"车道边界信息:")
        for j, lane in enumerate(road['lanes']):
            logger.info(f"  车道 {j+1}: left_boundary_index={lane.get('left_boundary_index', 'N/A')}, right_boundary_index={lane.get('right_boundary_index', 'N/A')}")
    
except Exception as e:
    logger.error(f"调试过程中发生错误: {e}")
    import traceback
    logger.error(traceback.format_exc())

logger.info("调试完成，详细日志已保存到 road_creation_debug.log")