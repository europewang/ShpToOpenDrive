#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主程序转换器测试

测试ShpToOpenDriveConverter类的功能。
"""

import unittest
import tempfile
import os
import json
import sys
from unittest.mock import Mock, patch, MagicMock

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import ShpToOpenDriveConverter


class TestShpToOpenDriveConverter(unittest.TestCase):
    """主转换器测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.converter = ShpToOpenDriveConverter()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init_default_config(self):
        """测试默认配置初始化"""
        converter = ShpToOpenDriveConverter()
        
        # 检查默认配置
        self.assertEqual(converter.config['geometry_tolerance'], 1.0)
        self.assertEqual(converter.config['min_road_length'], 10.0)
        self.assertEqual(converter.config['default_lane_width'], 3.5)
        self.assertEqual(converter.config['default_num_lanes'], 1)
        self.assertEqual(converter.config['default_speed_limit'], 50)
        self.assertFalse(converter.config['use_arc_fitting'])
        self.assertEqual(converter.config['coordinate_precision'], 3)
    
    def test_init_custom_config(self):
        """测试自定义配置初始化"""
        custom_config = {
            'geometry_tolerance': 0.5,
            'default_lane_width': 4.0,
            'use_arc_fitting': True
        }
        
        converter = ShpToOpenDriveConverter(custom_config)
        
        # 检查自定义配置
        self.assertEqual(converter.config['geometry_tolerance'], 0.5)
        self.assertEqual(converter.config['default_lane_width'], 4.0)
        self.assertTrue(converter.config['use_arc_fitting'])
        
        # 检查未修改的默认值
        self.assertEqual(converter.config['min_road_length'], 10.0)
    
    def test_map_attributes_default(self):
        """测试默认属性映射"""
        original_attrs = {'some_field': 'some_value'}
        mapping = {}
        
        mapped_attrs = self.converter._map_attributes(original_attrs, mapping)
        
        # 检查默认属性
        self.assertEqual(mapped_attrs['lane_width'], 3.5)
        self.assertEqual(mapped_attrs['num_lanes'], 1)
        self.assertEqual(mapped_attrs['speed_limit'], 50)
        self.assertEqual(mapped_attrs['road_type'], 'urban')
        self.assertFalse(mapped_attrs['bidirectional'])
    
    def test_map_attributes_custom(self):
        """测试自定义属性映射"""
        original_attrs = {
            'WIDTH': '4.0',
            'LANES': '2',
            'SPEED': '60',
            'TYPE': 'highway'
        }
        
        mapping = {
            'WIDTH': 'lane_width',
            'LANES': 'num_lanes',
            'SPEED': 'speed_limit',
            'TYPE': 'road_type'
        }
        
        mapped_attrs = self.converter._map_attributes(original_attrs, mapping)
        
        # 检查映射结果
        self.assertEqual(mapped_attrs['lane_width'], 4.0)
        self.assertEqual(mapped_attrs['num_lanes'], 2)
        self.assertEqual(mapped_attrs['speed_limit'], 60.0)
        self.assertEqual(mapped_attrs['road_type'], 'highway')
    
    def test_map_attributes_invalid_values(self):
        """测试无效值的属性映射"""
        original_attrs = {
            'WIDTH': 'invalid',
            'LANES': 'not_a_number',
            'SPEED': None
        }
        
        mapping = {
            'WIDTH': 'lane_width',
            'LANES': 'num_lanes',
            'SPEED': 'speed_limit'
        }
        
        mapped_attrs = self.converter._map_attributes(original_attrs, mapping)
        
        # 应该使用默认值
        self.assertEqual(mapped_attrs['lane_width'], 3.5)
        self.assertEqual(mapped_attrs['num_lanes'], 1)
        self.assertEqual(mapped_attrs['speed_limit'], 50)
    
    def test_get_conversion_stats(self):
        """测试获取转换统计"""
        stats = self.converter.get_conversion_stats()
        
        # 检查统计字段
        self.assertIn('input_roads', stats)
        self.assertIn('output_roads', stats)
        self.assertIn('total_length', stats)
        self.assertIn('conversion_time', stats)
        self.assertIn('errors', stats)
        self.assertIn('warnings', stats)
        
        # 检查初始值
        self.assertEqual(stats['input_roads'], 0)
        self.assertEqual(stats['output_roads'], 0)
        self.assertEqual(stats['total_length'], 0)
        self.assertEqual(stats['conversion_time'], 0)
        self.assertEqual(len(stats['errors']), 0)
        self.assertEqual(len(stats['warnings']), 0)
    
    def test_save_conversion_report(self):
        """测试保存转换报告"""
        report_path = os.path.join(self.temp_dir, 'test_report.json')
        
        # 设置一些统计数据
        self.converter.conversion_stats['input_roads'] = 5
        self.converter.conversion_stats['output_roads'] = 4
        
        # 保存报告
        self.converter.save_conversion_report(report_path)
        
        # 验证文件存在
        self.assertTrue(os.path.exists(report_path))
        
        # 验证内容
        with open(report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        self.assertIn('config', report)
        self.assertIn('statistics', report)
        self.assertIn('timestamp', report)
        self.assertEqual(report['statistics']['input_roads'], 5)
        self.assertEqual(report['statistics']['output_roads'], 4)
    
    @patch('main.ShapefileReader')
    @patch('main.OpenDriveGenerator')
    def test_convert_success_flow(self, mock_opendrive_gen, mock_shp_reader):
        """测试成功转换流程"""
        # 模拟shapefile读取器
        mock_reader_instance = Mock()
        mock_reader_instance.load_shapefile.return_value = True
        mock_reader_instance.convert_to_utm.return_value = True
        mock_reader_instance.filter_roads_by_length.return_value = 2
        mock_reader_instance.get_road_info.return_value = {'road_count': 2}
        mock_reader_instance.extract_road_geometries.return_value = [
            {
                'id': 1,
                'coordinates': [[0, 0], [10, 0]],
                'length': 10.0,
                'attributes': {}
            },
            {
                'id': 2,
                'coordinates': [[10, 0], [20, 10]],
                'length': 14.14,
                'attributes': {}
            }
        ]
        mock_reader_instance.get_road_attributes_mapping.return_value = {}
        mock_shp_reader.return_value = mock_reader_instance
        
        # 模拟OpenDrive生成器
        mock_generator_instance = Mock()
        mock_generator_instance.create_road_from_segments.return_value = 1
        mock_generator_instance.validate_opendrive.return_value = {'valid': True, 'errors': []}
        mock_generator_instance.generate_file.return_value = True
        mock_generator_instance.get_statistics.return_value = {'roads': 2}
        mock_opendrive_gen.return_value = mock_generator_instance
        
        # 执行转换
        input_path = "test_input.shp"
        output_path = os.path.join(self.temp_dir, "test_output.xodr")
        
        success = self.converter.convert(input_path, output_path)
        
        # 验证结果
        self.assertTrue(success)
        
        # 验证调用
        mock_shp_reader.assert_called_once_with(input_path)
        mock_reader_instance.load_shapefile.assert_called_once()
        mock_reader_instance.convert_to_utm.assert_called_once()
        mock_generator_instance.generate_file.assert_called_once_with(output_path)
        
        # 验证统计
        stats = self.converter.get_conversion_stats()
        self.assertEqual(stats['input_roads'], 2)
        self.assertEqual(stats['output_roads'], 2)
        self.assertGreater(stats['conversion_time'], 0)
    
    @patch('main.ShapefileReader')
    def test_convert_shapefile_load_failure(self, mock_shp_reader):
        """测试shapefile加载失败"""
        # 模拟加载失败
        mock_reader_instance = Mock()
        mock_reader_instance.load_shapefile.return_value = False
        mock_shp_reader.return_value = mock_reader_instance
        
        # 执行转换
        success = self.converter.convert("test_input.shp", "test_output.xodr")
        
        # 验证失败
        self.assertFalse(success)
    
    @patch('main.ShapefileReader')
    def test_convert_no_roads_after_filter(self, mock_shp_reader):
        """测试过滤后无道路"""
        # 模拟过滤后无道路
        mock_reader_instance = Mock()
        mock_reader_instance.load_shapefile.return_value = True
        mock_reader_instance.convert_to_utm.return_value = True
        mock_reader_instance.filter_roads_by_length.return_value = 0
        mock_shp_reader.return_value = mock_reader_instance
        
        # 执行转换
        success = self.converter.convert("test_input.shp", "test_output.xodr")
        
        # 验证失败
        self.assertFalse(success)
    
    @patch('main.ShapefileReader')
    def test_convert_no_geometries_extracted(self, mock_shp_reader):
        """测试无几何数据提取"""
        # 模拟无几何数据
        mock_reader_instance = Mock()
        mock_reader_instance.load_shapefile.return_value = True
        mock_reader_instance.convert_to_utm.return_value = True
        mock_reader_instance.filter_roads_by_length.return_value = 1
        mock_reader_instance.get_road_info.return_value = {'road_count': 1}
        mock_reader_instance.extract_road_geometries.return_value = []
        mock_shp_reader.return_value = mock_reader_instance
        
        # 执行转换
        success = self.converter.convert("test_input.shp", "test_output.xodr")
        
        # 验证失败
        self.assertFalse(success)
    
    @patch('main.ShapefileReader')
    @patch('main.OpenDriveGenerator')
    def test_convert_opendrive_validation_failure(self, mock_opendrive_gen, mock_shp_reader):
        """测试OpenDrive验证失败"""
        # 模拟shapefile读取成功
        mock_reader_instance = Mock()
        mock_reader_instance.load_shapefile.return_value = True
        mock_reader_instance.convert_to_utm.return_value = True
        mock_reader_instance.filter_roads_by_length.return_value = 1
        mock_reader_instance.get_road_info.return_value = {'road_count': 1}
        mock_reader_instance.extract_road_geometries.return_value = [
            {
                'id': 1,
                'coordinates': [[0, 0], [10, 0]],
                'length': 10.0,
                'attributes': {}
            }
        ]
        mock_reader_instance.get_road_attributes_mapping.return_value = {}
        mock_shp_reader.return_value = mock_reader_instance
        
        # 模拟OpenDrive验证失败
        mock_generator_instance = Mock()
        mock_generator_instance.create_road_from_segments.return_value = 1
        mock_generator_instance.validate_opendrive.return_value = {
            'valid': False, 
            'errors': ['Test validation error']
        }
        mock_opendrive_gen.return_value = mock_generator_instance
        
        # 执行转换
        success = self.converter.convert("test_input.shp", "test_output.xodr")
        
        # 验证失败
        self.assertFalse(success)
    
    def test_convert_exception_handling(self):
        """测试异常处理"""
        # 使用不存在的文件触发异常
        success = self.converter.convert(
            "nonexistent_file.shp", 
            "test_output.xodr"
        )
        
        # 验证失败
        self.assertFalse(success)
        
        # 验证错误记录
        stats = self.converter.get_conversion_stats()
        self.assertGreater(len(stats['errors']), 0)


class TestMainCommandLine(unittest.TestCase):
    """命令行接口测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('main.ShpToOpenDriveConverter')
    @patch('sys.argv')
    def test_main_basic_args(self, mock_argv, mock_converter_class):
        """测试基本命令行参数"""
        # 模拟命令行参数
        mock_argv.__getitem__.side_effect = lambda x: [
            'main.py', 'input.shp', 'output.xodr'
        ][x]
        mock_argv.__len__.return_value = 3
        
        # 模拟转换器
        mock_converter = Mock()
        mock_converter.convert.return_value = True
        mock_converter_class.return_value = mock_converter
        
        # 导入并运行main函数
        from main import main
        
        with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Mock()
            mock_args.input = 'input.shp'
            mock_args.output = 'output.xodr'
            mock_args.config = None
            mock_args.tolerance = 1.0
            mock_args.min_length = 10.0
            mock_args.use_arcs = False
            mock_args.report = None
            mock_parse_args.return_value = mock_args
            
            result = main()
        
        # 验证成功
        self.assertEqual(result, 0)
        mock_converter.convert.assert_called_once_with('input.shp', 'output.xodr')
    
    @patch('main.ShpToOpenDriveConverter')
    def test_main_with_config_file(self, mock_converter_class):
        """测试带配置文件的命令行"""
        # 创建配置文件
        config_path = os.path.join(self.temp_dir, 'config.json')
        config_data = {
            'geometry_tolerance': 0.5,
            'use_arc_fitting': True
        }
        
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        
        # 模拟转换器
        mock_converter = Mock()
        mock_converter.convert.return_value = True
        mock_converter_class.return_value = mock_converter
        
        # 导入并运行main函数
        from main import main
        
        with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Mock()
            mock_args.input = 'input.shp'
            mock_args.output = 'output.xodr'
            mock_args.config = config_path
            mock_args.tolerance = 1.0
            mock_args.min_length = 10.0
            mock_args.use_arcs = False
            mock_args.report = None
            mock_parse_args.return_value = mock_args
            
            result = main()
        
        # 验证成功
        self.assertEqual(result, 0)
        
        # 验证转换器使用了正确的配置
        call_args = mock_converter_class.call_args[0][0]
        self.assertEqual(call_args['geometry_tolerance'], 1.0)  # 命令行参数覆盖
        self.assertTrue(call_args['use_arc_fitting'])  # 来自配置文件
    
    @patch('main.ShpToOpenDriveConverter')
    def test_main_conversion_failure(self, mock_converter_class):
        """测试转换失败"""
        # 模拟转换失败
        mock_converter = Mock()
        mock_converter.convert.return_value = False
        mock_converter_class.return_value = mock_converter
        
        # 导入并运行main函数
        from main import main
        
        with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
            mock_args = Mock()
            mock_args.input = 'input.shp'
            mock_args.output = 'output.xodr'
            mock_args.config = None
            mock_args.tolerance = 1.0
            mock_args.min_length = 10.0
            mock_args.use_arcs = False
            mock_args.report = None
            mock_parse_args.return_value = mock_args
            
            result = main()
        
        # 验证失败
        self.assertEqual(result, 1)


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)