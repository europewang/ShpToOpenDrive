import os
import logging
from typing import Dict, List, Optional
import json
from pathlib import Path
from shp_reader import ShapefileReader, ShapefileReadingHandler
from geometry_converter import GeometryConverter, GeometryConversionHandler
from opendrive_generator import OpenDriveGenerator, OpenDriveGenerationHandler
import time
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'shp_to_opendrive.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
class ChainOfResponsibilityConverter:
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.conversion_stats = {
            'input_roads': 0,
            'output_roads': 0,
            'conversion_time': 0.0,
            'errors': [],
            'warnings': []
        }
        self._setup_chain()
    def _setup_chain(self):
        self.shapefile_handler = ShapefileReadingHandler(
            coordinate_precision=self.config.get('coordinate_precision', 3)
        )
        self.geometry_handler = GeometryConversionHandler(
            tolerance=self.config.get('geometry_tolerance', 1.0),
            smooth_curves=self.config.get('use_smooth_curves', True),
            preserve_detail=self.config.get('preserve_detail', True),
            curve_fitting_mode=self.config.get('curve_fitting_mode', 'parampoly3'),
            polynomial_degree=self.config.get('polynomial_degree', 3),
            curve_smoothness=self.config.get('curve_smoothness', 0.5),
            coordinate_precision=self.config.get('coordinate_precision', 3)
        )
        self.opendrive_handler = OpenDriveGenerationHandler(
            name=self.config.get('name', 'ConvertedRoad'),
            curve_fitting_mode=self.config.get('curve_fitting_mode', 'polyline'),
            polynomial_degree=self.config.get('polynomial_degree', 3),
            curve_smoothness=self.config.get('curve_smoothness', 0.5)
        )
        self.shapefile_handler.set_next(self.geometry_handler).set_next(self.opendrive_handler)
    def convert(self, shapefile_path: str, output_path: str, attribute_mapping: Dict = None) -> bool:
        try:
            start_time = time.time()
            request = {
                'stage': 'shapefile_loading',
                'shapefile_path': shapefile_path,
                'output_path': output_path,
                'attribute_mapping': attribute_mapping or {},
                'config': self.config
            }
            result = self.shapefile_handler.handle(request)
            self.conversion_stats['conversion_time'] = time.time() - start_time
            if result.get('success', False):
                self.conversion_stats['output_roads'] = len(result.get('road_ids', []))
                logger.info("转换完成！")
                return True
            else:
                error_msg = result.get('error', '未知错误')
                logger.error(f"转换失败: {error_msg}")
                self.conversion_stats['errors'].append(error_msg)
                return False
        except Exception as e:
            logger.error(f"转换过程出错: {e}")
            self.conversion_stats['errors'].append(str(e))
            return False
    def get_conversion_stats(self) -> Dict:
        return self.conversion_stats.copy()
    def save_conversion_report(self, report_path: str):
        try:
            report = {
                'config': self.config,
                'statistics': self.conversion_stats,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(f"转换报告已保存: {report_path}")
        except Exception as e:
            logger.error(f"保存转换报告失败: {e}")
class ShpToOpenDriveConverter:
    def __init__(self, config: Dict = None):
        self.config = {
            'geometry_tolerance': 1.0,      # 几何拟合容差（米）
            'min_road_length': 1.0,        # 最小道路长度（米）
            'default_lane_width': 3.5,      # 默认车道宽度（米）
            'default_num_lanes': 1,         # 默认车道数
            'default_speed_limit': 50,      # 默认限速（km/h）
            'use_arc_fitting': False,       # 是否使用圆弧拟合
            'coordinate_precision': 3,      # 坐标精度（小数位数）
            'use_smooth_curves': True,      # 是否使用平滑曲线拟合
            'preserve_detail': True,        # 是否保留更多细节
            'curve_fitting_mode': 'parampoly3',  # 曲线拟合模式
            'polynomial_degree': 3,         # 多项式拟合阶数
            'curve_smoothness': 0.5,        # 曲线平滑度
            'lane_format_settings': {
                'enabled': True,
                'road_id_field': 'RoadID',
                'index_field': 'Index',
                'auto_detect_lane_format': True,
                'lane_surface_generation': {
                    'enabled': True,
                    'width_interpolation': 'linear',
                    'center_line_calculation': 'midpoint',
                    'width_sampling_points': 50
                },
                'validation': {
                    'check_index_continuity': True,
                    'min_lanes_per_road': 2,
                    'max_width_variation': 10.0
                }
            }
        }
        if config:
            self.config.update(config)
        self.shp_reader = None
        geometry_tolerance = self.config['geometry_tolerance']
        if self.config.get('lane_format_settings', {}).get('enabled', False):
            geometry_tolerance = min(geometry_tolerance, 0.3)
        self.geometry_converter = GeometryConverter(
            tolerance=geometry_tolerance,
            smooth_curves=self.config.get('use_smooth_curves', True),
            preserve_detail=self.config.get('preserve_detail', True),
            curve_fitting_mode=self.config.get('curve_fitting_mode', 'parampoly3'),
            polynomial_degree=self.config.get('polynomial_degree', 3),
            curve_smoothness=self.config.get('curve_smoothness', 0.5),
            coordinate_precision=self.config.get('coordinate_precision', 3)
        )
        self.opendrive_generator = None
        self.conversion_stats = {
            'input_roads': 0,
            'output_roads': 0,
            'total_length': 0,
            'conversion_time': 0,
            'errors': [],
            'warnings': []
        }
    def convert(self, shapefile_path: str, output_path: str, 
               attribute_mapping: Dict = None) -> bool:
        import time
        start_time = time.time()
        try:
            logger.info("开始Shapefile到OpenDrive转换")
            logger.info(f"输入文件: {shapefile_path}")
            logger.info(f"输出文件: {output_path}")
            if not self._load_shapefile(shapefile_path):
                return False
            roads_data = self._extract_roads_data(attribute_mapping)
            if not roads_data:
                logger.error("没有提取到有效的道路数据")
                return False
            converted_roads = self._convert_geometries(roads_data)
            if not converted_roads:
                logger.error("几何转换失败")
                return False
            if not self._generate_opendrive(converted_roads, output_path):
                return False
            self.conversion_stats['conversion_time'] = time.time() - start_time
            self._log_conversion_stats()
            logger.info("转换完成！")
            return True
        except Exception as e:
            logger.error(f"转换过程出错: {e}")
            self.conversion_stats['errors'].append(str(e))
            return False
    def _load_shapefile(self, shapefile_path: str) -> bool:
        try:
            self.shp_reader = ShapefileReader(shapefile_path, self.config.get('coordinate_precision', 3))
            if not self.shp_reader.load_shapefile():
                return False
            if not self.shp_reader.convert_to_utm():
                logger.warning("坐标系转换失败，继续使用原坐标系")
            if not self.shp_reader.convert_to_local_coordinates():
                logger.warning("局部坐标系转换失败，继续使用当前坐标系")
            filtered_count = self.shp_reader.filter_roads_by_length(
                self.config['min_road_length']
            )
            if filtered_count == 0:
                logger.error("过滤后没有剩余道路")
                return False
            road_info = self.shp_reader.get_road_info()
            self.conversion_stats['input_roads'] = road_info['road_count']
            logger.info(f"成功加载 {road_info['road_count']} 条道路")
            return True
        except Exception as e:
            logger.error(f"加载shapefile失败: {e}")
            return False
    def _extract_roads_data(self, attribute_mapping: Dict = None) -> List[Dict]:
        try:
            roads_geometries = self.shp_reader.extract_road_geometries()
            if not roads_geometries:
                return []
            if self._is_lane_format(roads_geometries):
                return self._process_lane_data(roads_geometries, attribute_mapping)
            else:
                return self._process_traditional_data(roads_geometries, attribute_mapping)
        except Exception as e:
            logger.error(f"提取道路数据失败: {e}")
            return []
    def _is_lane_format(self, roads_geometries: List[Dict]) -> bool:
        if not roads_geometries:
            return False
        first_road = roads_geometries[0]
        return all(key in first_road for key in ['road_id', 'lanes', 'lane_surfaces'])
    def _process_lane_data(self, roads_geometries: List[Dict], 
                          attribute_mapping: Dict = None) -> List[Dict]:
        logger.info("处理Lane.shp格式数据")
        roads_data = []
        for road_geom in roads_geometries:
            road_id = road_geom['road_id']
            lanes = road_geom['lanes']  # 现在lanes就是车道面
            lane_surfaces = road_geom['lane_surfaces']  # 与lanes相同
            total_length = 0
            if lanes:
                center_coords = lanes[0].get('center_line', [])
                if center_coords:
                    total_length = self._calculate_line_length(center_coords)
            road_data = {
                'id': road_id,
                'type': 'lane_based',  # 标识为基于车道的道路
                'lanes': lanes,
                'lane_surfaces': lane_surfaces,
                'lane_count': len(lanes),
                'length': total_length,
                'attributes': self._extract_lane_attributes(lanes, attribute_mapping)
            }
            roads_data.append(road_data)
        logger.info(f"处理了 {len(roads_data)} 条基于车道的道路")
        return roads_data
    def _calculate_line_length(self, coords: List[tuple]) -> float:
        import math
        if len(coords) < 2:
            return 0.0
        total_length = 0.0
        for i in range(len(coords) - 1):
            x1, y1 = coords[i]
            x2, y2 = coords[i + 1]
            segment_length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            total_length += segment_length
        return total_length
    def _process_traditional_data(self, roads_geometries: List[Dict], 
                                 attribute_mapping: Dict = None) -> List[Dict]:
        logger.info("处理传统格式道路数据")
        if attribute_mapping is None:
            attribute_mapping = self.shp_reader.get_road_attributes_mapping()
        roads_data = []
        for road_geom in roads_geometries:
            road_data = {
                'id': road_geom['id'],
                'type': 'traditional',  # 标识为传统道路
                'coordinates': road_geom['coordinates'],
                'length': road_geom['length'],
                'attributes': self._map_attributes(
                    road_geom['attributes'], 
                    attribute_mapping
                )
            }
            roads_data.append(road_data)
        logger.info(f"处理了 {len(roads_data)} 条传统道路")
        return roads_data
    def _extract_lane_attributes(self, lanes: List[Dict], 
                                attribute_mapping: Dict = None) -> Dict:
        if not lanes:
            return {}
        first_lane_attrs = lanes[0].get('attributes', {})
        if attribute_mapping:
            return self._map_attributes(first_lane_attrs, attribute_mapping)
        else:
            return first_lane_attrs
    def _map_attributes(self, original_attrs: Dict, mapping: Dict) -> Dict:
        mapped_attrs = {
            'lane_width': self.config['default_lane_width'],
            'num_lanes': self.config['default_num_lanes'],
            'speed_limit': self.config['default_speed_limit'],
            'road_type': 'urban',
            'bidirectional': False
        }
        for original_key, mapped_key in mapping.items():
            if original_key in original_attrs:
                value = original_attrs[original_key]
                if mapped_key == 'lane_width':
                    try:
                        mapped_attrs['lane_width'] = float(value)
                    except (ValueError, TypeError):
                        pass
                elif mapped_key == 'num_lanes':
                    try:
                        mapped_attrs['num_lanes'] = int(value)
                    except (ValueError, TypeError):
                        pass
                elif mapped_key == 'speed_limit':
                    try:
                        mapped_attrs['speed_limit'] = float(value)
                    except (ValueError, TypeError):
                        pass
                else:
                    mapped_attrs[mapped_key] = value
        return mapped_attrs
    def _convert_geometries(self, roads_data: List[Dict]) -> List[Dict]:
        try:
            converted_roads = []
            for road_data in roads_data:
                if road_data.get('type') == 'lane_based':
                    converted_road = self._convert_lane_based_geometry(road_data)
                else:
                    converted_road = self._convert_traditional_geometry(road_data)
                if converted_road:
                    converted_roads.append(converted_road)
                    self.conversion_stats['total_length'] += converted_road['total_length']
            logger.info(f"成功转换 {len(converted_roads)} 条道路的几何")
            return converted_roads
        except Exception as e:
            logger.error(f"几何转换失败: {e}")
            return []
    def _convert_lane_based_geometry(self, road_data: Dict) -> Dict:
        try:
            road_id = road_data['id']
            lane_surfaces = road_data['lane_surfaces']
            converted_surfaces = self.geometry_converter.convert_lane_surface_geometry(lane_surfaces)
            if not converted_surfaces:
                logger.warning(f"道路 {road_id} 车道面几何转换失败")
                return None
            total_length = 0
            if converted_surfaces:
                first_surface = converted_surfaces[0]
                total_length = self.geometry_converter.calculate_road_length(
                    first_surface['center_segments']
                )
            converted_road = {
                'id': road_id,
                'type': 'lane_based',
                'lane_surfaces': converted_surfaces,
                'lanes': road_data['lanes'],
                'lane_count': road_data['lane_count'],
                'attributes': road_data['attributes'],
                'total_length': total_length
            }
            logger.info(f"成功转换基于车道的道路 {road_id}，包含 {len(converted_surfaces)} 个车道面")
            return converted_road
        except Exception as e:
            logger.error(f"Lane格式道路 {road_data.get('id', 'unknown')} 几何转换失败: {e}")
            return None
    def _convert_traditional_geometry(self, road_data: Dict) -> Dict:
        try:
            coordinates = road_data['coordinates']
            if self.config.get('use_smooth_curves', True):
                segments = self.geometry_converter.convert_road_geometry(coordinates)
            elif self.config['use_arc_fitting']:
                segments = self.geometry_converter.fit_arc_segments(coordinates)
            else:
                segments = self.geometry_converter.fit_line_segments(coordinates)
            if not segments:
                logger.warning(f"道路 {road_data['id']} 几何转换失败")
                return None
            if not self.geometry_converter.validate_geometry_continuity(segments):
                logger.warning(f"道路 {road_data['id']} 几何不连续")
                self.conversion_stats['warnings'].append(
                    f"道路 {road_data['id']} 几何不连续"
                )
            total_length = self.geometry_converter.calculate_road_length(segments)
            converted_road = {
                'id': road_data['id'],
                'type': 'traditional',
                'segments': segments,
                'attributes': road_data['attributes'],
                'total_length': total_length
            }
            return converted_road
        except Exception as e:
            logger.error(f"传统格式道路 {road_data.get('id', 'unknown')} 几何转换失败: {e}")
            return None
    def _extract_segments_from_lane_surfaces(self, lane_surfaces: List[Dict]) -> List[Dict]:
        if not lane_surfaces:
            return []
        first_surface = lane_surfaces[0]
        if 'center_segments' in first_surface:
            return first_surface['center_segments']
        logger.warning("车道面缺少center_segments，尝试从边界生成")
        return []
    def _generate_opendrive(self, converted_roads: List[Dict], output_path: str) -> bool:
        try:
            road_network_name = Path(output_path).stem
            self.opendrive_generator = OpenDriveGenerator(
                name=road_network_name,
                curve_fitting_mode=self.config.get('curve_fitting_mode', 'polyline'),
                polynomial_degree=self.config.get('polynomial_degree', 3),
                curve_smoothness=self.config.get('curve_smoothness', 0.5)
            )
            road_ids = []
            for road_data in converted_roads:
                if road_data['type'] == 'lane_based':
                    road_id = self.opendrive_generator.create_road_from_lane_surfaces(
                        road_data['lane_surfaces'],
                        road_data['attributes']
                    )
                else:
                    segments = road_data['segments']
                    road_id = self.opendrive_generator.create_road_from_segments(
                        segments,
                        road_data['attributes']
                    )
                if road_id > 0:
                    road_ids.append(road_id)
            if not road_ids:
                logger.error("没有成功创建任何道路")
                return False
            validation_result = self.opendrive_generator.validate_opendrive()
            if not validation_result['valid']:
                logger.error(f"OpenDrive验证失败: {validation_result['errors']}")
                return False
            if not self.opendrive_generator.generate_file(output_path):
                return False
            self.conversion_stats['output_roads'] = len(road_ids)
            stats = self.opendrive_generator.get_statistics()
            logger.info(f"OpenDrive统计: {stats}")
            return True
        except Exception as e:
            logger.error(f"生成OpenDrive文件失败: {e}")
            return False
    def _log_conversion_stats(self):
        stats = self.conversion_stats
        logger.info("=== 转换统计 ===")
        logger.info(f"输入道路数: {stats['input_roads']}")
        logger.info(f"输出道路数: {stats['output_roads']}")
        logger.info(f"总长度: {stats['total_length']:.2f} 米")
        logger.info(f"转换时间: {stats['conversion_time']:.2f} 秒")
        if stats['warnings']:
            logger.info(f"警告数: {len(stats['warnings'])}")
            for warning in stats['warnings'][:5]:  # 只显示前5个警告
                logger.warning(warning)
        if stats['errors']:
            logger.info(f"错误数: {len(stats['errors'])}")
            for error in stats['errors']:
                logger.error(error)
    def save_conversion_report(self, report_path: str):
        try:
            report = {
                'config': self.config,
                'statistics': self.conversion_stats,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(f"转换报告已保存: {report_path}")
        except Exception as e:
            logger.error(f"保存转换报告失败: {e}")
    
    def get_conversion_stats(self) -> Dict:
        return self.conversion_stats.copy()
def main():
    import argparse
    parser = argparse.ArgumentParser(description='将Shapefile转换为OpenDrive格式')
    parser.add_argument('input', help='输入shapefile路径')
    parser.add_argument('output', help='输出OpenDrive文件路径')
    parser.add_argument('--config', help='配置文件路径（JSON格式）')
    parser.add_argument('--tolerance', type=float, default=1.0, help='几何拟合容差（米）')
    parser.add_argument('--min-length', type=float, default=1.0, help='最小道路长度（米）')
    parser.add_argument('--use-arcs', action='store_true', help='使用圆弧拟合')
    parser.add_argument('--report', help='转换报告输出路径')
    args = parser.parse_args()
    config = {}
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r', encoding='utf-8') as f:
            config = json.load(f)
    config.update({
        'geometry_tolerance': args.tolerance,
        'min_road_length': args.min_length,
        'use_arc_fitting': args.use_arcs
    })
    converter = ChainOfResponsibilityConverter(config)
    success = converter.convert(args.input, args.output)
    if args.report:
        converter.save_conversion_report(args.report)
    if success:
        print("转换成功完成！")
        return 0
    else:
        print("转换失败！")
        return 1
if __name__ == '__main__':
    import sys
    sys.exit(main())