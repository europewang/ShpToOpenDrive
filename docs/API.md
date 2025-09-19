# ShpToOpenDrive API 文档

## 概述

ShpToOpenDrive 是一个用于将 Shapefile 数据转换为 OpenDRIVE 格式的 Python 库，现在还支持基于 Open3D 的 3D 可视化功能。

## 核心模块

### 1. GeometryConverter 类

#### 描述
负责将 Shapefile 中的几何数据转换为 OpenDRIVE 格式的几何元素。

#### 主要方法
- `load_shapefile()`: 加载shapefile文件
- `read_features()`: 读取所有道路特征（新增）
- `extract_road_geometries()`: 提取道路几何信息
- `convert_to_utm()`: 坐标系转换
- `get_road_info()`: 获取道路基本信息

##### `__init__(self)`
初始化几何转换器。

##### `convert_linestring_to_opendrive(self, linestring, road_id=1)`
将 LineString 几何转换为 OpenDRIVE 道路几何。

**参数：**
- `linestring`: Shapely LineString 对象
- `road_id`: 道路ID，默认为1

**返回：**
- OpenDRIVE 道路几何数据

##### `calculate_curvature(self, points)`
计算点序列的曲率。

**参数：**
- `points`: 点坐标列表

**返回：**
- 曲率值列表

### 2. OpenDriveGenerator 类

#### 描述
生成完整的 OpenDRIVE XML 文件。

#### 主要方法

##### `__init__(self)`
初始化 OpenDRIVE 生成器。

##### `create_opendrive_from_shapefile(self, shapefile_path, output_path=None)`
从 Shapefile 创建 OpenDRIVE 文件。

**参数：**
- `shapefile_path`: Shapefile 文件路径
- `output_path`: 输出文件路径，可选

**返回：**
- 生成的 OpenDRIVE XML 字符串

##### `add_road(self, road_data)`
添加道路数据到 OpenDRIVE 文档。

**参数：**
- `road_data`: 道路数据字典

##### `generate_xml(self)`
生成最终的 XML 字符串。

**返回：**
- OpenDRIVE XML 字符串

### 3. RoadVisualizer 类 (新增)

#### 描述
基于 Open3D 的 3D 可视化器，支持 SHP 和 OpenDRIVE 文件的可视化显示。

#### 主要方法

##### `__init__(self)`
初始化可视化器，创建 GUI 界面和 3D 渲染窗口。

##### `load_shp_file(self, file_path)`
加载 Shapefile 文件。

**参数：**
- `file_path`: Shapefile 文件路径

**返回：**
- GeoDataFrame 对象

##### `shp_to_line_set(self, gdf)`
将 SHP 数据转换为 Open3D 线集（已修复坐标归一化问题）。

**参数：**
- `gdf`: GeoDataFrame 对象

**返回：**
- Open3D LineSet 对象

##### `load_opendrive_file(self, file_path)`
加载 OpenDRIVE 文件。

**参数：**
- `file_path`: OpenDRIVE 文件路径

**返回：**
- 解析后的 OpenDRIVE 数据字典

##### `create_shp_geometry(self)`
创建 Shapefile 的 3D 几何对象。

**返回：**
- Open3D 几何对象列表

##### `create_opendrive_geometry(self)`
创建 OpenDRIVE 的 3D 几何对象。

**返回：**
- Open3D 几何对象列表

##### `render_scene(self)`
渲染 3D 场景，显示所有加载的几何数据。

##### `export_data(self, format_type, file_path)`
导出数据到指定格式。

**参数：**
- `format_type`: 导出格式 ('ply', 'obj', 'stl', 'pcd')
- `file_path`: 导出文件路径

##### `run(self)`
启动可视化器主循环。

### 4. Web3DServer 类

#### 描述
Flask Web服务器，提供基于 Three.js 的 Web3D 可视化功能，支持 SHP 和 OpenDRIVE 文件的上传、可视化和导出。

#### 主要方法

##### `__init__(self)`
初始化Web3D服务器，创建必要的组件实例。

##### `validate_uploaded_files(self, files)`
验证上传的文件是否包含必要的SHP文件组件。

**参数：**
- `files`: 上传的文件列表

**返回：**
- `(is_valid, message)`: 验证结果和消息

##### `save_uploaded_files(self, files)`
保存上传的文件到临时目录。

**参数：**
- `files`: 上传的文件列表

**返回：**
- `(shp_file_path, upload_dir)`: SHP文件路径和上传目录

##### `load_shp_file(self, file_path)`
加载SHP文件并转换为GeoJSON格式。

**参数：**
- `file_path`: SHP文件路径

**返回：**
- 包含数据和统计信息的字典

##### `load_xodr_file(self, file_path)`
加载OpenDRIVE文件并转换为GeoJSON格式。

**参数：**
- `file_path`: OpenDRIVE文件路径

**返回：**
- 包含数据和统计信息的字典

##### `shp_to_geojson(self, gdf)`
将GeoDataFrame转换为GeoJSON格式，支持坐标归一化。

**参数：**
- `gdf`: GeoDataFrame 对象

**返回：**
- GeoJSON格式的数据字典，包含metadata信息

##### `xodr_to_geojson(self, center_lines)`
将OpenDRIVE中心线数据转换为GeoJSON格式。

**参数：**
- `center_lines`: 道路中心线数据字典

**返回：**
- GeoJSON格式的数据字典

##### `export_to_xodr(self, output_path, **kwargs)`
导出当前数据为OpenDRIVE格式。

**参数：**
- `output_path`: 输出文件路径
- `**kwargs`: 导出参数（CRS、版本、道路宽度等）

**返回：**
- 导出是否成功

##### `export_to_shp(self, output_path, **kwargs)`
导出当前数据为Shapefile格式。

**参数：**
- `output_path`: 输出文件路径
- `**kwargs`: 导出参数（CRS、几何类型等）

**返回：**
- 导出是否成功

#### Web API端点

##### `GET /`
返回Web3D可视化主页。

**返回：**
- HTML页面

##### `POST /api/load_shp`
通过文件路径加载SHP文件。

**请求参数：**
- `shp_path` (string): SHP文件路径

**返回：**
- `success` (boolean): 是否成功
- `message` (string): 状态消息
- `data` (object): GeoJSON数据

##### `POST /api/upload_shp`
上传SHP文件并加载。

**请求参数：**
- `files`: 多个文件（.shp, .shx, .dbf, .prj等）

**返回：**
- `success` (boolean): 是否成功
- `message` (string): 状态消息
- `data` (object): GeoJSON数据
- `filename` (string): 文件名
- `upload_dir` (string): 上传目录

##### `POST /api/upload_xodr`
上传OpenDRIVE文件并加载。

**请求参数：**
- `files`: OpenDRIVE文件（.xodr）

**返回：**
- `success` (boolean): 是否成功
- `message` (string): 状态消息
- `data` (object): GeoJSON数据
- `filename` (string): 文件名

##### `GET /api/get_sample_files`
获取示例SHP文件列表。

**返回：**
- `files` (array): 文件列表

##### `GET /api/current_data`
获取当前加载的数据。

**返回：**
- 当前数据的GeoJSON格式

##### `POST /api/export_xodr`
导出为OpenDRIVE格式。

**请求参数：**
- `fileName` (string): 文件名
- `crs` (string): 坐标系
- `customCRS` (string): 自定义坐标系
- `xodrVersion` (string): OpenDRIVE版本
- `roadWidth` (number): 道路宽度
- `laneCount` (number): 车道数
- `includeElevation` (boolean): 是否包含高程

**返回：**
- 下载的OpenDRIVE文件

##### `POST /api/export_shp`
导出为Shapefile格式。

**请求参数：**
- `fileName` (string): 文件名
- `crs` (string): 坐标系
- `customCRS` (string): 自定义坐标系
- `includeAttributes` (boolean): 是否包含属性
- `geometryType` (string): 几何类型

**返回：**
- 下载的Shapefile文件

### 5. XODRParser 类 (新增)

#### 描述
OpenDRIVE 文件解析器，用于解析和提取 OpenDRIVE 文件中的几何信息。

#### 主要方法

##### `__init__(self)`
初始化解析器。

##### `parse_file(self, file_path)`
解析 OpenDRIVE 文件。

**参数：**
- `file_path`: XODR 文件路径

**返回：**
- 解析后的数据字典，包含 header、roads、junctions

##### `generate_road_points(self, road_data, resolution=1.0)`
根据道路几何生成 3D 点序列。

**参数：**
- `road_data`: 道路数据
- `resolution`: 采样分辨率（米），默认 1.0

**返回：**
- 3D 点列表 [(x, y, z), ...]

##### `get_road_center_lines(self, resolution=1.0)`
获取所有道路的中心线点序列。

**参数：**
- `resolution`: 采样分辨率（米），默认 1.0

**返回：**
- 道路中心线列表，每条道路是一个点序列

##### `get_statistics(self)`
获取解析统计信息。

**返回：**
- 统计信息字典，包含道路数量、交叉口数量、总长度等

## 使用示例

### 命令行快速转换

```bash
# 使用默认配置快速转换
python -c "from src.main import ShpToOpenDriveConverter; import json; config = json.load(open('config/example_config.json', 'r', encoding='utf-8')); converter = ShpToOpenDriveConverter(config); result = converter.convert('data/CenterLane.shp', 'output/CenterLane.xodr'); print('转换成功!' if result else '转换失败!')"

# 使用高精度配置转换
python -c "from src.main import ShpToOpenDriveConverter; import json; config = json.load(open('config/high_precision.json', 'r', encoding='utf-8')); converter = ShpToOpenDriveConverter(config); result = converter.convert('data/sample_roads.shp', 'output/sample_roads.xodr'); print('转换成功!' if result else '转换失败!')"
```

### 基本转换

```python
from src.opendrive_generator import OpenDriveGenerator

# 创建生成器
generator = OpenDriveGenerator()

# 从 Shapefile 生成 OpenDRIVE
xml_content = generator.create_opendrive_from_shapefile(
    'input.shp', 
    'output.xodr'
)
```

### 3D 可视化

```python
from src.visualizer import RoadVisualizer

# 创建可视化器
visualizer = RoadVisualizer()

# 启动可视化界面
visualizer.run()
```

### Web3D 可视化

```python
# 方法1：直接运行服务器脚本
python web_server.py

# 方法2：在代码中启动服务器
from flask import Flask
from web_server import app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

**Web API 使用示例：**

```javascript
// 上传SHP文件
const formData = new FormData();
formData.append('files', shpFile);
formData.append('files', shxFile);
formData.append('files', dbfFile);

fetch('/api/upload_shp', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        console.log('上传成功:', data.message);
        // 处理返回的GeoJSON数据
        renderGeoJSON(data.data);
    }
});

// 导出为OpenDRIVE格式
fetch('/api/export_xodr', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        fileName: 'export.xodr',
        crs: 'EPSG:4326',
        xodrVersion: '1.7',
        roadWidth: 3.5,
        laneCount: 2
    })
})
.then(response => response.blob())
.then(blob => {
    // 下载文件
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'export.xodr';
    a.click();
});
```

### OpenDRIVE 文件解析

```python
from src.xodr_parser import XODRParser

# 创建解析器
parser = XODRParser()

# 解析文件
data = parser.parse_file('road.xodr')

# 获取统计信息
stats = parser.get_statistics()
print(f"道路数量: {stats['roads_count']}")
print(f"总长度: {stats['total_length']:.2f}米")

# 生成中心线
center_lines = parser.get_road_center_lines(resolution=2.0)
```

## 支持的文件格式

### 输入格式
- **Shapefile (.shp)**: 包含道路几何的矢量数据
- **OpenDRIVE (.xodr)**: 标准的道路网络描述格式

### 输出格式
- **OpenDRIVE (.xodr)**: 标准的道路网络描述格式
- **PLY (.ply)**: 3D 点云格式
- **OBJ (.obj)**: 3D 模型格式
- **STL (.stl)**: 3D 打印格式
- **PCD (.pcd)**: 点云数据格式

## 依赖项

### 核心依赖
- `scenariogeneration>=0.13.0`: OpenDRIVE 生成
- `geopandas>=0.12.0`: 地理数据处理
- `shapely>=2.0.0`: 几何操作
- `numpy>=1.21.0`: 数值计算
- `lxml>=4.9.0`: XML 处理

### 可视化依赖
- `open3d>=0.18.0`: 3D 可视化和几何处理
- `tkinter`: GUI 界面（Python 标准库）

### Web服务依赖
- `flask>=2.0.0`: Web服务器框架
- `flask-cors>=4.0.0`: 跨域资源共享
- `werkzeug>=2.0.0`: WSGI工具库
- `tempfile`: 临时文件处理（Python 标准库）

### 可选依赖
- `matplotlib>=3.5.0`: 2D 绘图
- `folium>=0.14.0`: 交互式地图

### 开发依赖
- `pytest>=7.0.0`: 测试框架
- `black>=22.0.0`: 代码格式化
- `flake8>=4.0.0`: 代码检查

## 错误处理

所有主要方法都包含适当的错误处理机制：

- **文件不存在**: 抛出 `FileNotFoundError`
- **格式错误**: 抛出 `ValueError`
- **几何错误**: 抛出 `GeometryError`
- **XML 解析错误**: 抛出 `ET.ParseError`

## 性能注意事项

- 大型 Shapefile 文件可能需要较长的处理时间
- 3D 可视化的性能取决于几何复杂度和点密度
- 建议对大型数据集使用适当的采样分辨率
- OpenDRIVE 解析的内存使用量与文件大小成正比

## 版本信息

- **当前版本**: v1.4.0
- **Python版本要求**: >= 3.8
- **最后更新**: 2025年1月

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。