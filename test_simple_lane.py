import sys
sys.path.append('src')
from shp_reader import ShapefileReader
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_simple_lane_processing():
    """测试简单Lane.shp文件的处理流程"""
    
    test_file = 'data/test_lane/TestLane.shp'
    
    print("=== 测试简单Lane.shp处理流程 ===")
    print(f"测试文件: {test_file}")
    
    try:
        # 1. 创建ShapefileReader实例
        reader = ShapefileReader(test_file)
        print("✓ ShapefileReader实例创建成功")
        
        # 2. 加载shapefile
        if not reader.load_shapefile():
            print("✗ 加载shapefile失败")
            return False
        print("✓ Shapefile加载成功")
        
        # 3. 检查数据基本信息
        print(f"\n数据基本信息:")
        print(f"  总记录数: {len(reader.gdf)}")
        print(f"  列名: {list(reader.gdf.columns)}")
        print(f"  坐标系: {reader.gdf.crs}")
        
        # 4. 检查RoadID分组
        road_ids = reader.gdf['RoadID'].unique()
        print(f"\nRoadID分组:")
        print(f"  唯一RoadID: {sorted(road_ids)}")
        
        for road_id in sorted(road_ids):
            group = reader.gdf[reader.gdf['RoadID'] == road_id]
            indices = group['Index'].tolist()
            print(f"  RoadID {road_id}: {len(group)} 条边界线, Index={indices}")
        
        # 5. 测试Lane格式检测
        is_lane_format = reader._is_lane_shapefile()
        print(f"\nLane格式检测: {is_lane_format}")
        
        if not is_lane_format:
            print("✗ 未检测到Lane格式")
            return False
        
        # 6. 提取车道几何数据
        print("\n开始提取车道几何数据...")
        roads = reader.extract_lane_geometries()
        
        if not roads:
            print("✗ 未提取到任何道路数据")
            return False
        
        print(f"✓ 成功提取 {len(roads)} 条道路")
        
        # 7. 分析提取结果
        print("\n提取结果分析:")
        for i, road in enumerate(roads):
            print(f"\n--- 道路 {i+1} ---")
            print(f"  RoadID: {road['road_id']}")
            print(f"  车道数量: {road['lane_count']}")
            print(f"  车道面数量: {len(road['lane_surfaces'])}")
            
            # 显示车道面详情
            for j, surface in enumerate(road['lane_surfaces']):
                # 检查车道面数据结构
                surface_id = surface.get('surface_id', 'N/A')
                left_boundary = surface.get('left_boundary', {})
                right_boundary = surface.get('right_boundary', {})
                
                left_coords = len(left_boundary.get('coordinates', []))
                right_coords = len(right_boundary.get('coordinates', []))
                
                print(f"    车道面 {j+1}: surface_id={surface_id}, 左边界点数={left_coords}, 右边界点数={right_coords}")
        
        print("\n✓ 所有测试通过！")
        return True
        
    except Exception as e:
        print(f"\n✗ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_simple_lane_processing()
    if success:
        print("\n🎉 简单Lane.shp处理测试成功！")
    else:
        print("\n❌ 简单Lane.shp处理测试失败！")