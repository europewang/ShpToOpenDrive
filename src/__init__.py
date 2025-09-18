"""ShpToOpenDrive - 将ArcGIS Shapefile转换为OpenDrive格式的工具包

这个包提供了将shapefile格式的道路数据转换为OpenDrive (.xodr) 格式的功能。
主要模块包括：
- shp_reader: 读取和解析shapefile数据
- geometry_converter: 几何转换和道路参数化
- opendrive_generator: 生成OpenDrive XML文件
"""

__version__ = "0.1.0"
__author__ = "ShpToOpenDrive Team"

from .shp_reader import ShapefileReader
from .geometry_converter import GeometryConverter
from .opendrive_generator import OpenDriveGenerator
from .main import ShpToOpenDriveConverter

__all__ = [
    "ShapefileReader",
    "GeometryConverter", 
    "OpenDriveGenerator",
    "ShpToOpenDriveConverter"
]