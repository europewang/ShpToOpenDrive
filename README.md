# Shapefile到OpenDrive转换器使用说明

## 项目概述

ShpToOpenDrive 是一个强大的工具，用于将 Shapefile 格式的道路数据转换为 OpenDrive 标准格式。现在支持两种输入格式：

- **传统道路格式**: 包含道路中心线的标准shapefile
- **Lane.shp格式**: 包含车道边界线的详细车道数据，支持变宽车道面

## 系统架构

项目采用模块化设计，主要包含以下核心组件：

- **ShpToOpenDriveConverter**: 主控制器，协调整个转换流程
- **ShapefileReader**: 数据读取模块，处理shapefile文件和坐标转换
- **GeometryConverter**: 几何转换模块，将离散点转换为参数化几何
- **OpenDriveGenerator**: 文件生成模块，输出标准OpenDRIVE格式
- **XodrToObjConverter**: 新增的3D模型转换器，将OpenDRIVE文件转换为OBJ格式
- **XodrParser**: OpenDRIVE文件解析器，支持文件验证和数据提取

详细的转换流程和组件交互请参考：[docs/sequence_diagram.md](docs/sequence_diagram.md)

完整的API文档请参考：[docs/API_Documentation.md](docs/API_Documentation.md)

## 目录结构
```
ShpToOpenDrive/
├── data/                    # 测试数据目录
│   ├── test_lane/          # 普通测试数据
│   └── testODsample/       # 高级测试数据
│       ├── wh2000/         # 标准测试集
│       └── LaneTest.shp    # 进阶测试文件
├── output/                 # 转换结果输出目录
├── config/                 # 配置文件目录
│   ├── default.json        # 默认配置
│   ├── high_precision.json # 高精度配置
│   ├── lane_format.json    # Lane格式专用配置
│   └── ...                 # 其他专用配置
├── src/                    # 源代码目录
│   ├── shp2xodr.py        # SHP到XODR转换脚本（主程序）
│   ├── xodr2obj.py        # XODR到OBJ转换脚本
│   ├── shp_reader.py      # Shapefile读取器
│   ├── geometry_converter.py # 几何转换器
│   ├── opendrive_generator.py # OpenDRIVE生成器
│   ├── xodr_parser.py     # OpenDRIVE解析器
│   ├── xodr_to_obj_converter.py # 3D模型转换器核心
│   └── visualizer.py      # 可视化工具
├── web/                   # Web界面
│   ├── web_server.py      # Web服务器
│   ├── templates/         # HTML模板
│   ├── js/               # JavaScript文件
│   ├── css/              # 样式文件
│   └── static/           # 静态资源
├── logs/                 # 日志文件目录
├── docs/                 # 文档目录
├── test_testlane.py      # 测试脚本
└── requirements.txt      # 依赖包列表
```

## 快速开始

### 环境准备
```bash
# 1. 激活conda环境
conda activate shp2opendrive

# 2. 进入项目目录
cd E:\Code\ShpToOpenDrive

# 3. 安装依赖（首次使用）
pip install -r requirements.txt
```

### 基本使用步骤
1. 将你的shapefile文件（.shp, .shx, .dbf等）放入data/目录
2. 根据文件格式选择合适的配置文件
3. 运行转换命令
4. 在output/目录查看生成的.xodr文件

## 转换脚本使用方法

### 1. SHP到XODR转换 (shp2xodr.py)

#### 基本语法
```bash
python src/shp2xodr.py <输入文件> <输出文件> [选项]
```

#### 命令行参数
- `input`: 输入shapefile路径（必需）
- `output`: 输出OpenDrive文件路径（必需）
- `--config`: 配置文件路径（可选）
- `--tolerance`: 几何拟合容差，单位米（默认1.0）
- `--min-length`: 最小道路长度，单位米（默认1.0）
- `--use-arcs`: 启用圆弧拟合（可选）
- `--report`: 转换报告输出路径（可选）
- `--verbose`: 启用详细日志输出（可选）
- `--validate`: 验证输出文件格式（可选）

#### 命令行使用示例
```bash
# 基本转换
python src/shp2xodr.py data/test_lane/TestLane.shp output/TestLane.xodr

# 使用高精度配置
python src/shp2xodr.py data/testODsample/wh2000/Lane.shp output/Lane.xodr --config config/high_precision.json

# 自定义参数转换
python src/shp2xodr.py data/testODsample/LaneTest.shp output/LaneTest.xodr --tolerance 0.5 --min-length 2.0 --use-arcs

# 生成详细报告
python src/shp2xodr.py data/test_lane/TestLane.shp output/TestLane.xodr --report output/conversion_report.json --verbose

# 转换并验证输出
python src/shp2xodr.py data/testODsample/wh2000/Lane.shp output/Lane.xodr --validate

# 快速处理大文件
python src/shp2xodr.py large_dataset.shp output/large_dataset.xodr --config config/fast_processing.json
```

### 2. XODR到OBJ转换 (xodr2obj.py)

#### 基本语法
```bash
python src/xodr2obj.py <输入XODR文件> <输出OBJ文件> [选项]
```

#### 新功能特性 (v3.1.0)
- **🎨 多车道材质支持**: 为每个车道生成独立的材质和颜色
- **🔧 改进的网格算法**: 基于libOpenDRIVE的高精度车道边界计算
- **📁 自动材质分组**: 根据车道ID自动生成材质名称（如lane_1, lane_neg_1等）
- **📄 双文件输出**: 同时生成.obj网格文件和.mtl材质文件

#### 命令行参数
- `input`: 输入XODR文件路径（必需）
- `output`: 输出OBJ文件路径（必需）
- `--resolution, -r`: 采样分辨率（米），默认0.5米
- `--with-height`: 包含车道高度信息
- `--with-objects`: 包含道路对象（实验性功能）
- `--eps`: 网格生成精度，默认0.1米
- `--high-quality`: 高质量模式（分辨率0.1米，包含高度信息）
- `--verbose, -v`: 显示详细输出信息
- `--quiet, -q`: 静默模式，只显示错误信息

#### 命令行使用示例
```bash
# 基本转换（支持多车道材质）
python src/xodr2obj.py output/TestLane.xodr output/TestLane.obj

# 高精度多车道转换
python src/xodr2obj.py output/Lane.xodr output/Lane.obj --resolution 0.1 --with-height

# 高质量模式（推荐用于多车道场景）
python src/xodr2obj.py output/LaneTest.xodr output/LaneTest.obj --high-quality

# 详细输出模式（查看车道材质生成过程）
python src/xodr2obj.py output/TestLane.xodr output/TestLane.obj --verbose

# 静默模式
python src/xodr2obj.py output/Lane.xodr output/Lane.obj --quiet

# 完整多车道转换流程示例
python src/shp2xodr.py data/testODsample/LaneTest.shp output/LaneTest.xodr
python src/xodr2obj.py output/LaneTest.xodr output/LaneTest_multi.obj --high-quality
# 输出文件：LaneTest_multi.obj（网格）+ LaneTest_multi.mtl（多车道材质）

# 测试多车道材质功能
python src/xodr2obj.py output/wh2000_test.xodr output/wh2000_multi.obj 0.5 --debug
```

### 3. Python脚本方式

#### SHP到XODR转换
```python
from src.shp2xodr import ShpToOpenDriveConverter

# 创建转换器实例
converter = ShpToOpenDriveConverter()

# 执行转换
success = converter.convert(
    'data/test_lane/TestLane.shp',
    'output/TestLane.xodr'
)

if success:
    print("转换成功！")
else:
    print("转换失败！")
```

#### 使用配置文件
```python
import json
from src.shp2xodr import ShpToOpenDriveConverter

# 加载配置文件
with open('config/high_precision.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 创建转换器
converter = ShpToOpenDriveConverter(config)

# 执行转换
result = converter.convert(
    'data/testODsample/wh2000/Lane.shp',
    'output/Lane.xodr'
)
```

#### XODR到OBJ转换（支持多车道材质）
```python
from src.xodr_to_obj_converter import XODRToOBJConverter

# 创建转换器实例（v3.1.0支持多车道材质）
converter = XODRToOBJConverter(
    resolution=0.5,  # 网格分辨率
    lane_width=3.5   # 默认车道宽度
)

# 执行多车道转换
success = converter.convert(
    'output/TestLane.xodr',
    'output/TestLane_multi.obj'  # 自动生成.mtl材质文件
)

if success:
    print("多车道3D模型转换成功！")
    print("输出文件：")
    print("- TestLane_multi.obj（网格数据）")
    print("- TestLane_multi.mtl（车道材质）")
    
    # 获取转换统计信息
    stats = converter.get_conversion_stats()
    print(f"生成车道数量: {stats.get('lane_count', 0)}")
    print(f"材质分组数量: {stats.get('material_groups', 0)}")
else:
    print("3D模型转换失败！")
```

#### 完整转换流程
```python
from src.shp2xodr import ShpToOpenDriveConverter
from src.xodr_to_obj_converter import XODRToOBJConverter

# 第一步：SHP到XODR
shp_converter = ShpToOpenDriveConverter()
xodr_success = shp_converter.convert(
    'data/testODsample/LaneTest.shp',
    'output/LaneTest.xodr'
)

if xodr_success:
    print("XODR转换成功！")
    
    # 第二步：XODR到OBJ
    obj_converter = XODRToOBJConverter(
        resolution=0.1,
        with_lane_height=True
    )
    obj_success = obj_converter.convert(
        'output/LaneTest.xodr',
        'output/LaneTest.obj'
    )
    
    if obj_success:
        print("完整转换流程成功！")
    else:
        print("OBJ转换失败！")
else:
    print("XODR转换失败！")
```

#### 自定义配置
```python
from src.main import ShpToOpenDriveConverter

# 自定义配置
config = {
    'geometry_tolerance': 0.5,
    'use_smooth_curves': True,
    'preserve_detail': True,
    'default_lane_width': 3.5,
    'coordinate_precision': 3
}

# 创建转换器
converter = ShpToOpenDriveConverter(config)

# 执行转换
result = converter.convert(
    'data/testODsample/LaneTest.shp',
    'output/LaneTest.xodr'
)
```

### 3. 测试用例

#### 普通测试
```bash
# 使用测试脚本
python test_testlane.py

# 或直接调用shp2xodr.py
python src/shp2xodr.py data/test_lane/TestLane.shp output/TestLane.xodr
```

#### 标准测试
```bash
# 标准测试数据集
python src/shp2xodr.py data/testODsample/wh2000/Lane.shp output/wh2000_Lane.xodr
```

#### 进阶测试
```bash
# 进阶测试数据
python src/shp2xodr.py data/testODsample/LaneTest.shp output/LaneTest_advanced.xodr
```

### 4. XODR文件解析和3D转换

#### XODR文件解析
```python
from src.xodr_parser import XODRParser

# 创建解析器
parser = XODRParser()

# 解析XODR文件
header, roads, junctions = parser.parse_file('output/TestLane.xodr')

# 查看解析结果
print(f"道路数量: {len(roads)}")
print(f"交叉口数量: {len(junctions)}")

# 生成道路点云数据
for road in roads:
    points = parser.generate_road_points(road, step=1.0)
    print(f"道路 {road['id']} 包含 {len(points)} 个点")
```

#### 3D模型转换（多车道支持）
```python
from src.xodr_to_obj_converter import XODRToOBJConverter

# 创建3D转换器（v3.1.0支持多车道材质）
converter = XODRToOBJConverter(
    resolution=0.5,  # 网格分辨率
    lane_width=3.5   # 默认车道宽度
)

# 转换XODR到多车道OBJ格式
success = converter.convert('output/TestLane.xodr', 'output/TestLane_multi.obj')

if success:
    print("多车道3D模型转换成功！")
    print("输出文件：")
    print("- TestLane_multi.obj（3D网格，包含车道分组）")
    print("- TestLane_multi.mtl（车道材质定义）")
    print("可以在Blender、3ds Max等3D软件中打开，每个车道有独立材质")
    
    # 查看转换统计
    stats = converter.get_conversion_stats()
    print(f"\n转换统计：")
    print(f"- 车道数量: {stats.get('lane_count', 0)}")
    print(f"- 顶点数量: {stats.get('vertex_count', 0)}")
    print(f"- 面片数量: {stats.get('face_count', 0)}")
    print(f"- 材质分组: {stats.get('material_groups', 0)}")
else:
    print("3D模型转换失败！")
```

#### 批量转换和处理
```python
import os
from src.main import ShpToOpenDriveConverter
from src.xodr_to_obj_converter import XODRToOBJConverter

# 批量转换SHP到XODR
shp_converter = ShpToOpenDriveConverter()
obj_converter = XODRToOBJConverter()

data_dir = 'data/batch_processing'
output_dir = 'output/batch_results'

for filename in os.listdir(data_dir):
    if filename.endswith('.shp'):
        shp_path = os.path.join(data_dir, filename)
        xodr_path = os.path.join(output_dir, filename.replace('.shp', '.xodr'))
        obj_path = os.path.join(output_dir, filename.replace('.shp', '.obj'))
        
        # SHP -> XODR
        if shp_converter.convert(shp_path, xodr_path):
            print(f"✓ {filename} -> XODR 转换成功")
            
            # XODR -> OBJ
            if obj_converter.convert(xodr_path, obj_path):
                print(f"✓ {filename} -> OBJ 转换成功")
            else:
                print(f"✗ {filename} -> OBJ 转换失败")
        else:
            print(f"✗ {filename} -> XODR 转换失败")
```

## Web前端使用指南 (v1.3.0)

### 1. 启动Web服务器

#### 方法一：直接启动
```bash
# 激活环境
conda activate shp2opendrive

# 进入web目录
cd web

# 启动Web服务器
python web_server.py
```

#### 方法二：从项目根目录启动
```bash
# 激活环境
conda activate shp2opendrive

# 在项目根目录下启动
python web/web_server.py
```

服务器启动后，访问地址：**http://localhost:5000**

### 2. Web界面功能详解 (v1.3.0 重大更新)

#### 🎨 全新苹果风格设计
- **简洁美观**: 采用苹果风格灰白色调设计，界面简洁流畅
- **响应式布局**: 支持不同屏幕尺寸，自适应显示
- **优化交互**: 流畅的动画效果和用户体验
- **现代化UI**: 圆角设计、阴影效果、渐变色彩

#### 📁 智能文件管理
- **拖拽上传**: 支持拖拽文件到界面直接上传
- **多格式支持**: 自动识别SHP、XODR、OBJ等格式
- **智能验证**: 实时检查文件完整性和格式正确性
- **清屏功能**: 一键清除所有文件，无需确认弹窗
- **批量处理**: 支持多文件批量上传和转换
- **格式验证**: 自动检测和验证文件格式完整性

#### ⚙️ 高级转换选项
- **配置文件选择**: 提供多种预设配置（默认、高精度、Lane格式等）
- **参数调整**: 几何容差、曲线拟合、细节保留等选项
- **导出模式**: 支持XODR、SHP、OBJ多种格式导出
- **质量控制**: OBJ转换支持质量模式选择
- **实时反馈**: 转换进度和结果实时显示，支持错误诊断

#### 🎯 3D可视化增强
- **实时渲染**: OpenDRIVE文件的实时3D预览
- **交互控制**: 鼠标缩放、旋转、平移操作
- **信息显示**: 道路几何信息实时显示（坐标、方向、曲率）
- **视角重置**: 优化的相机位置，更好的观察角度
- **性能优化**: 支持大规模道路网络流畅渲染
- **基于Three.js**: 高性能3D渲染引擎

#### 界面布局
- **左侧面板**: 文件上传区域和操作控制
- **右侧主区域**: 3D可视化窗口
- **底部状态栏**: 显示坐标信息和操作提示

#### 操作指南
1. **文件上传**
   - 点击"选择文件"或直接拖拽SHP文件到上传区域
   - 系统自动检测文件格式（传统道路/Lane格式）
   - 支持批量上传相关文件（.shp, .shx, .dbf, .prj）
   - 实时显示文件大小和格式验证结果
   - 支持文件预览和属性检查

2. **转换设置**
   - 选择预设配置文件（默认、高精度、快速处理等）
   - 自定义几何容差、车道宽度、最小道路长度等参数
   - 选择输出格式（XODR、OBJ）和质量等级
   - 配置坐标系统和投影参数
   - 设置验证选项和报告生成

3. **3D预览操作**
   - **鼠标左键**: 旋转视角
   - **鼠标右键**: 平移视图
   - **滚轮**: 缩放视图
   - **左键点击道路**: 显示道路详细信息
   - **重置视角**: 点击重置按钮恢复默认视角

4. **道路信息查看**
   - 点击任意道路线条查看详细信息
   - 显示内容包括：
     - 道路ID和名称
     - 线条长度（米）
     - 坐标点数和采样密度
     - 起始点坐标(X,Y)
     - 结束点坐标(X,Y)
     - X/Y坐标范围和边界框
     - 车道数量和宽度信息
     - 道路类型和限速信息

5. **文件导出**
   - 转换完成后自动生成下载链接
   - 支持下载OpenDRIVE(.xodr)文件
   - 可选择下载OBJ 3D模型文件
   - 支持下载详细转换报告（JSON/PDF格式）
   - 提供转换统计信息和质量评估报告

### 3. API接口 (v1.3.0)

Web界面提供完整的RESTful API接口：

#### 文件转换接口
- `POST /api/export_xodr` - SHP到XODR转换
- `POST /api/export_shp` - 数据导出为SHP格式
- `POST /api/convert_xodr_to_obj` - XODR到OBJ转换（支持质量模式）
- `POST /api/save_obj_data` - 保存OBJ数据
- `POST /api/convert_obj_to_obj` - OBJ格式转换

#### 文件管理接口
- `POST /api/upload_xodr` - 上传XODR文件
- `GET /api/download/<filename>` - 下载生成的文件
- `DELETE /api/clear` - 清除所有临时文件

### 4. 故障排除

#### 常见问题
1. **服务器无法启动**
   - 检查端口5000是否被占用
   - 确认Python环境和依赖包正确安装
   - 查看控制台错误信息

2. **文件上传失败**
   - 确认文件格式正确（需要完整的shapefile文件集）
   - 检查文件大小限制
   - 验证文件编码格式

3. **3D预览异常**
   - 检查浏览器WebGL支持
   - 更新浏览器到最新版本
   - 清除浏览器缓存

4. **转换失败**
   - 查看浏览器开发者工具控制台
   - 检查服务器日志文件
   - 验证输入数据格式和完整性

# 使用自定义配置转换Lane.shp
python -c "from src.main import ShpToOpenDriveConverter; config = {'tolerance': 0.5, 'use_smooth_curves': True, 'preserve_detail': True}; converter = ShpToOpenDriveConverter(config); result = converter.convert('data/Lane.shp', 'output/Lane.xodr'); print('转换成功!' if result else '转换失败!')"
```

## 配置说明

### 配置文件详细指南

项目提供了多种预设配置文件，详细说明请参考：[docs/Configuration_Guide.md](docs/Configuration_Guide.md)

### 通用配置参数
- `geometry_tolerance`: 几何拟合容差（米），影响转换精度
- `min_road_length`: 最小道路长度（米），过滤短道路段
- `default_lane_width`: 默认车道宽度（米），用于缺失宽度信息的车道
- `default_num_lanes`: 默认车道数，用于传统格式道路
- `default_speed_limit`: 默认限速（km/h），用于缺失限速信息的道路
- `use_arc_fitting`: 是否使用圆弧拟合，提高曲线精度
- `coordinate_precision`: 坐标精度（小数位数），影响输出文件大小
- `use_smooth_curves`: 是否使用平滑曲线处理
- `preserve_detail`: 是否保留原始几何细节

### 高级配置参数
- `curve_fitting_mode`: 曲线拟合模式（polynomial/spline/parampoly3）
- `polynomial_degree`: 多项式拟合次数（2-5）
- `curve_smoothness`: 曲线平滑度（0.0-1.0）
- `attribute_mapping`: 属性字段映射配置
- `validation`: 数据验证和质量检查配置
- `performance_settings`: 性能优化配置

### Lane.shp格式专用配置
- use_smooth_curves: 是否使用平滑曲线（默认：True）
- preserve_detail: 是否保留细节（默认：True）
- tolerance: 几何处理容差（默认：1.0）
- lane_format_settings: Lane格式专用设置
  - enabled: 是否启用Lane格式处理（默认：True）
  - road_id_field: 道路ID字段名（默认：'RoadID'）
  - index_field: 索引字段名（默认：'Index'）

## 数据格式要求

### 传统道路格式
- 几何类型：LineString（道路中心线）
- 必需属性：无（可选属性见下方映射）

### Lane.shp格式
- 几何类型：Polygon（车道面）
- 必需属性：
  - RoadID: 道路唯一标识符
  - Index: 车道索引（用于排序）
- 可选属性：
  - WIDTH: 车道宽度
  - SPEED: 限速
  - TYPE: 车道类型

#### 变宽车道支持
系统现在能够自动检测和处理变宽车道：
- **自动检测**：通过分析车道面的边界线间距变化，自动识别变宽车道
- **精确计算**：沿车道中心线计算每个位置的精确宽度
- **OpenDRIVE兼容**：生成符合OpenDRIVE标准的多个`<width>`元素
- **阈值控制**：宽度变化超过0.1米时识别为变宽车道，否则视为等宽车道
- **详细日志**：输出变宽车道的检测结果和宽度变化范围

## 属性映射

### 传统格式属性映射
如果你的shapefile包含道路属性，可以通过attribute_mapping参数映射到OpenDrive属性：
- WIDTH -> lane_width
- LANES -> num_lanes  
- SPEED -> speed_limit
- TYPE -> road_type

### Lane.shp格式属性映射
Lane.shp格式自动识别以下属性：
- RoadID -> 道路分组标识
- Index -> 车道排序
- WIDTH -> 车道宽度
- SPEED -> 限速
- TYPE -> 车道类型

## 输出特性

### OpenDRIVE格式输出
- **标准兼容**: 符合OpenDRIVE 1.7标准规范
- **几何精度**: 支持直线、圆弧、螺旋线、多项式曲线
- **车道信息**: 完整的车道宽度、类型、限速信息
- **坐标系统**: 保持原始坐标系统或转换为标准投影
- **验证支持**: 内置格式验证，确保文件正确性

### 传统格式输出特点
- 生成标准OpenDrive道路网络结构
- 支持圆弧拟合和直线段组合
- 统一车道宽度配置
- 自动生成道路连接关系

### Lane.shp格式输出特点
- 支持变宽车道面精确建模
- 基于边界线的精确车道边界计算
- 平滑的几何过渡和宽度变化
- 详细的车道属性和索引信息
- 自动检测和处理复杂车道几何

### 3D模型输出（OBJ格式）- v3.1.0多车道增强
- **🎨 多车道材质支持**: 每个车道自动生成独立材质和颜色
- **🔧 高质量网格**: 基于libOpenDRIVE几何生成精确3D网格
- **📁 智能材质分组**: 根据车道ID自动命名（lane_1, lane_neg_1等）
- **📄 双文件输出**: 同时生成.obj网格文件和.mtl材质文件
- **🎯 车道级渲染**: 支持单独车道的3D可视化和材质编辑
- **⚡ 优化性能**: 自适应网格密度，平衡质量和性能
- **🔗 标准兼容**: 支持主流3D软件导入（Blender、3ds Max、Maya等）

#### 多车道材质特性
- **自动颜色分配**: 每个车道使用不同的材质颜色
- **材质属性完整**: 包含环境光、漫反射、镜面反射等完整材质属性
- **车道ID映射**: 正向车道（lane_1, lane_2...）和负向车道（lane_neg_1, lane_neg_2...）
- **3D软件友好**: 在3D软件中可直接选择和编辑单个车道材质

## 输出验证和质量保证

### 自动验证功能
生成的OpenDRIVE文件经过多层验证，确保符合OpenDRIVE 1.7标准：

1. **XML结构验证**
   - 标准XML格式和编码检查
   - 必需元素和属性完整性验证
   - 版本信息和命名空间正确性

2. **几何一致性验证**
   - 道路几何连续性检查
   - 车道宽度合理性验证
   - 坐标系统一致性确认

3. **数据质量检查**
   - 道路长度和车道数量统计
   - 几何精度和拟合质量评估
   - 属性映射完整性检查

### 质量报告
转换完成后可生成详细的质量报告，包含：
- 转换统计信息（道路数量、总长度等）
- 几何质量评估（拟合误差、精度指标）
- 数据完整性检查结果
- 潜在问题和改进建议

### 验证工具
```bash
# 使用内置验证功能
python src/shp2xodr.py input.shp output.xodr --validate

# 单独验证已有XODR文件
python -c "from src.xodr_parser import XODRParser; parser = XODRParser(); result = parser.validate_file('output.xodr'); print('验证通过' if result else '验证失败')"
```

## 版本信息

**当前版本**: v1.3.0

### 更新日志

#### v1.3.0 (2025-01-22)
- 🎨 **Web界面全面优化**：
  - 全新苹果风格界面设计，灰白色调简洁美观
  - 清屏功能直接执行，移除确认弹窗
  - 简化导出选项，删除冗余的OpenDRIVE和SHP导出参数
  - 优化3D道路可视化，支持实时交互和信息查看
  - 改进重置视角功能，相机位置更加合理
- 🔧 **API接口扩展**：
  - 新增export_xodr、export_shp、convert_xodr_to_obj等完整API接口
  - 支持质量模式选择和双模式操作
  - 完善文件管理接口，支持上传、下载、清除操作
  - 优化错误处理和用户提示
- 🚀 **核心功能增强**：
  - 新增XodrToObjConverter模块，支持OpenDRIVE到OBJ格式转换
  - 完善XodrParser解析器，增强文件验证和数据提取能力
  - 优化道路参考线算法，提高几何精度
  - 改进道路宽度识别算法，支持变宽车道处理
- 📚 **文档完善**：
  - 全面更新README文档，添加详细使用指南
  - 完善API文档，记录所有新增接口
  - 新增Web前端使用指南和故障排除
  - 更新项目结构和配置说明

#### v1.2.0 (2025-01-22)
- 🔧 修复 OpenDrive 文件根元素版本属性问题
- ✅ 新增 OpenDrive 文件格式验证功能
- 📈 改进验证逻辑，确保100%验证通过率
- 🎯 优化 XML 生成流程，符合 OpenDrive 1.7 标准
- 📋 完善API文档和使用说明

#### v1.1.0 (2024-01-XX)
- **重大改进**：优化车道宽度计算算法
  - 基于参考线几何段进行精确的s坐标计算
  - 计算垂直于参考线方向的车道宽度，提高精度
  - 支持复杂几何形状（直线、螺旋线、圆弧）
  - 新增多个辅助方法提升算法稳定性
- 完善API文档，添加新增方法的详细说明
- 添加调试配置支持TestLane.shp文件
- 优化错误处理和回退机制
- 支持Lane.shp格式转换
- 新增变宽车道面处理
- 优化几何算法

#### v1.0.0
- 基础Shapefile到OpenDrive转换功能
- 支持传统道路格式
- Web界面支持