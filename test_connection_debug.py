import sys
sys.path.append('src')
import geopandas as gpd
from shp_reader import ShapefileReader
from geometry_converter import RoadConnectionManager

# 读取shapefile数据
reader = ShapefileReader('data/testODsample/LaneTest.shp')
reader.load_shapefile()
reader.convert_to_utm()
roads_data = reader.extract_road_geometries()

print(f'读取到 {len(roads_data)} 条道路')
if roads_data:
    print(f'第一条道路的键: {list(roads_data[0].keys())}')
    # 检查是否为lane格式
    first_road = roads_data[0]
    is_lane_format = all(key in first_road for key in ['road_id', 'lanes', 'lane_surfaces'])
    print(f'是否为Lane格式: {is_lane_format}')

print('\n=== 前两条道路的详细信息 ===')
for i, road in enumerate(roads_data[:2]):
    road_id = road.get('id', road.get('road_id', 'N/A'))
    # 检查是否为lane格式
    is_lane_format = all(key in road for key in ['road_id', 'lanes', 'lane_surfaces'])
    road_type = 'lane_based' if is_lane_format else 'unknown'
    print(f'Road {i}: ID={road_id}, Type={road_type}')
    
    # 如果是lane格式，显示车道面信息
    if is_lane_format and 'lane_surfaces' in road:
        lane_surfaces = road['lane_surfaces']
        print(f'  包含 {len(lane_surfaces)} 个车道面')
        for j, surface in enumerate(lane_surfaces[:2]):  # 只显示前两个车道面
            attrs = surface.get('attributes', {})
            print(f'    车道面 {j}: surface_id={surface.get("surface_id", "N/A")}')
            print(f'      SNodeID={attrs.get("SNodeID", "N/A")}, ENodeID={attrs.get("ENodeID", "N/A")}')
            print(f'      RoadID={attrs.get("RoadID", "N/A")}, LaneID={attrs.get("LaneID", "N/A")}')
    print()

# 测试RoadConnectionManager
print('\n=== 测试RoadConnectionManager ===')
connection_manager = RoadConnectionManager()

# 添加道路面数据
for road_idx, road in enumerate(roads_data):
    # 检查是否为lane格式
    is_lane_format = all(key in road for key in ['road_id', 'lanes', 'lane_surfaces'])
    if is_lane_format:
        road_id = road.get('road_id', f'road_{road_idx}')
        print(f'处理lane_based道路 {road_id}，包含 {len(road["lane_surfaces"])} 个车道面')
        for surface_idx, surface in enumerate(road['lane_surfaces']):
            # 从surface的attributes中获取SNodeID和ENodeID
            attrs = surface.get('attributes', {})
            # 生成唯一的surface_id
            unique_surface_id = f"{road_id}_{surface['surface_id']}"
            surface_data = {
                'surface_id': unique_surface_id,
                'attributes': {
                    'SNodeID': attrs.get('SNodeID'),
                    'ENodeID': attrs.get('ENodeID')
                }
            }
            connection_manager.add_road_surface(surface_data)
            print(f'添加道路面: {unique_surface_id}, SNodeID={attrs.get("SNodeID")}, ENodeID={attrs.get("ENodeID")}')
    else:
        print(f'跳过非lane_based道路: unknown')

# 构建连接关系
print('\n开始构建连接关系...')
connection_manager.build_connections()

# 获取连接信息
connection_info = connection_manager.get_connection_info()
print(f'\n=== 连接关系统计 ===')
print(f'总道路面数: {connection_info["total_surfaces"]}')
print(f'有前继的道路面数: {connection_info["surfaces_with_predecessors"]}')
print(f'有后继的道路面数: {connection_info["surfaces_with_successors"]}')
print(f'总节点数: {connection_info["total_nodes"]}')

print(f'\n前继关系: {connection_info["predecessor_map"]}')
print(f'后继关系: {connection_info["successor_map"]}')