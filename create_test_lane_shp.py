import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString
import os

def create_test_lane_shp():
    """创建简单的Lane.shp测试文件"""
    
    # 创建测试数据
    geometries = []
    road_ids = []
    indices = []
    
    # 道路1: RoadID=1001，包含4条车道边界线（3个车道）
    # 车道边界线从左到右编号为0,1,2,3
    road1_y_base = 100
    road1_lane_width = 3.5
    
    for i in range(4):  # 4条边界线
        y_offset = i * road1_lane_width
        line_coords = [
            (0, road1_y_base + y_offset),
            (50, road1_y_base + y_offset),
            (100, road1_y_base + y_offset)
        ]
        geometries.append(LineString(line_coords))
        road_ids.append(1001)
        indices.append(str(i))
    
    # 道路2: RoadID=1002，包含3条车道边界线（2个车道）
    road2_y_base = 200
    road2_lane_width = 4.0
    
    for i in range(3):  # 3条边界线
        y_offset = i * road2_lane_width
        line_coords = [
            (0, road2_y_base + y_offset),
            (30, road2_y_base + y_offset + 0.5),  # 轻微弯曲
            (60, road2_y_base + y_offset),
            (80, road2_y_base + y_offset)
        ]
        geometries.append(LineString(line_coords))
        road_ids.append(1002)
        indices.append(str(i))
    
    # 道路3: RoadID=1003，包含5条车道边界线（4个车道）
    road3_y_base = 300
    road3_lane_width = 3.0
    
    for i in range(5):  # 5条边界线
        y_offset = i * road3_lane_width
        line_coords = [
            (10, road3_y_base + y_offset),
            (40, road3_y_base + y_offset - 1),  # 向内弯曲
            (70, road3_y_base + y_offset),
            (90, road3_y_base + y_offset + 0.5)
        ]
        geometries.append(LineString(line_coords))
        road_ids.append(1003)
        indices.append(str(i))
    
    # 创建GeoDataFrame
    gdf = gpd.GeoDataFrame({
        'RoadID': road_ids,
        'Index': indices,
        'geometry': geometries
    })
    
    # 设置坐标系（使用UTM坐标系）
    gdf.crs = 'EPSG:32650'  # UTM Zone 50N
    
    # 创建输出目录
    output_dir = 'data/test_lane'
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存为shapefile
    output_path = os.path.join(output_dir, 'TestLane.shp')
    gdf.to_file(output_path)
    
    print(f"成功创建测试Lane.shp文件: {output_path}")
    print(f"包含 {len(gdf)} 条车道边界线记录")
    print(f"道路数量: {len(gdf['RoadID'].unique())}")
    
    # 显示数据统计
    print("\n数据统计:")
    for road_id in sorted(gdf['RoadID'].unique()):
        road_data = gdf[gdf['RoadID'] == road_id]
        indices = sorted(road_data['Index'].tolist(), key=lambda x: int(x))
        print(f"  RoadID {road_id}: {len(road_data)} 条边界线, Index范围: {indices}")
    
    return output_path

if __name__ == "__main__":
    try:
        shp_path = create_test_lane_shp()
        print(f"\n测试文件创建完成: {shp_path}")
    except Exception as e:
        print(f"创建测试文件失败: {e}")
        import traceback
        traceback.print_exc()