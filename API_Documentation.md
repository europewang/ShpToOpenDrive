# ShpToOpenDrive API 文档

## 项目概述

ShpToOpenDrive 是一个将 Shapefile 格式的道路数据转换为 OpenDrive 标准格式的 Python 工具包。该项目提供了完整的转换流程，包括数据读取、几何处理、格式转换和文件生成。

## 模块架构

```
src/
├── main.py                 # 主程序和转换器
├── shp_reader.py           # Shapefile 读取模块
├── geometry_converter.py   # 几何转换模块
└── opendrive_generator.py  # OpenDrive 生成模块
```

---

## 1. shp_reader.py - Shapefile 读取模块

### 模块说明
负责读取和预处理 Shapefile 格式的道路数据，包括坐标系转换、数据过滤和属性提取。

### ShapefileReader 类

#### 构造函数
```python
__init__(self, shapefile_path: str)
```
**参数:**
- `shapefile_path` (str): Shapefile 文件路径

**功能:** 初始化 Shapefile 读取器

#### 主要方法

##### load_shapefile()
```python
load_shapefile(self) -> bool
```
**返回值:** bool - 加载是否成功

**功能:** 加载 Shapefile 文件并验证数据有效性

**异常处理:**
- 文件不存在或格式错误时返回 False
- 记录详细的错误日志

##### get_road_info()
```python
get_road_info(self) -> Dict[str, any]
```
**返回值:** Dict - 包含道路基本信息的字典

**返回字典结构:**
```python
{
    'road_count': int,           # 道路数量
    'total_length': float,       # 总长度（米）
    'coordinate_system': str,    # 坐标系信息
    'bounds': tuple,            # 边界范围 (minx, miny, maxx, maxy)
    'geometry_types': list      # 几何类型列表
}
```

##### extract_road_geometries()
```python
extract_road_geometries(self) -> List[Dict]
```
**返回值:** List[Dict] - 道路几何信息列表

**返回列表元素结构:**
```python
{
    'id': int,                  # 道路ID
    'coordinates': List[Tuple], # 坐标点列表 [(x, y), ...]
    'length': float,            # 道路长度（米）
    'attributes': Dict          # 属性字典
}
```

**功能:** 提取所有道路的几何信息和属性数据

**坐标处理:**
- 自动检测并处理三维坐标数据（包含Z值）
- 确保输出的坐标为二维格式 (x, y)
- 兼容二维和三维输入数据

##### get_road_attributes_mapping()
```python
get_road_attributes_mapping(self) -> Dict[str, str]
```
**返回值:** Dict - 属性字段映射建议

**功能:** 分析 Shapefile 属性字段，提供到 OpenDrive 标准字段的映射建议

##### convert_to_utm()
```python
convert_to_utm(self) -> bool
```
**返回值:** bool - 转换是否成功

**功能:** 将地理坐标系转换为 UTM 投影坐标系

**转换逻辑:**
1. 检测当前坐标系是否为地理坐标系
2. 计算数据中心经度确定 UTM 区域
3. 判断南北半球
4. 执行坐标转换
5. 记录转换前后的坐标范围信息

##### convert_to_local_coordinates()
```python
convert_to_local_coordinates(self) -> bool
```
**返回值:** bool - 转换是否成功

**功能:** 将坐标转换为局部坐标系（以数据范围的最小点为原点）

**转换逻辑:**
1. 获取数据边界范围
2. 以最小 x、y 坐标为原点
3. 对所有几何体进行坐标平移
4. 支持 LineString 和 MultiLineString 几何类型
5. 生成适合 OpenDrive 格式的局部坐标系

**应用场景:**
- 确保 OpenDrive 文件中的坐标从 (0,0) 附近开始
- 避免大坐标值导致的精度问题
- 提高转换后文件的兼容性

##### filter_roads_by_length()
```python
filter_roads_by_length(self, min_length: float) -> int
```
**参数:**
- `min_length` (float): 最小长度阈值（米）

**返回值:** int - 过滤后剩余道路数量

**功能:** 根据长度过滤道路，移除过短的道路段

##### get_sample_data()
```python
get_sample_data(self, n: int = 5) -> List[Dict]
```
**参数:**
- `n` (int): 样本数量，默认 5

**返回值:** List[Dict] - 样本道路数据

**功能:** 获取前 n 条道路的样本数据用于预览和测试

---

## 2. geometry_converter.py - 几何转换模块

### 模块说明
负责将 Shapefile 中的复杂几何形状转换为 OpenDrive 标准的几何元素（直线段和圆弧段）。

### GeometryConverter 类

#### 构造函数
```python
__init__(self, tolerance: float = 1.0)
```
**参数:**
- `tolerance` (float): 几何拟合容差（米），默认 1.0

**功能:** 初始化几何转换器，设置拟合精度

#### 主要方法

##### convert_road_geometry()
```python
convert_road_geometry(self, coordinates: List[Tuple[float, float]]) -> List[Dict]
```
**参数:**
- `coordinates` (List[Tuple]): 道路坐标点列表

**返回值:** List[Dict] - 几何段列表

**几何段字典结构:**
```python
{
    'type': str,        # 'line' 或 'arc'
    's': float,         # 起始 s 坐标
    'x': float,         # 起始 x 坐标
    'y': float,         # 起始 y 坐标
    'hdg': float,       # 起始航向角（弧度）
    'length': float,    # 段长度
    'curvature': float  # 曲率（仅圆弧段）
}
```

**功能:** 将坐标序列转换为 OpenDrive 几何段

##### fit_line_segments()
```python
fit_line_segments(self, coordinates: List[Tuple[float, float]]) -> List[Dict]
```
**参数:**
- `coordinates` (List[Tuple]): 坐标点列表

**返回值:** List[Dict] - 直线段列表

**功能:** 使用 Douglas-Peucker 算法简化坐标序列并拟合为直线段

**算法流程:**
1. 使用 Douglas-Peucker 算法简化坐标点
2. 计算相邻点间的直线段参数
3. 生成符合 OpenDrive 标准的几何段

##### fit_arc_segments()
```python
fit_arc_segments(self, coordinates: List[Tuple[float, float]]) -> List[Dict]
```
**参数:**
- `coordinates` (List[Tuple]): 坐标点列表

**返回值:** List[Dict] - 混合几何段列表（直线段和圆弧段）

**功能:** 检测弯曲段并拟合为圆弧，直线段保持为直线

**算法流程:**
1. 检测坐标序列中的弯曲段
2. 对弯曲段进行圆弧拟合
3. 对直线段保持直线处理
4. 组合生成完整的几何段序列

##### calculate_road_length()
```python
calculate_road_length(self, segments: List[Dict]) -> float
```
**参数:**
- `segments` (List[Dict]): 几何段列表

**返回值:** float - 道路总长度（米）

**功能:** 计算所有几何段的总长度

##### validate_geometry_continuity()
```python
validate_geometry_continuity(self, segments: List[Dict]) -> bool
```
**参数:**
- `segments` (List[Dict]): 几何段列表

**返回值:** bool - 几何是否连续

**功能:** 验证几何段之间的连续性，确保相邻段的端点匹配

**验证标准:**
- 使用连续几何定义，自动保证几何连续性
- 基于第一个几何段的绝对坐标计算后续段的相对位置

**重要更新 (v1.1):**
- 修复了多线条坐标系统问题
- 现在只有第一个几何段使用绝对坐标 (x, y)
- 后续几何段使用相对定位，避免每条线都从原点开始的错误
- 改进了几何连续性验证算法，适配新的坐标系统

#### 私有方法

##### _douglas_peucker()
```python
_douglas_peucker(self, coordinates: List[Tuple], tolerance: float) -> List[Tuple]
```
**功能:** Douglas-Peucker 线简化算法实现

##### _point_to_line_distance()
```python
_point_to_line_distance(self, point: Tuple, line_start: Tuple, line_end: Tuple) -> float
```
**功能:** 计算点到直线的垂直距离

##### _detect_curve_segment()
```python
_detect_curve_segment(self, coordinates: List[Tuple], start_idx: int) -> int
```
**功能:** 检测弯曲段的结束位置

##### _fit_single_arc()
```python
_fit_single_arc(self, coordinates: List[Tuple], start_s: float) -> Optional[Dict]
```
**功能:** 拟合单个圆弧段

##### _fit_circle()
```python
_fit_circle(self, coordinates: List[Tuple]) -> Tuple[Tuple[float, float], float]
```
**功能:** 使用最小二乘法拟合圆心和半径

---

## 3. opendrive_generator.py - OpenDrive 生成模块

### 模块说明
使用 scenariogeneration 库生成标准的 OpenDrive (.xodr) 格式文件。

### OpenDriveGenerator 类

#### 构造函数
```python
__init__(self, name: str = "ConvertedRoad")
```
**参数:**
- `name` (str): 道路网络名称，默认 "ConvertedRoad"

**功能:** 初始化 OpenDrive 生成器

#### 主要方法

##### create_road_from_segments()
```python
create_road_from_segments(self, segments: List[Dict], road_attributes: Dict = None) -> int
```
**参数:**
- `segments` (List[Dict]): 几何段列表
- `road_attributes` (Dict): 道路属性，可选

**默认属性:**
```python
{
    'lane_width': 3.5,    # 车道宽度（米）
    'num_lanes': 1,       # 车道数量
    'speed_limit': 50     # 限速（km/h）
}
```

**返回值:** int - 创建的道路 ID，失败时返回 -1

**功能:** 从几何段创建完整的 OpenDrive 道路对象

##### create_multiple_roads()
```python
create_multiple_roads(self, roads_data: List[Dict]) -> List[int]
```
**参数:**
- `roads_data` (List[Dict]): 道路数据列表

**道路数据结构:**
```python
{
    'segments': List[Dict],    # 几何段列表
    'attributes': Dict         # 道路属性
}
```

**返回值:** List[int] - 创建的道路 ID 列表

**功能:** 批量创建多条道路

##### add_road_connections()
```python
add_road_connections(self, connections: List[Dict])
```
**参数:**
- `connections` (List[Dict]): 连接信息列表

**连接信息结构:**
```python
{
    'road1_id': int,           # 道路1 ID
    'road2_id': int,           # 道路2 ID
    'contact_point': str       # 连接点类型 ('start'/'end')
}
```

**功能:** 添加道路间的连接关系（简化实现）

##### add_road_objects()
```python
add_road_objects(self, road_id: int, objects: List[Dict])
```
**参数:**
- `road_id` (int): 道路 ID
- `objects` (List[Dict]): 道路对象列表

**对象信息结构:**
```python
{
    's': float,           # s 坐标
    't': float,           # t 坐标
    'id': int,            # 对象 ID
    'type': str,          # 对象类型
    'name': str,          # 对象名称
    'z_offset': float,    # 高度偏移
    'heading': float      # 朝向角
}
```

**功能:** 为指定道路添加道路对象（标志、信号灯等）

##### set_road_elevation()
```python
set_road_elevation(self, road_id: int, elevation_data: List[Dict])
```
**参数:**
- `road_id` (int): 道路 ID
- `elevation_data` (List[Dict]): 高程数据列表

**高程数据结构:**
```python
{
    's': float,    # s 坐标
    'a': float,    # 高程值
    'b': float,    # 坡度
    'c': float,    # 曲率变化
    'd': float     # 曲率变化率
}
```

**功能:** 设置道路的高程剖面

##### generate_file()
```python
generate_file(self, output_path: str) -> bool
```
**参数:**
- `output_path` (str): 输出文件路径

**返回值:** bool - 生成是否成功

**功能:** 生成最终的 OpenDrive XML 文件

**生成流程:**
1. 创建输出目录
2. 调整道路和车道连接关系
3. 写入 XML 文件

##### validate_opendrive()
```python
validate_opendrive(self) -> Dict[str, any]
```
**返回值:** Dict - 验证结果

**验证结果结构:**
```python
{
    'valid': bool,           # 是否有效
    'errors': List[str],     # 错误列表
    'warnings': List[str],   # 警告列表
    'road_count': int,       # 道路数量
    'total_length': float    # 总长度
}
```

**功能:** 验证生成的 OpenDrive 数据的有效性

##### get_statistics()
```python
get_statistics(self) -> Dict[str, any]
```
**返回值:** Dict - 统计信息

**统计信息结构:**
```python
{
    'road_count': int,              # 道路数量
    'total_length': float,          # 总长度
    'geometry_types': Dict[str, int], # 几何类型统计
    'lane_count': int               # 车道总数
}
```

**功能:** 获取生成的 OpenDrive 文件的统计信息

#### 私有方法

##### _create_planview_from_segments()
```python
_create_planview_from_segments(self, segments: List[Dict]) -> xodr.PlanView
```
**功能:** 从几何段创建 OpenDrive PlanView 对象

##### _create_lane_section()
```python
_create_lane_section(self, attributes: Dict) -> xodr.Lanes
```
**功能:** 根据属性创建车道剖面

---

## 4. main.py - 主程序模块

### 模块说明
整合所有功能模块，提供完整的转换流程和命令行接口。

### ShpToOpenDriveConverter 类

#### 构造函数
```python
__init__(self, config: Dict = None)
```
**参数:**
- `config` (Dict): 转换配置参数，可选

**默认配置:**
```python
{
    'geometry_tolerance': 1.0,      # 几何拟合容差（米）
    'min_road_length': 10.0,        # 最小道路长度（米）
    'default_lane_width': 3.5,      # 默认车道宽度（米）
    'default_num_lanes': 1,         # 默认车道数
    'default_speed_limit': 50,      # 默认限速（km/h）
    'use_arc_fitting': False,       # 是否使用圆弧拟合
    'coordinate_precision': 3,      # 坐标精度（小数位数）
}
```

**功能:** 初始化转换器，设置配置参数

#### 主要方法

##### convert()
```python
convert(self, shapefile_path: str, output_path: str, attribute_mapping: Dict = None) -> bool
```
**参数:**
- `shapefile_path` (str): 输入 Shapefile 路径
- `output_path` (str): 输出 OpenDrive 文件路径
- `attribute_mapping` (Dict): 属性字段映射，可选

**返回值:** bool - 转换是否成功

**功能:** 执行完整的转换过程

**转换流程:**
1. 加载 Shapefile 文件
2. 提取和预处理道路数据
3. 执行几何转换
4. 生成 OpenDrive 文件
5. 记录转换统计信息

##### get_conversion_stats()
```python
get_conversion_stats(self) -> Dict
```
**返回值:** Dict - 转换统计信息

**统计信息结构:**
```python
{
    'input_roads': int,        # 输入道路数
    'output_roads': int,       # 输出道路数
    'total_length': float,     # 总长度（米）
    'conversion_time': float,  # 转换时间（秒）
    'errors': List[str],       # 错误列表
    'warnings': List[str]      # 警告列表
}
```

**功能:** 获取转换过程的详细统计信息

##### save_conversion_report()
```python
save_conversion_report(self, report_path: str)
```
**参数:**
- `report_path` (str): 报告文件路径

**功能:** 保存详细的转换报告为 JSON 格式

**报告内容:**
- 转换配置
- 统计信息
- 时间戳

#### 私有方法

##### _load_shapefile()
```python
_load_shapefile(self, shapefile_path: str) -> bool
```
**功能:** 加载和预处理 Shapefile 文件

##### _extract_roads_data()
```python
_extract_roads_data(self, attribute_mapping: Dict = None) -> List[Dict]
```
**功能:** 提取道路数据和属性信息

##### _map_attributes()
```python
_map_attributes(self, original_attrs: Dict, mapping: Dict) -> Dict
```
**功能:** 映射属性字段到 OpenDrive 标准

##### _convert_geometries()
```python
_convert_geometries(self, roads_data: List[Dict]) -> List[Dict]
```
**功能:** 转换道路几何数据

##### _generate_opendrive()
```python
_generate_opendrive(self, converted_roads: List[Dict], output_path: str) -> bool
```
**功能:** 生成最终的 OpenDrive 文件

##### _log_conversion_stats()
```python
_log_conversion_stats(self)
```
**功能:** 记录和输出转换统计信息

### 命令行接口

#### main() 函数
```python
main()
```
**功能:** 命令行主函数，解析参数并执行转换

**命令行参数:**
- `input`: 输入 Shapefile 路径（必需）
- `output`: 输出 OpenDrive 文件路径（必需）
- `--config`: 配置文件路径（JSON 格式）
- `--tolerance`: 几何拟合容差（米）
- `--min-length`: 最小道路长度（米）
- `--use-arcs`: 使用圆弧拟合
- `--report`: 转换报告输出路径

**使用示例:**
```bash
python -m src.main input.shp output.xodr --tolerance 0.5 --use-arcs --report report.json
```

---

## 使用指南

### 基本使用

```python
from src.main import ShpToOpenDriveConverter

# 创建转换器
config = {
    'geometry_tolerance': 0.5,
    'min_road_length': 5.0,
    'use_arc_fitting': True
}
converter = ShpToOpenDriveConverter(config)

# 执行转换
success = converter.convert('input.shp', 'output.xodr')

if success:
    stats = converter.get_conversion_stats()
    print(f"转换成功：{stats['output_roads']} 条道路")
else:
    print("转换失败")
```

### 高级配置

```python
# 自定义属性映射
attribute_mapping = {
    'WIDTH': 'lane_width',      # Shapefile 字段 -> OpenDrive 属性
    'LANES': 'num_lanes',
    'SPEED': 'speed_limit'
}

# 执行转换
converter.convert('input.shp', 'output.xodr', attribute_mapping)

# 保存转换报告
converter.save_conversion_report('conversion_report.json')
```

### 错误处理

转换过程中的错误和警告会被记录在统计信息中：

```python
stats = converter.get_conversion_stats()

if stats['errors']:
    print("错误：")
    for error in stats['errors']:
        print(f"  - {error}")

if stats['warnings']:
    print("警告：")
    for warning in stats['warnings']:
        print(f"  - {warning}")
```

---

## 注意事项

1. **坐标系要求**: 输入的 Shapefile 应包含有效的坐标系信息
2. **几何类型**: 仅支持 LineString 类型的几何数据
3. **内存使用**: 大型数据集可能需要较多内存
4. **精度设置**: 几何拟合容差影响输出精度和文件大小
5. **依赖库**: 需要安装 geopandas、shapely、scenariogeneration 等依赖

---

## 版本信息

- **版本**: 1.0.0
- **Python 要求**: >= 3.7
- **主要依赖**: geopandas, shapely, scenariogeneration, numpy

---

*本文档最后更新时间: 2025年1月*