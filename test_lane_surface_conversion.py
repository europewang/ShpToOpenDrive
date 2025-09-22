import sys
sys.path.append('src')
from shp_reader import ShapefileReader
from geometry_converter import GeometryConverter
from opendrive_generator import OpenDriveGenerator
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_lane_surface_conversion():
    """测试车道面构建和几何转换逻辑"""
    print("=== 测试车道面构建和几何转换 ===")
    
    try:
        # 1. 加载测试Lane.shp文件
        print("\n1. 加载测试Lane.shp文件...")
        reader = ShapefileReader('E:/Code/ShpToOpenDrive/data/test_lane/TestLane.shp')
        
        if not reader.load_shapefile():
            print("✗ 无法加载shapefile文件")
            return False
        
        print("✓ 成功加载shapefile文件")
        
        # 2. 提取车道几何数据
        print("\n2. 提取车道几何数据...")
        roads = reader.extract_lane_geometries()
        
        if not roads:
            print("✗ 未提取到任何道路数据")
            return False
        
        print(f"✓ 成功提取 {len(roads)} 条道路")
        
        # 3. 测试几何转换器
        print("\n3. 测试几何转换器...")
        converter = GeometryConverter(tolerance=0.5)
        
        # 取第一条道路进行详细测试
        first_road = roads[0]
        lane_surfaces = first_road['lane_surfaces']
        
        print(f"测试道路 {first_road['road_id']}，包含 {len(lane_surfaces)} 个车道面")
        
        # 4. 转换车道面几何
        print("\n4. 转换车道面几何...")
        converted_surfaces = converter.convert_lane_surface_geometry(lane_surfaces)
        
        if not converted_surfaces:
            print("✗ 车道面几何转换失败")
            return False
        
        print(f"✓ 成功转换 {len(converted_surfaces)} 个车道面")
        
        # 5. 分析转换结果
        print("\n5. 分析转换结果...")
        for i, surface in enumerate(converted_surfaces):
            surface_id = surface['surface_id']
            center_segments = surface.get('center_segments', [])
            width_profile = surface.get('width_profile', [])
            
            print(f"  车道面 {i+1} ({surface_id}):")
            print(f"    中心线几何段数量: {len(center_segments)}")
            print(f"    宽度变化点数量: {len(width_profile)}")
            
            if width_profile:
                start_width = width_profile[0]['width']
                end_width = width_profile[-1]['width']
                print(f"    起始宽度: {start_width:.2f}m")
                print(f"    结束宽度: {end_width:.2f}m")
        
        # 6. 测试OpenDrive生成
        print("\n6. 测试OpenDrive生成...")
        generator = OpenDriveGenerator("TestRoad")
        
        # 从车道面提取几何段（简化处理）
        segments = []
        if converted_surfaces:
            first_surface = converted_surfaces[0]
            center_segments = first_surface.get('center_segments', [])
            segments = center_segments
        
        # 构建道路属性
        road_attributes = {
            'num_lanes': first_road['lane_count'],
            'lane_width': 3.5,
            'speed_limit': 50
        }
        
        # 创建道路
        road_id = generator.create_road_from_segments(segments, road_attributes)
        
        if road_id > 0:
            print(f"✓ 成功创建道路，ID: {road_id}")
            
            # 验证OpenDrive数据
            validation_result = generator.validate_opendrive()
            if validation_result['valid']:
                print("✓ OpenDrive数据验证通过")
            else:
                print(f"⚠ OpenDrive数据验证警告: {validation_result['warnings']}")
            
            # 生成文件
            output_file = 'test_lane_output.xodr'
            if generator.generate_file(output_file):
                print(f"✓ OpenDrive文件已保存到: {output_file}")
                return True
            else:
                print("✗ OpenDrive文件生成失败")
                return False
        else:
            print("✗ 道路创建失败")
            return False
        
    except Exception as e:
        print(f"\n✗ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_lane_surface_conversion()
    if success:
        print("\n🎉 车道面构建和几何转换测试成功！")
    else:
        print("\n❌ 车道面构建和几何转换测试失败！")