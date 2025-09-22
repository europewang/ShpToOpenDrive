import xml.etree.ElementTree as ET
import os
import sys
from typing import Dict, List, Tuple

def validate_xodr_file(xodr_path: str) -> Dict:
    """验证OpenDrive文件格式正确性
    
    Args:
        xodr_path: .xodr文件路径
        
    Returns:
        Dict: 验证结果
    """
    result = {
        'valid': False,
        'errors': [],
        'warnings': [],
        'info': {},
        'statistics': {}
    }
    
    try:
        # 1. 检查文件是否存在
        if not os.path.exists(xodr_path):
            result['errors'].append(f"文件不存在: {xodr_path}")
            return result
        
        # 2. 检查文件大小
        file_size = os.path.getsize(xodr_path)
        if file_size == 0:
            result['errors'].append("文件为空")
            return result
        
        result['info']['file_size'] = file_size
        
        # 3. 解析XML
        try:
            tree = ET.parse(xodr_path)
            root = tree.getroot()
        except ET.ParseError as e:
            result['errors'].append(f"XML解析错误: {e}")
            return result
        
        # 4. 验证根元素
        if root.tag != 'OpenDRIVE':
            result['errors'].append(f"根元素应为'OpenDRIVE'，实际为'{root.tag}'")
            return result
        
        # 5. 验证header元素
        header = root.find('header')
        if header is None:
            result['errors'].append("缺少header元素")
            result['info']['version'] = "N/A.N/A"
        else:
            # 验证header必需属性
            required_header_attrs = ['revMajor', 'revMinor', 'name']
            for attr in required_header_attrs:
                if attr not in header.attrib:
                    result['errors'].append(f"header缺少必需属性: {attr}")
            
            # 验证header推荐属性
            recommended_attrs = ['version', 'date']
            missing_recommended = [attr for attr in recommended_attrs if attr not in header.attrib]
            if missing_recommended:
                result['warnings'].append(f"header缺少推荐属性: {', '.join(missing_recommended)}")
            
            result['info']['version'] = f"{header.get('revMajor', 'N/A')}.{header.get('revMinor', 'N/A')}"
            result['info']['header'] = dict(header.attrib)
        
        # 7. 验证road元素
        roads = root.findall('road')
        if not roads:
            result['warnings'].append("没有找到road元素")
        
        result['statistics']['road_count'] = len(roads)
        
        # 验证每条道路
        total_length = 0
        geometry_types = {}
        lane_count = 0
        
        for i, road in enumerate(roads):
            road_id = road.get('id', f'road_{i}')
            
            # 验证road属性
            required_road_attrs = ['id', 'length']
            for attr in required_road_attrs:
                if attr not in road.attrib:
                    result['errors'].append(f"道路{road_id}缺少必需属性: {attr}")
            
            # 累计长度
            try:
                road_length = float(road.get('length', 0))
                total_length += road_length
            except ValueError:
                result['warnings'].append(f"道路{road_id}长度格式错误")
            
            # 验证planView
            plan_view = road.find('planView')
            if plan_view is None:
                result['errors'].append(f"道路{road_id}缺少planView元素")
            else:
                geometries = plan_view.findall('geometry')
                for geom in geometries:
                    geom_type = None
                    for child in geom:
                        if child.tag in ['line', 'arc', 'spiral', 'poly3', 'paramPoly3']:
                            geom_type = child.tag
                            break
                    
                    if geom_type:
                        geometry_types[geom_type] = geometry_types.get(geom_type, 0) + 1
                    else:
                        result['warnings'].append(f"道路{road_id}包含未知几何类型")
            
            # 验证lanes
            lanes = road.find('lanes')
            if lanes is None:
                result['warnings'].append(f"道路{road_id}缺少lanes元素")
            else:
                # 统计车道数
                lane_sections = lanes.findall('laneSection')
                for section in lane_sections:
                    left_lanes = section.find('left')
                    right_lanes = section.find('right')
                    center_lane = section.find('center')
                    
                    if left_lanes is not None:
                        lane_count += len(left_lanes.findall('lane'))
                    if right_lanes is not None:
                        lane_count += len(right_lanes.findall('lane'))
                    if center_lane is not None:
                        lane_count += len(center_lane.findall('lane'))
        
        result['statistics']['total_length'] = total_length
        result['statistics']['geometry_types'] = geometry_types
        result['statistics']['lane_count'] = lane_count
        
        # 8. 检查是否有错误
        if not result['errors']:
            result['valid'] = True
        
        return result
        
    except Exception as e:
        result['errors'].append(f"验证过程中发生异常: {e}")
        return result

def print_validation_result(result: Dict, file_path: str):
    """打印验证结果"""
    print(f"\n=== OpenDrive文件验证结果: {os.path.basename(file_path)} ===")
    
    if result['valid']:
        print("✓ 文件格式验证通过")
    else:
        print("✗ 文件格式验证失败")
    
    # 打印错误
    if result['errors']:
        print("\n❌ 错误:")
        for error in result['errors']:
            print(f"  - {error}")
    
    # 打印警告
    if result['warnings']:
        print("\n⚠️ 警告:")
        for warning in result['warnings']:
            print(f"  - {warning}")
    
    # 打印基本信息
    if result['info']:
        print("\n📋 基本信息:")
        for key, value in result['info'].items():
            if key == 'file_size':
                print(f"  文件大小: {value} 字节")
            elif key == 'version':
                print(f"  OpenDrive版本: {value}")
            elif key == 'header':
                print(f"  Header信息:")
                for h_key, h_value in value.items():
                    print(f"    {h_key}: {h_value}")
    
    # 打印统计信息
    if result['statistics']:
        print("\n📊 统计信息:")
        stats = result['statistics']
        if 'road_count' in stats:
            print(f"  道路数量: {stats['road_count']}")
        if 'total_length' in stats:
            print(f"  总长度: {stats['total_length']:.2f} 米")
        if 'lane_count' in stats:
            print(f"  车道数量: {stats['lane_count']}")
        if 'geometry_types' in stats and stats['geometry_types']:
            print(f"  几何类型分布:")
            for geom_type, count in stats['geometry_types'].items():
                print(f"    {geom_type}: {count}")

def validate_multiple_files():
    """验证多个生成的文件"""
    print("=== 批量验证OpenDrive文件 ===")
    
    # 要验证的文件列表
    files_to_validate = [
        'E:/Code/ShpToOpenDrive/output/full_test_output.xodr',
        'E:/Code/ShpToOpenDrive/output/test_默认配置.xodr',
        'E:/Code/ShpToOpenDrive/output/test_Lane格式配置.xodr',
        'E:/Code/ShpToOpenDrive/test_lane_output.xodr'
    ]
    
    valid_files = 0
    total_files = 0
    
    for file_path in files_to_validate:
        if os.path.exists(file_path):
            total_files += 1
            result = validate_xodr_file(file_path)
            print_validation_result(result, file_path)
            
            if result['valid']:
                valid_files += 1
        else:
            print(f"\n⚠️ 文件不存在: {os.path.basename(file_path)}")
    
    print(f"\n=== 验证总结 ===")
    print(f"总文件数: {total_files}")
    print(f"有效文件数: {valid_files}")
    print(f"验证通过率: {(valid_files/total_files*100) if total_files > 0 else 0:.1f}%")
    
    return valid_files == total_files

def check_opendrive_compliance(xodr_path: str):
    """检查OpenDrive标准合规性"""
    print(f"\n=== OpenDrive标准合规性检查: {os.path.basename(xodr_path)} ===")
    
    if not os.path.exists(xodr_path):
        print("✗ 文件不存在")
        return False
    
    try:
        tree = ET.parse(xodr_path)
        root = tree.getroot()
        
        compliance_issues = []
        
        # 检查版本兼容性
        rev_major = root.get('revMajor')
        rev_minor = root.get('revMinor')
        
        if rev_major and rev_minor:
            version = f"{rev_major}.{rev_minor}"
            print(f"OpenDrive版本: {version}")
            
            # 检查是否为支持的版本
            supported_versions = ['1.4', '1.5', '1.6', '1.7']
            if version not in supported_versions:
                compliance_issues.append(f"版本{version}可能不被广泛支持")
        
        # 检查坐标系统
        header = root.find('header')
        if header is not None:
            geo_ref = header.find('geoReference')
            if geo_ref is None:
                compliance_issues.append("缺少地理参考信息(geoReference)")
        
        # 检查道路连接性
        roads = root.findall('road')
        road_ids = [road.get('id') for road in roads]
        
        # 检查junction元素
        junctions = root.findall('junction')
        if len(roads) > 1 and not junctions:
            compliance_issues.append("多条道路但缺少junction连接信息")
        
        if compliance_issues:
            print("⚠️ 合规性问题:")
            for issue in compliance_issues:
                print(f"  - {issue}")
        else:
            print("✓ 基本合规性检查通过")
        
        return len(compliance_issues) == 0
        
    except Exception as e:
        print(f"✗ 合规性检查失败: {e}")
        return False

if __name__ == "__main__":
    # 验证所有生成的文件
    all_valid = validate_multiple_files()
    
    # 对主要输出文件进行合规性检查
    main_output = 'E:/Code/ShpToOpenDrive/output/test_Lane格式配置.xodr'
    if os.path.exists(main_output):
        check_opendrive_compliance(main_output)
    
    if all_valid:
        print("\n🎉 所有文件验证通过！")
    else:
        print("\n❌ 部分文件验证失败！")