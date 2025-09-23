# ShpToOpenDrive API 文档

## 项目概述

ShpToOpenDrive 是一个将 Shapefile 格式的道路数据转换为 OpenDrive 标准格式的 Python 工具包。该项目提供了完整的转换流程，包括数据读取、几何处理、格式转换和文件生成。

## 系统架构

详细的转换流程和组件交互请参考：[序列图文档](docs/sequence_diagram.md)

该文档包含：
- 主要转换流程序列图
- 车道面处理详细流程
- 几何转换详细流程
- 文件生成流程
- 关键组件说明

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

**功能:** 初始化 Shapefile 读取器，支持传统道路格式和Lane.shp格式

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

**功能:** 提取所有道路的几何信息和属性数据，自动检测文件格式

**坐标处理:**
- 自动检测并处理三维坐标数据（包含Z值）
- 确保输出的坐标为二维格式 (x, y)
- 兼容二维和三维输入数据

##### extract_lane_geometries()
```python
extract_lane_geometries(self) -> List[Dict]
```
**返回值:** List[Dict] - Lane格式道路数据列表

**功能:** 专门处理Lane.shp格式，按RoadID分组并构建车道面

**返回数据结构:**
```python
[
    {
        'road_id': str,         # 道路ID
        'lanes': List[Dict],    # 车道数据列表
        'lane_surfaces': List[Dict], # 车道面数据
        'lane_count': int,      # 车道数量
        'attributes': Dict      # 道路属性
    }
]
```

##### _is_lane_shapefile()
```python
_is_lane_shapefile(self) -> bool
```
**返回值:** bool - 是否为Lane格式

**功能:** 检测shapefile是否为Lane.shp格式（包含RoadID和Index字段）

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

##### _build_lanes_from_boundaries() (v1.2.0新增)
```python
_build_lanes_from_boundaries(self, boundary_lines: List[Dict]) -> List[Dict]
```
**参数:**
- `boundary_lines` (List[Dict]): 边界线列表

**返回值:** List[Dict] - 车道面列表

**功能:** 从边界线构建车道面，相邻边界线组合成车道面

**构建流程:**
1. 按Index排序边界线确保正确的相邻关系
2. 相邻边界线组合成车道面
3. 计算车道面中心线和宽度变化
4. 合并边界属性信息

**车道面数据结构:**
```python
{
    'surface_id': str,           # 车道面ID (格式: "左Index_右Index")
    'left_boundary': Dict,       # 左边界信息
    'right_boundary': Dict,      # 右边界信息
    'center_line': List[tuple],  # 中心线坐标
    'width_profile': List[Dict], # 宽度变化曲线
    'attributes': Dict           # 合并的属性信息
}
```

##### _calculate_center_line() (v1.2.0新增)
```python
_calculate_center_line(self, left_coords: List[tuple], right_coords: List[tuple]) -> List[tuple]
```
**参数:**
- `left_coords` (List[tuple]): 左边界坐标
- `right_coords` (List[tuple]): 右边界坐标

**返回值:** List[tuple] - 中心线坐标

**功能:** 计算两条边界线之间的中心线

**算法:**
- 确保两条线有相同的点数（取较少的点数）
- 计算对应点的中点坐标
- 生成中心线坐标序列

##### _calculate_width_profile() (v1.2.0新增)
```python
_calculate_width_profile(self, left_coords: List[tuple], right_coords: List[tuple]) -> List[Dict]
```
**参数:**
- `left_coords` (List[tuple]): 左边界坐标
- `right_coords` (List[tuple]): 右边界坐标

**返回值:** List[Dict] - 宽度变化数据

**功能:** 计算车道宽度变化曲线，支持变宽车道的描述

##### _merge_boundary_attributes() (v1.2.0新增)
```python
_merge_boundary_attributes(self, left_attrs: Dict, right_attrs: Dict) -> Dict
```
**参数:**
- `left_attrs` (Dict): 左边界属性
- `right_attrs` (Dict): 右边界属性

**返回值:** Dict - 合并后的属性

**功能:** 合并左右边界的属性信息，生成车道面的综合属性

---

## 2. geometry_converter.py - 几何转换模块

### 模块说明
负责将 Shapefile 中的复杂几何形状转换为 OpenDrive 标准的几何元素（直线段和圆弧段）。

### GeometryConverter 类

#### 构造函数
```python
__init__(self, tolerance: float = 1.0, use_smooth_curves: bool = True, preserve_detail: bool = True)
```
**参数:**
- `tolerance` (float): 几何简化容差，默认 1.0 米
- `use_smooth_curves` (bool): 是否使用平滑曲线拟合，默认 True
- `preserve_detail` (bool): 是否保留细节，默认 True

**功能:** 初始化几何转换器，支持传统道路和变宽车道面转换

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

##### convert_lane_surface_geometry()
```python
convert_lane_surface_geometry(self, lane_surfaces: List[Dict]) -> List[Dict]
```
**参数:**
- `lane_surfaces` (List[Dict]): 车道面数据列表

**返回值:** List[Dict] - 转换后的车道面几何数据

**功能:** 转换车道面几何，计算中心线和宽度变化曲线

**返回数据结构:**
```python
[
    {
        'surface_id': str,          # 车道面ID
        'center_segments': List[Dict], # 中心线几何段
        'width_profile': List[Dict],   # 宽度变化曲线
        'left_boundary': Dict,      # 左边界
        'right_boundary': Dict      # 右边界
    }
]
```

##### _calculate_center_line()
```python
_calculate_center_line(self, left_coords: List[Tuple[float, float]], right_coords: List[Tuple[float, float]]) -> List[Tuple[float, float]]
```
**参数:**
- `left_coords` (List[Tuple[float, float]]): 左边界坐标点
- `right_coords` (List[Tuple[float, float]]): 右边界坐标点

**返回值:** List[Tuple[float, float]] - 中心线坐标点

**功能:** 计算两条边界线的中心线，保持复杂形状。使用高密度插值来保持曲线形状，对于点数较少的车道面增加10倍采样密度。

**算法特点:**
- 自适应采样密度：少点数时增加10倍采样，多点数时增加2倍采样
- 高密度插值保持复杂曲线形状
- 支持不同长度的左右边界线

##### _interpolate_coordinates()
```python
_interpolate_coordinates(self, coords: List[Tuple], target_count: int) -> List[Tuple]
```
**参数:**
- `coords` (List[Tuple]): 原始坐标点
- `target_count` (int): 目标点数

**返回值:** List[Tuple] - 插值后的坐标点

**功能:** 插值坐标点以匹配目标数量，基于累积距离进行等间距插值

##### _calculate_width_profile()
```python
_calculate_width_profile(self, left_coords: List[Tuple], right_coords: List[Tuple], center_segments: List[Dict]) -> List[Dict]
```
**参数:**
- `left_coords` (List[Tuple]): 左边界坐标
- `right_coords` (List[Tuple]): 右边界坐标
- `center_segments` (List[Dict]): 中心线几何段

**返回值:** List[Dict] - 宽度变化曲线数据

**功能:** 计算车道宽度变化曲线，支持变宽车道的精确描述

**返回数据结构:**
```python
[
    {
        's': float,      # 沿中心线的距离
        'width': float   # 该位置的车道宽度
    }
]
```

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

**版本设置:**
- 自动设置 OpenDrive 版本为 1.7 (revMajor=1, revMinor=7)
- 确保生成的文件符合 OpenDrive 标准格式

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

##### create_road_from_lane_surfaces() (v1.2.0新增)
```python
create_road_from_lane_surfaces(self, lane_surfaces: List[Dict], road_attributes: Dict = None) -> int
```
**参数:**
- `lane_surfaces` (List[Dict]): 车道面数据列表
- `road_attributes` (Dict, 可选): 道路属性

**返回值:** int - 创建的道路ID，失败时返回-1

**功能:** 从车道面数据创建道路，支持多车道面的复杂道路结构

**处理流程:**
1. 计算道路参考线（使用所有车道面的平均中心线）
2. 创建道路几何（planView）
3. 创建基于车道面的车道剖面
4. 生成完整的道路对象

**特点:**
- 支持变宽车道的精确描述
- 自动计算平均中心线作为道路参考线
- 智能处理车道宽度变化

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

##### _calculate_road_reference_line() (v1.2.0新增)
```python
_calculate_road_reference_line(self, lane_surfaces: List[Dict]) -> List[Dict]
```
**参数:**
- `lane_surfaces` (List[Dict]): 车道面数据列表

**返回值:** List[Dict] - 道路参考线的几何段

**功能:** 计算道路参考线（所有车道面的平均中心线）

**算法策略:**
- 单车道面：直接使用其中心线
- 多车道面：计算所有中心线的平均线
- 支持从边界线动态计算中心线

##### _calculate_center_line_coords() (v1.2.0新增)
```python
_calculate_center_line_coords(self, left_coords: List[Tuple[float, float]], right_coords: List[Tuple[float, float]]) -> List[Tuple[float, float]]
```
**参数:**
- `left_coords` (List[Tuple[float, float]]): 左边界坐标
- `right_coords` (List[Tuple[float, float]]): 右边界坐标

**返回值:** List[Tuple[float, float]] - 中心线坐标

**功能:** 从左右边界计算中心线坐标，确保两边界点数相同

##### _calculate_average_center_line() (v1.2.0新增)
```python
_calculate_average_center_line(self, all_center_coords: List[List[Tuple[float, float]]]) -> List[Tuple[float, float]]
```
**参数:**
- `all_center_coords` (List[List[Tuple[float, float]]]): 所有车道面的中心线坐标列表

**返回值:** List[Tuple[float, float]] - 平均中心线坐标

**功能:** 计算多个中心线的平均线，用于生成道路参考线

**算法:**
- 找到最短中心线长度作为基准
- 对每个位置计算所有中心线的坐标平均值
- 生成统一长度的平均中心线

##### _create_lane_section_from_surfaces() (v1.2.0新增)
```python
_create_lane_section_from_surfaces(self, lane_surfaces: List[Dict], attributes: Dict = None) -> xodr.Lanes
```
**参数:**
- `lane_surfaces` (List[Dict]): 车道面数据列表
- `attributes` (Dict, 可选): 道路属性

**返回值:** xodr.Lanes - 车道对象

**功能:** 从车道面数据创建车道剖面，支持变宽车道

**变宽车道处理:**
- 检测宽度变化超过0.1米的车道
- 为变宽车道创建多个width元素
- 等宽车道使用单个width元素
- 自动添加车道标线

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
    'use_smooth_curves': True,      # 使用平滑曲线
    'preserve_detail': True,        # 保留细节
    'coordinate_precision': 3,      # 坐标精度（小数位数）
    'lane_format_settings': {       # Lane格式专用设置
        'enabled': True,
        'road_id_field': 'RoadID',
        'index_field': 'Index'
    }
}
```

**功能:** 初始化转换器，支持传统道路和Lane.shp格式转换

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

##### _process_lane_data() (v1.2.0新增)
```python
_process_lane_data(self, roads_geometries: List[Dict], attribute_mapping: Dict = None) -> List[Dict]
```
**参数:**
- `roads_geometries` (List[Dict]): Lane格式的道路几何数据
- `attribute_mapping` (Dict, 可选): 属性映射配置

**返回值:** List[Dict] - 处理后的道路数据

**功能:** 处理Lane.shp格式的数据，构建基于车道面的道路结构

**处理特点:**
- 支持车道面数据结构
- 计算基于中心线的道路长度
- 提取车道属性信息
- 标识为lane_based类型道路

##### _convert_lane_based_geometry() (v1.2.0新增)
```python
_convert_lane_based_geometry(self, road_data: Dict) -> Dict
```
**参数:**
- `road_data` (Dict): Lane格式的道路数据

**返回值:** Dict - 转换后的道路数据

**功能:** 转换基于车道的几何数据，调用geometry_converter进行车道面几何转换

**转换流程:**
1. 提取车道面数据
2. 调用convert_lane_surface_geometry进行几何转换
3. 计算道路总长度
4. 构建完整的转换后道路数据

##### _extract_segments_from_lane_surfaces() (v1.2.0新增)
```python
_extract_segments_from_lane_surfaces(self, lane_surfaces: List[Dict]) -> List[Dict]
```
**参数:**
- `lane_surfaces` (List[Dict]): 车道面数据列表

**返回值:** List[Dict] - 几何段列表

**功能:** 从车道面数据中提取几何段，优先使用center_segments，备选从边界生成

##### _extract_lane_attributes() (v1.2.0新增)
```python
_extract_lane_attributes(self, lanes: List[Dict], attribute_mapping: Dict = None) -> Dict
```
**参数:**
- `lanes` (List[Dict]): 车道数据列表
- `attribute_mapping` (Dict, 可选): 属性映射配置

**返回值:** Dict - 提取的车道属性

**功能:** 从车道数据中提取属性信息，支持自定义属性映射

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

##### _is_lane_format()
```python
_is_lane_format(self, roads_data: List[Dict]) -> bool
```
**功能:** 检测道路数据是否为Lane格式

##### _process_lane_data()
```python
_process_lane_data(self, roads_data: List[Dict]) -> List[Dict]
```
**功能:** 处理Lane格式的道路数据，按RoadID分组并构建车道面

##### _process_traditional_data()
```python
_process_traditional_data(self, roads_data: List[Dict]) -> List[Dict]
```
**功能:** 处理传统格式的道路数据

##### _extract_lane_attributes()
```python
_extract_lane_attributes(self, lane_group: List[Dict]) -> Dict
```
**功能:** 从车道组中提取道路属性

##### _convert_lane_based_geometry()
```python
_convert_lane_based_geometry(self, road_data: Dict) -> Dict
```
**功能:** 转换基于车道的几何数据

##### _convert_traditional_geometry()
```python
_convert_traditional_geometry(self, road_data: Dict) -> Dict
```
**功能:** 转换传统格式的几何数据

##### _extract_segments_from_lane_surfaces()
```python
_extract_segments_from_lane_surfaces(self, lane_surfaces: List[Dict]) -> List[Dict]
```
**功能:** 从车道面数据中提取几何段用于OpenDrive生成

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

**命令行快速转换示例:**
```bash
# 使用默认配置转换
python -c "from src.main import ShpToOpenDriveConverter; import json; config = json.load(open('config/example_config.json', 'r', encoding='utf-8')); converter = ShpToOpenDriveConverter(config); result = converter.convert('data/CenterLane.shp', 'output/CenterLane.xodr'); print('转换成功!' if result else '转换失败!')"

# 使用高精度配置转换
python -c "from src.main import ShpToOpenDriveConverter; import json; config = json.load(open('config/high_precision.json', 'r', encoding='utf-8')); converter = ShpToOpenDriveConverter(config); result = converter.convert('data/sample_roads.shp', 'output/sample_roads.xodr'); print('转换成功!' if result else '转换失败!')"
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

## 5. xodr_parser.py - OpenDrive 解析模块

### 模块说明
负责解析 OpenDrive (.xodr) 格式文件，提取道路几何信息并转换为可视化数据。

### XODRParser 类

#### 构造函数
```python
__init__(self)
```
**功能:** 初始化 OpenDrive 解析器

#### 主要方法

##### parse_file()
```python
parse_file(self, file_path: str) -> Dict
```
**参数:**
- `file_path` (str): XODR 文件路径

**返回值:** Dict - 包含头部信息、道路数据和交叉口信息的字典

**功能:** 解析 OpenDrive 文件并提取所有结构化数据

**异常处理:**
- XML 解析错误时抛出 ValueError
- 文件读取失败时抛出相应异常

##### get_road_center_lines()
```python
get_road_center_lines(self, resolution: float = 1.0) -> Dict[str, Dict]
```
**参数:**
- `resolution` (float): 采样分辨率（米），默认1.0

**返回值:** Dict[str, Dict] - 道路中心线字典

**功能:** 获取所有道路的中心线点序列

**返回数据结构:**
```python
{
    'road_id': {
        'coordinates': List[Tuple[float, float]],  # 中心线坐标点
        'length': float                            # 道路长度
    }
}
```

**特点:**
- 支持自定义采样分辨率
- 自动过滤无几何数据的道路
- 返回完整的坐标序列和长度信息

##### generate_road_points() (v1.2.0新增)
```python
generate_road_points(self, road: Dict, resolution: float = 1.0) -> List[Tuple[float, float]]
```
**参数:**
- `road` (Dict): 道路数据字典
- `resolution` (float): 采样分辨率（米），默认1.0

**返回值:** List[Tuple[float, float]] - 道路中心线坐标点

**功能:** 根据道路的planView几何数据生成中心线坐标点序列

**支持的几何类型:**
- 直线（line）几何
- 圆弧（arc）几何
- 螺旋线（spiral）几何
- 多项式（poly3）几何

##### get_statistics()
```python
get_statistics(self) -> Dict
```
**返回值:** Dict - 包含道路数量、总长度、几何类型等统计信息

**功能:** 获取解析后的统计信息

##### generate_road_points()
```python
generate_road_points(self, road_data: Dict, resolution: float = 1.0) -> List[Tuple[float, float, float]]
```
**参数:**
- `road_data` (Dict): 道路数据
- `resolution` (float): 采样分辨率（米）

**返回值:** List[Tuple[float, float, float]] - 3D 点列表

**功能:** 根据道路几何生成 3D 点序列

---

## Web API 接口

### /api/upload_xodr
**方法:** POST
**功能:** 上传 OpenDrive 文件并转换为 GeoJSON 格式

**请求参数:**
- `files`: 文件列表，必须包含 .xodr 格式文件

**响应格式:**
```json
{
  "success": true,
  "message": "成功上传并加载 N 条道路",
  "data": {
    "type": "FeatureCollection",
    "features": [...],
    "metadata": {
      "center": [x, y, z],
      "bounds": {...},
      "feature_count": N,
      "has_z_coordinate": true
    }
  },
  "filename": "example.xodr",
  "upload_dir": "/tmp/..."
}
```

---

## 最近更新

### v1.2.0 (最新版本)

#### 新增功能
1. **车道面生成系统**: 全新的车道面处理架构
   - `create_road_from_lane_surfaces()`: 从车道面数据创建道路
   - `_calculate_road_reference_line()`: 智能计算道路参考线
   - `_calculate_average_center_line()`: 多车道面平均中心线计算
   - 支持复杂多车道面道路结构

2. **高精度中心线计算**: 改进的中心线生成算法
   - 自适应采样密度：少点数时增加10倍采样
   - 高密度插值保持复杂曲线形状
   - 支持不同长度的左右边界线

3. **车道面构建系统**: 从边界线自动构建车道面
   - `_build_lanes_from_boundaries()`: 智能车道面构建
   - 按Index排序确保正确的相邻关系
   - 自动计算中心线和宽度变化

4. **Lane.shp格式支持**: 完整的车道面数据处理
   - `_process_lane_data()`: 专门的Lane格式数据处理
   - `_convert_lane_based_geometry()`: 车道几何转换
   - 支持基于车道面的道路结构

#### 算法优化
- **平均中心线算法**: 多车道面的智能参考线生成
- **变宽车道检测**: 精确识别宽度变化超过0.1米的车道
- **几何段提取**: 从车道面数据提取道路几何
- **属性合并**: 智能合并左右边界属性

### v1.1.0
- **新增功能**: 添加 OpenDrive 文件解析和可视化支持
- **修复问题**: 修复 `get_road_center_lines()` 方法返回格式不匹配导致的 metadata 访问错误
- **改进**: 统一 Shapefile 和 OpenDrive 文件的处理流程
- **Web界面**: 支持混合文件格式上传，自动识别文件类型

---

## 7. validate_xodr.py - OpenDrive 文件验证模块

### 模块说明
验证生成的 OpenDrive (.xodr) 文件是否符合标准格式要求。

### 主要功能

#### validate_opendrive_file()
```python
validate_opendrive_file(file_path: str) -> Dict
```
**参数:**
- `file_path` (str): .xodr 文件路径

**返回值:** Dict - 验证结果字典

**验证项目:**
- XML 格式正确性
- OpenDrive 根元素结构
- Header 必需属性 (revMajor, revMinor, name)
- Header 推荐属性 (version, date)
- 基本统计信息 (道路数量、车道数量、总长度)

#### 批量验证
```python
python validate_xodr.py
```
**功能:**
- 自动扫描 output 目录下所有 .xodr 文件
- 生成详细的验证报告
- 显示验证通过率和合规性检查结果

---

## 版本信息

**当前版本**: v1.2.0  
**更新日期**: 2025年1月  
**兼容性**: Python 3.7+, OpenDRIVE 1.4+

### 更新日志

#### v1.2.0 (2025年1月)
- **重大更新**: 新增车道面生成系统，支持从车道面数据创建道路
- **新增功能**: 高精度中心线计算，自适应采样密度算法
- **新增功能**: 车道面构建系统，从边界线自动构建车道面
- **新增功能**: Lane.shp格式完整支持，专门的车道数据处理
- **算法优化**: 平均中心线算法，多车道面智能参考线生成
- **算法优化**: 变宽车道精确检测和处理
- 新增 `validate_xodr.py` 模块，提供 OpenDRIVE 文件验证功能
- 增强错误处理和日志记录
- 优化几何转换算法
- 改进文档结构和示例

#### v1.1.0 (2024年12月)
- 新增 `xodr_parser.py` 模块，支持 OpenDRIVE 文件解析
- 添加 Web API 接口
- 增强几何转换精度
- 优化内存使用
- **变宽车道支持**: 新增对车道宽度变化的精确描述
- **几何转换优化**: 改进了几何段转换算法
- **日志系统增强**: 添加了详细的处理日志

#### v1.0.0 (2024年11月)
- 初始版本发布
- 基础 Shapefile 到 OpenDRIVE 转换功能
- 支持直线和圆弧几何
- 基本的车道配置

---

## v1.2.0 版本总结

### 核心改进

#### 1. 车道面生成系统
v1.2.0版本引入了全新的车道面处理架构，支持从复杂的车道面数据创建精确的OpenDRIVE道路：

- **智能参考线计算**: 自动计算多车道面的平均中心线作为道路参考线
- **变宽车道支持**: 精确处理宽度变化超过0.1米的车道
- **车道面构建**: 从边界线自动构建完整的车道面结构

#### 2. 高精度几何算法
新版本大幅提升了几何计算的精度和稳定性：

- **自适应采样**: 根据数据复杂度自动调整采样密度
- **形状保持**: 高密度插值确保复杂曲线形状不失真
- **边界处理**: 智能处理不同长度的左右边界线

#### 3. Lane.shp格式完整支持
专门针对Lane.shp格式优化的数据处理流程：

- **专用处理器**: `_process_lane_data()` 专门处理车道数据
- **几何转换**: `_convert_lane_based_geometry()` 优化的车道几何转换
- **属性合并**: 智能合并左右边界的属性信息

### 技术特点

#### 算法优势
- **平均中心线算法**: 多车道面的智能参考线生成，确保道路几何的准确性
- **变宽车道检测**: 精确识别和处理宽度变化，支持复杂的车道轮廓
- **几何段提取**: 从车道面数据高效提取道路几何信息

#### 数据结构优化
- **车道面数据结构**: 完整的车道面信息包含边界、中心线、宽度变化等
- **宽度变化曲线**: 精确描述车道宽度沿道路的变化情况
- **属性映射**: 灵活的属性映射机制支持不同数据源

### 应用场景

v1.2.0版本特别适用于：

1. **复杂道路建模**: 多车道、变宽车道的精确建模
2. **高精度仿真**: 自动驾驶仿真对道路几何的高精度要求
3. **数据转换**: 从GIS数据到仿真数据的无损转换
4. **道路设计**: 支持复杂道路设计的数字化表达

### 兼容性

- **向后兼容**: 完全兼容v1.1.0的所有功能
- **数据格式**: 支持Road.shp和Lane.shp两种数据格式
- **OpenDRIVE标准**: 符合OpenDRIVE 1.4+标准
- **Python版本**: 支持Python 3.7+

---

*本文档最后更新时间: 2025年1月*