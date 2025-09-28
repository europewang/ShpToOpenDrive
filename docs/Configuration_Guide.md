# 配置文件使用指南

本文档详细介绍了 ShpToOpenDrive 项目中各种配置文件的使用方法和参数说明。

## 配置文件概述

项目提供了多种预设配置文件，适用于不同的转换场景和精度要求：

- `default.json` - 默认配置，适合大多数场景
- `high_precision.json` - 高精度配置，适合精确建模
- `fast_processing.json` - 快速处理配置，适合大文件批量转换
- `urban_roads.json` - 城市道路配置，针对城市路网优化
- `lane_format.json` - Lane.shp格式专用配置
- `polynomial_curves.json` - 多项式曲线拟合配置
- `spline_curves.json` - 样条曲线拟合配置

## 配置文件结构

### 基本参数

```json
{
  "description": "配置文件描述",
  "geometry_tolerance": 1.0,        // 几何拟合容差（米）
  "min_road_length": 1.0,           // 最小道路长度（米）
  "default_lane_width": 3.5,        // 默认车道宽度（米）
  "default_num_lanes": 1,           // 默认车道数
  "default_speed_limit": 50,        // 默认限速（km/h）
  "use_arc_fitting": false,         // 是否使用圆弧拟合
  "use_smooth_curves": true,        // 使用平滑曲线
  "preserve_detail": true,          // 保留细节
  "coordinate_precision": 3         // 坐标精度（小数位数）
}
```

### 高级参数

```json
{
  "curve_fitting_mode": "polynomial",  // 曲线拟合模式
  "polynomial_degree": 3,              // 多项式次数
  "curve_smoothness": 0.4,             // 曲线平滑度 (0-1)
  "attribute_mapping": {               // 属性映射
    "WIDTH": "lane_width",
    "LANES": "num_lanes",
    "SPEED": "speed_limit"
  }
}
```

## 详细配置说明

### 1. default.json - 默认配置

**适用场景：** 一般道路转换，平衡精度和性能

**主要特点：**
- 几何容差：1.0米
- 启用平滑曲线和细节保留
- 3位小数精度
- 使用三次多项式拟合

**推荐用途：**
- 标准道路网络转换
- 初次使用和测试
- 中等精度要求的项目

### 2. high_precision.json - 高精度配置

**适用场景：** 需要厘米级精度的高精度建模

**主要特点：**
- 几何容差：0.1米（高精度）
- 最小道路长度：0.5米（保留短道路）
- 5位小数精度
- 启用圆弧拟合

**推荐用途：**
- 自动驾驶仿真
- 精密道路设计
- 科研项目

**注意事项：**
- 处理时间较长
- 输出文件较大
- 内存占用较高

### 3. fast_processing.json - 快速处理配置

**适用场景：** 大文件和批量转换，优先处理速度

**主要特点：**
- 几何容差：5.0米（低精度，高速度）
- 最小道路长度：50米（过滤小道路）
- 禁用圆弧拟合
- 2位小数精度
- 启用简化和内存优化

**推荐用途：**
- 大型城市道路网络
- 批量数据处理
- 快速原型制作

**性能优化：**
```json
"performance_settings": {
  "simplification_enabled": true,
  "batch_processing": true,
  "memory_optimization": true
}
```

### 4. urban_roads.json - 城市道路配置

**适用场景：** 城市道路网络，包含交叉口和复杂路网

**主要特点：**
- 默认双向2车道
- 限速40km/h（城市标准）
- 车道宽度3.0米
- 支持单行道属性
- 包含人行道和自行车道设置

**城市道路专用设置：**
```json
"road_settings": {
  "default_road_type": "urban",
  "bidirectional_default": true,
  "intersection_handling": true,
  "traffic_signals": true
},
"lane_settings": {
  "sidewalk_width": 1.5,
  "parking_lane_width": 2.5,
  "bike_lane_width": 1.5
}
```

### 5. lane_format.json - Lane.shp格式专用配置

**适用场景：** 处理包含车道边界线的Lane.shp格式数据

**主要特点：**
- 自动检测Lane格式
- 支持RoadID和Index属性
- 启用车道面几何转换
- 支持变宽车道建模

**Lane格式专用设置：**
```json
"lane_format_settings": {
  "enabled": true,
  "road_id_field": "RoadID",
  "index_field": "Index",
  "auto_detect_lane_format": true,
  "lane_surface_generation": {
    "enabled": true,
    "width_interpolation": "linear",
    "center_line_calculation": "midpoint",
    "width_sampling_points": 50
  }
}
```

**验证设置：**
```json
"validation": {
  "check_index_continuity": true,
  "min_lanes_per_road": 2,
  "max_width_variation": 10.0
}
```

### 6. polynomial_curves.json - 多项式曲线配置

**适用场景：** 需要平滑曲线且保持高精度的场景

**主要特点：**
- 使用三次多项式拟合
- 平衡精度和平滑度
- 适中的平滑效果（0.4）
- 4位小数精度

**曲线拟合参数：**
```json
"curve_fitting_mode": "polynomial",
"polynomial_degree": 3,
"curve_smoothness": 0.4
```

### 7. spline_curves.json - 样条曲线配置

**适用场景：** 需要极度平滑曲线的高速公路场景

**主要特点：**
- 使用样条曲线拟合
- 最高平滑度（0.2）
- 优先平滑度而非细节
- 适合高速公路

**平滑度设置：**
```json
"curve_fitting_mode": "spline",
"curve_smoothness": 0.2,
"preserve_detail": false
```

## 配置文件使用方法

### 1. 命令行方式

```bash
# 使用默认配置
python src/main.py input.shp output.xodr

# 使用指定配置文件
python src/main.py input.shp output.xodr --config config/high_precision.json
```

### 2. Python脚本方式

```python
import json
from src.main import ShpToOpenDriveConverter

# 加载配置文件
with open('config/high_precision.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 创建转换器
converter = ShpToOpenDriveConverter(config)

# 执行转换
result = converter.convert('input.shp', 'output.xodr')
```

### 3. 自定义配置

```python
# 自定义配置参数
custom_config = {
    'geometry_tolerance': 0.5,
    'min_road_length': 2.0,
    'default_lane_width': 3.2,
    'use_arc_fitting': True,
    'coordinate_precision': 4
}

converter = ShpToOpenDriveConverter(custom_config)
```

## 参数详细说明

### 几何参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `geometry_tolerance` | float | 1.0 | 几何拟合容差（米），越小越精确 |
| `min_road_length` | float | 1.0 | 最小道路长度（米），过滤短道路 |
| `use_arc_fitting` | bool | false | 是否使用圆弧拟合 |
| `use_smooth_curves` | bool | true | 是否使用平滑曲线 |
| `preserve_detail` | bool | true | 是否保留细节 |
| `coordinate_precision` | int | 3 | 坐标精度（小数位数） |

### 车道参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `default_lane_width` | float | 3.5 | 默认车道宽度（米） |
| `default_num_lanes` | int | 1 | 默认车道数 |
| `default_speed_limit` | int | 50 | 默认限速（km/h） |

### 曲线拟合参数

| 参数 | 类型 | 可选值 | 说明 |
|------|------|--------|------|
| `curve_fitting_mode` | string | polynomial, spline, parampoly3 | 曲线拟合模式 |
| `polynomial_degree` | int | 2-5 | 多项式次数 |
| `curve_smoothness` | float | 0.0-1.0 | 曲线平滑度，0最粗糙，1最平滑 |

### 属性映射

属性映射用于将Shapefile中的字段映射到OpenDRIVE标准属性：

```json
"attribute_mapping": {
  "WIDTH": "lane_width",      // 车道宽度
  "LANES": "num_lanes",       // 车道数
  "SPEED": "speed_limit",     // 限速
  "TYPE": "road_type",        // 道路类型
  "NAME": "road_name",        // 道路名称
  "ONEWAY": "bidirectional",  // 单行道
  "SURFACE": "surface_type"   // 路面类型
}
```

## 性能优化建议

### 大文件处理

1. **使用fast_processing.json配置**
2. **增大几何容差**（5.0米或更大）
3. **提高最小道路长度**（50米或更大）
4. **禁用圆弧拟合**
5. **降低坐标精度**（2位小数）

### 高精度要求

1. **使用high_precision.json配置**
2. **减小几何容差**（0.1米或更小）
3. **启用圆弧拟合**
4. **提高坐标精度**（5位小数）
5. **保留细节设置**

### 内存优化

```json
"performance_settings": {
  "simplification_enabled": true,
  "batch_processing": true,
  "memory_optimization": true
}
```

## 配置文件验证

系统会自动验证配置文件的有效性：

1. **必需参数检查**：确保所有必需参数存在
2. **数值范围验证**：检查参数值是否在有效范围内
3. **类型检查**：验证参数类型是否正确
4. **逻辑一致性**：检查参数组合是否合理

## 故障排除

### 常见问题

1. **转换精度不足**
   - 减小`geometry_tolerance`
   - 增加`coordinate_precision`
   - 启用`preserve_detail`

2. **处理速度慢**
   - 增大`geometry_tolerance`
   - 禁用`use_arc_fitting`
   - 启用性能优化设置

3. **输出文件过大**
   - 减少`coordinate_precision`
   - 增大`min_road_length`
   - 启用简化设置

4. **Lane.shp格式识别失败**
   - 检查`RoadID`和`Index`字段
   - 启用`auto_detect_lane_format`
   - 验证数据格式

### 调试技巧

1. **启用详细日志**
2. **使用小数据集测试**
3. **逐步调整参数**
4. **检查转换统计信息**

## 最佳实践

1. **选择合适的配置**：根据数据特点和精度要求选择配置
2. **测试小数据集**：先用小数据集测试配置效果
3. **监控性能指标**：关注处理时间和内存使用
4. **备份原始数据**：转换前备份原始Shapefile
5. **验证输出结果**：使用验证工具检查输出质量

---

*配置文件指南最后更新时间: 2025年1月*