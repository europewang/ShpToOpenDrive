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

详细的转换流程和组件交互请参考：[docs/sequence_diagram.md](docs/sequence_diagram.md)

完整的API文档请参考：[docs/API_Documentation.md](docs/API_Documentation.md)

## 目录结构
- data/: 放置输入的shapefile文件
- output/: 转换后的OpenDrive文件输出目录
- config/: 配置文件目录
- src/: 源代码目录
- web/: Web界面相关文件
  - web_server.py: Web服务器主程序
  - templates/: HTML模板
  - js/: JavaScript文件
  - css/: 样式文件
- tests/: 测试文件目录

## 使用步骤
1. 将你的shapefile文件（.shp, .shx, .dbf等）放入data/目录
2. 根据文件格式选择合适的配置文件
3. 运行转换命令
4. 在output/目录查看生成的.xodr文件

## 快速转换命令

### 传统道路格式转换
```bash
# 使用默认配置快速转换
python -c "from src.main import ShpToOpenDriveConverter; import json; config = json.load(open('config/default.json', 'r', encoding='utf-8')); converter = ShpToOpenDriveConverter(config); result = converter.convert('data/CenterLane.shp', 'output/CenterLane.xodr'); print('转换成功!' if result else '转换失败!')"

# 使用高精度配置转换
python -c "from src.main import ShpToOpenDriveConverter; import json; config = json.load(open('config/high_precision.json', 'r', encoding='utf-8')); converter = ShpToOpenDriveConverter(config); result = converter.convert('data/sample_roads.shp', 'output/sample_roads.xodr'); print('转换成功!' if result else '转换失败!')"
```

### Lane.shp格式转换
```bash
# 转换Lane.shp格式文件
python -c "from src.main import ShpToOpenDriveConverter; converter = ShpToOpenDriveConverter(); result = converter.convert('data/Lane.shp', 'output/Lane.xodr'); print('转换成功!' if result else '转换失败!')"
```

## Web界面使用

### 启动Web服务器
```bash
# 进入web目录
cd web

# 启动Web服务器
python web_server.py
```

访问地址：http://localhost:5000

### Web界面功能
- 可视化文件上传和转换
- 3D道路预览
- 实时坐标显示
- 文件导出功能
- 支持多种文件格式（SHP、XODR）

# 使用自定义配置转换Lane.shp
python -c "from src.main import ShpToOpenDriveConverter; config = {'tolerance': 0.5, 'use_smooth_curves': True, 'preserve_detail': True}; converter = ShpToOpenDriveConverter(config); result = converter.convert('data/Lane.shp', 'output/Lane.xodr'); print('转换成功!' if result else '转换失败!')"
```

## 配置说明

### 通用配置参数
- geometry_tolerance: 几何拟合容差（米）
- min_road_length: 最小道路长度（米）
- default_lane_width: 默认车道宽度（米）
- default_num_lanes: 默认车道数
- default_speed_limit: 默认限速（km/h）
- use_arc_fitting: 是否使用圆弧拟合
- coordinate_precision: 坐标精度（小数位数）

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

### 传统格式输出
- 生成标准OpenDrive道路网络
- 支持圆弧拟合和直线段
- 统一车道宽度

### Lane.shp格式输出
- 支持变宽车道面
- 精确的车道边界
- 平滑的几何过渡
- 详细的车道信息

## 输出验证

生成的OpenDRIVE文件符合OpenDRIVE 1.7标准，包含：
- 标准XML结构和版本信息
- 完整的道路几何定义
- 准确的车道信息
- 地理参考坐标系

## 版本信息

**当前版本**: v1.2.0

### 更新日志

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