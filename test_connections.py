import logging
import sys
sys.path.append('src')
from geometry_converter import RoadConnectionManager
from shp_reader import ShapefileReader

# 设置日志级别
logging.basicConfig(level=logging.INFO)

# 读取测试数据
shapefile_path = 'data/testODsample/LaneTest.shp'
reader = ShapefileReader(shapefile_path)
roads = reader.read_features()

# 提取所有车道面
all_lane_surfaces = []
for road in roads:
    if 'lane_surfaces' in road:
        all_lane_surfaces.extend(road['lane_surfaces'])

print(f'总车道面数量: {len(all_lane_surfaces)}')

# 创建连接管理器
connection_manager = RoadConnectionManager()

# 添加所有道路面
for surface in all_lane_surfaces:
    left_coords = surface['left_boundary']['coordinates']
    right_coords = surface['right_boundary']['coordinates']
    center_coords, width_data = connection_manager._calculate_center_line(left_coords, right_coords)
    
    attributes = surface.get('attributes', {})
    s_node_id = attributes.get('SNodeID') or attributes.get('s_node_id')
    e_node_id = attributes.get('ENodeID') or attributes.get('e_node_id')
    
    print(f'表面 {surface["surface_id"]}: SNodeID={s_node_id}, ENodeID={e_node_id}')
    
    surface_data = {
        'surface_id': surface['surface_id'],
        'attributes': {'SNodeID': s_node_id, 'ENodeID': e_node_id},
        'center_line': center_coords
    }
    
    start_heading = connection_manager._calculate_heading(center_coords[0], center_coords[1]) if len(center_coords) > 1 else None
    end_heading = connection_manager._calculate_heading(center_coords[-2], center_coords[-1]) if len(center_coords) > 1 else None
    
    connection_manager.add_road_surface(surface_data, start_heading=start_heading, end_heading=end_heading)

print(f'添加到连接管理器的道路面数量: {len(connection_manager.road_surfaces)}')

# 构建连接关系
connection_manager.build_connections()

print(f'节点连接数量: {len(connection_manager.node_connections)}')
print(f'前继映射数量: {len(connection_manager.predecessor_map)}')
print(f'后继映射数量: {len(connection_manager.successor_map)}')

# 检查哪些道路面被跳过了
skipped_surfaces = []
for surface_id, surface_info in connection_manager.road_surfaces.items():
    s_node = surface_info['s_node_id']
    e_node = surface_info['e_node_id']
    
    if s_node is None or e_node is None:
        skipped_surfaces.append(surface_id)
        print(f'道路面 {surface_id} 被跳过: SNodeID={s_node}, ENodeID={e_node}')

print(f'被跳过的道路面数量: {len(skipped_surfaces)}')

# 检查节点连接详情
for node_id, connections in connection_manager.node_connections.items():
    incoming_count = len(connections.get("incoming", []))
    outgoing_count = len(connections.get("outgoing", []))
    print(f'节点 {node_id}: incoming={incoming_count}, outgoing={outgoing_count}')