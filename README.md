# Shapefile到OpenDrive转换器

一个用于将ArcGIS Shapefile格式的道路数据转换为OpenDrive格式的Python工具。

## 版本信息

**当前版本：v1.1.0**

### 更新日志

#### v1.1.0 (2024-01-XX)
- 🔧 **重要修复**：解决了多线条坐标系统问题
- ✅ 修复了每条线都从原点开始绘制的错误
- 🎯 优化了几何段坐标定义：只有第一个几何段使用绝对坐标
- 🔄 改进了几何连续性验证算法
- 📝 更新了API文档和使用说明

#### v1.0.0 (2024-01-XX)
- 🎉 初始版本发布
- 📁 支持Shapefile到OpenDrive转换
- 🗺️ 坐标系自动转换
- 📐 基础几何转换功能

## 功能特性

- 🗺️ **Shapefile读取**：支持读取包含道路几何和属性信息的shapefile文件
- 🔄 **坐标系转换**：自动转换坐标系到UTM投影坐标系
- 📐 **几何转换**：将离散点几何转换为OpenDrive参数化描述
- 🛣️ **道路生成**：生成符合OpenDrive 1.7标准的道路网络
- ⚙️ **灵活配置**：支持自定义转换参数和属性映射
- 📊 **转换统计**：提供详细的转换过程统计和报告

## 安装要求

### Python版本
- Python 3.7+

### 依赖包
```bash
pip install -r requirements.txt
```

主要依赖：
- `scenariogeneration`: OpenDrive文件生成
- `geopandas`: 地理数据处理
- `pyshp`: Shapefile读取
- `numpy`: 数值计算
- `scipy`: 科学计算
- `matplotlib`: 可视化（可选）

## 快速开始

### 1. 基本使用

```python
from src.main import ShpToOpenDriveConverter

# 创建转换器
converter = ShpToOpenDriveConverter()

# 执行转换
success = converter.convert(
    shapefile_path="data/roads.shp",
    output_path="output/roads.xodr"
)

if success:
    print("转换成功！")
else:
    print("转换失败！")
```

### 2. 运行示例

```bash
# 运行示例脚本
python example.py
```

### 3. 命令行使用

```bash
# 基本转换
python -m src.main input.shp output.xodr

# 自定义参数
python -m src.main input.shp output.xodr --tolerance 0.5 --use-arcs

# 生成转换报告
python -m src.main input.shp output.xodr --report report.json
```

## 配置选项

### 转换参数

```python
config = {
    'geometry_tolerance': 1.0,      # 几何拟合容差（米）
    'min_road_length': 10.0,        # 最小道路长度（米）
    'default_lane_width': 3.5,      # 默认车道宽度（米）
    'default_num_lanes': 1,         # 默认车道数
    'default_speed_limit': 50,      # 默认限速（km/h）
    'use_arc_fitting': False,       # 是否使用圆弧拟合
    'coordinate_precision': 3,      # 坐标精度（小数位数）
}

converter = ShpToOpenDriveConverter(config)
```

### 属性映射

如果你的shapefile包含道路属性，可以通过属性映射将其转换为OpenDrive属性：

```python
attribute_mapping = {
    'WIDTH': 'lane_width',      # 车道宽度
    'LANES': 'num_lanes',       # 车道数
    'SPEED': 'speed_limit',     # 限速
    'TYPE': 'road_type',        # 道路类型
    'NAME': 'road_name',        # 道路名称
}

converter.convert(
    shapefile_path="data/roads.shp",
    output_path="output/roads.xodr",
    attribute_mapping=attribute_mapping
)
```

## 项目结构

```
ShpToOpenDrive/
├── src/                    # 源代码目录
│   ├── __init__.py        # 包初始化
│   ├── main.py            # 主程序和转换器
│   ├── shp_reader.py      # Shapefile读取模块
│   ├── geometry_converter.py  # 几何转换模块
│   └── opendrive_generator.py # OpenDrive生成模块
├── data/                   # 输入数据目录
├── output/                 # 输出文件目录
├── config/                 # 配置文件目录
├── tests/                  # 测试文件目录
├── example.py             # 使用示例
├── requirements.txt       # 依赖包列表
└── README.md             # 项目说明
```

## 输入要求

### Shapefile格式

输入的shapefile应该包含：

1. **几何类型**：LineString或MultiLineString
2. **坐标系**：任何地理坐标系（程序会自动转换到UTM）
3. **属性字段**（可选）：
   - 道路宽度
   - 车道数
   - 限速
   - 道路类型
   - 道路名称

### 文件组成

确保shapefile的所有组成文件都存在：
- `.shp` - 几何数据
- `.shx` - 索引文件
- `.dbf` - 属性数据
- `.prj` - 投影信息（推荐）

## 输出格式

生成的OpenDrive文件符合OpenDrive 1.7标准，包含：

- **道路几何**：参数化的直线和圆弧段
- **车道信息**：车道宽度、数量和类型
- **道路属性**：限速、道路类型等
- **参考线**：基于输入几何的道路中心线

## 使用示例

### 示例1：基本转换

```python
from src.main import ShpToOpenDriveConverter

# 创建转换器
converter = ShpToOpenDriveConverter()

# 转换文件
success = converter.convert(
    "data/city_roads.shp", 
    "output/city_roads.xodr"
)

# 查看统计
stats = converter.get_conversion_stats()
print(f"转换了 {stats['output_roads']} 条道路")
print(f"总长度: {stats['total_length']:.2f} 米")
```

### 示例2：高精度转换

```python
# 高精度配置
high_precision_config = {
    'geometry_tolerance': 0.1,      # 10cm容差
    'use_arc_fitting': True,        # 使用圆弧拟合
    'coordinate_precision': 5,      # 5位小数精度
}

converter = ShpToOpenDriveConverter(high_precision_config)
converter.convert("data/highway.shp", "output/highway.xodr")
```

### 示例3：批量转换

```python
import os
from pathlib import Path

# 批量转换目录中的所有shapefile
input_dir = "data/"
output_dir = "output/batch/"

for shp_file in Path(input_dir).glob("*.shp"):
    output_file = os.path.join(output_dir, f"{shp_file.stem}.xodr")
    
    converter = ShpToOpenDriveConverter()
    success = converter.convert(str(shp_file), output_file)
    
    if success:
        print(f"✓ {shp_file.name} -> {output_file}")
    else:
        print(f"✗ {shp_file.name} 转换失败")
```

## 故障排除

### 常见问题

1. **坐标系问题**
   - 确保shapefile包含投影信息（.prj文件）
   - 检查坐标系是否为地理坐标系

2. **几何问题**
   - 检查道路几何是否连续
   - 调整`geometry_tolerance`参数
   - 使用`min_road_length`过滤短道路

3. **属性映射问题**
   - 检查shapefile属性字段名称
   - 确保数值字段格式正确

4. **内存问题**
   - 对于大文件，考虑分批处理
   - 调整几何简化参数

### 调试模式

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 启用详细日志
converter = ShpToOpenDriveConverter()
converter.convert("input.shp", "output.xodr")
```

## 性能优化

### 大文件处理

1. **增加容差**：`geometry_tolerance = 2.0`
2. **过滤短道路**：`min_road_length = 20.0`
3. **禁用圆弧拟合**：`use_arc_fitting = False`
4. **降低精度**：`coordinate_precision = 2`

### 内存优化

```python
# 内存优化配置
memory_config = {
    'geometry_tolerance': 2.0,
    'min_road_length': 20.0,
    'use_arc_fitting': False,
    'coordinate_precision': 2,
}
```

## 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 许可证

本项目采用MIT许可证。详见LICENSE文件。

## 联系方式

如有问题或建议，请通过以下方式联系：

- 创建Issue
- 发送邮件
- 提交Pull Request

## 更新日志

### v1.1.0
- 🔧 **坐标系转换修复**：修复了WGS84坐标系转换问题
- ✨ **新增局部坐标系转换**：添加`convert_to_local_coordinates()`方法
- 📍 **坐标处理优化**：确保OpenDrive文件坐标从(0,0)附近开始
- 🛠️ **三维坐标兼容**：改进对包含Z值的三维坐标数据的处理
- 📊 **增强日志记录**：添加详细的坐标转换过程日志
- 🎯 **精度改进**：避免大坐标值导致的精度问题

### v1.0.0
- 初始版本发布
- 支持基本的shapefile到OpenDrive转换
- 包含几何转换和属性映射功能
- 提供命令行和Python API接口