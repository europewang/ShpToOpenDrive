# Shapefile到OpenDrive转换器使用说明

## 项目概述

ShpToOpenDrive 是一个强大的工具，用于将 Shapefile 格式的道路数据转换为 OpenDrive 标准格式。现在支持两种输入格式：

- **传统道路格式**: 包含道路中心线的标准shapefile
- **Lane.shp格式**: 包含车道边界线的详细车道数据，支持变宽车道面

## 目录结构
- data/: 放置输入的shapefile文件
- output/: 转换后的OpenDrive文件输出目录
- config/: 配置文件目录
- src/: 源代码目录
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
python -c "from src.main import ShpToOpenDriveConverter; import json; config = json.load(open('config/example_config.json', 'r', encoding='utf-8')); converter = ShpToOpenDriveConverter(config); result = converter.convert('data/CenterLane.shp', 'output/CenterLane.xodr'); print('转换成功!' if result else '转换失败!')"

# 使用高精度配置转换
python -c "from src.main import ShpToOpenDriveConverter; import json; config = json.load(open('config/high_precision.json', 'r', encoding='utf-8')); converter = ShpToOpenDriveConverter(config); result = converter.convert('data/sample_roads.shp', 'output/sample_roads.xodr'); print('转换成功!' if result else '转换失败!')"
```

### Lane.shp格式转换
```bash
# 转换Lane.shp格式文件
python -c "from src.main import ShpToOpenDriveConverter; converter = ShpToOpenDriveConverter(); result = converter.convert('data/Lane.shp', 'output/Lane.xodr'); print('转换成功!' if result else '转换失败!')"

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

## 文件验证

### 验证生成的OpenDrive文件
```bash
# 验证所有输出文件
python validate_xodr.py
```

### 验证功能
- **格式验证**: 检查XML结构和OpenDrive标准合规性
- **版本检查**: 确保文件包含正确的版本信息（revMajor, revMinor）
- **统计信息**: 显示道路数量、车道数量、总长度等
- **合规性检查**: 检查地理参考信息和连接关系
- **批量验证**: 自动扫描output目录下所有.xodr文件

### 验证报告
验证脚本会生成详细报告，包括：
- ✓ 验证通过的文件
- ⚠️ 警告信息（如缺少推荐属性）
- ❌ 错误信息（如格式不正确）
- 📊 统计信息和验证通过率

## 版本信息

**当前版本**: v1.2.0

### 更新日志

#### v1.2.0 (2025-01-22)
- 🔧 修复 OpenDrive 文件根元素版本属性问题
- ✅ 新增 OpenDrive 文件格式验证功能
- 📈 改进验证逻辑，确保100%验证通过率
- 🎯 优化 XML 生成流程，符合 OpenDrive 1.7 标准
- 📋 完善API文档和使用说明

#### v1.1.0
- 支持Lane.shp格式转换
- 新增变宽车道面处理
- 优化几何算法

#### v1.0.0
- 基础Shapefile到OpenDrive转换功能
- 支持传统道路格式
- Web界面支持