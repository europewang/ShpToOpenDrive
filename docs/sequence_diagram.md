# ShpToOpenDrive 序列图

本文档展示了 ShpToOpenDrive 项目从 Shapefile 到 OpenDRIVE 转换的完整流程。

## 主要转换流程序列图

```mermaid
sequenceDiagram
    participant User as 用户
    participant Main as ShpToOpenDriveConverter
    participant Reader as ShapefileReader
    participant Converter as GeometryConverter
    participant Generator as OpenDriveGenerator
    participant File as 文件系统

    User->>Main: convert(shapefile_path, output_path)
    Note over Main: 开始转换流程
    
    %% 步骤1: 加载Shapefile
    Main->>Reader: ShapefileReader(shapefile_path)
    Main->>Reader: load_shapefile()
    Reader->>File: 读取.shp, .shx, .dbf文件
    File-->>Reader: 返回shapefile数据
    Reader-->>Main: 加载成功/失败
    
    Main->>Reader: convert_to_utm()
    Reader-->>Main: 坐标系转换结果
    
    Main->>Reader: convert_to_local_coordinates()
    Reader-->>Main: 局部坐标系转换结果
    
    Main->>Reader: filter_roads_by_length(min_length)
    Reader-->>Main: 过滤后的道路数量
    
    Main->>Reader: get_road_info()
    Reader-->>Main: 道路基本信息
    
    %% 步骤2: 提取道路数据
    Main->>Reader: extract_road_geometries()
    Reader-->>Main: 道路几何数据
    
    alt Lane.shp格式
        Main->>Main: _process_lane_data()
        Note over Main: 处理车道面数据<br/>包含road_id, lanes, lane_surfaces
    else 传统格式
        Main->>Main: _process_traditional_data()
        Note over Main: 处理中心线数据<br/>包含coordinates, attributes
    end
    
    %% 步骤3: 几何转换
    Main->>Converter: GeometryConverter()
    
    alt Lane格式道路
        Main->>Converter: convert_lane_surface_geometry(lane_surfaces)
        Converter->>Converter: 计算车道中心线
        Converter->>Converter: 生成几何段(直线/圆弧)
        Converter->>Converter: 验证几何连续性
        Converter-->>Main: 转换后的车道面数据
    else 传统格式道路
        Main->>Converter: convert_road_geometry(coordinates)
        Converter->>Converter: 参数化几何(直线/圆弧拟合)
        Converter->>Converter: 平滑曲线处理
        Converter->>Converter: 验证几何连续性
        Converter-->>Main: 转换后的几何段
    end
    
    %% 步骤4: 生成OpenDRIVE
    Main->>Generator: OpenDriveGenerator(road_network_name)
    
    loop 每条道路
        alt Lane格式道路
            Main->>Generator: create_road_from_lane_surfaces(lane_surfaces, attributes)
            Generator->>Generator: 计算道路参考线
            Generator->>Generator: 创建车道剖面
            Generator->>Generator: 处理变宽车道
            Generator->>Generator: 添加车道标线
        else 传统格式道路
            Main->>Generator: create_road_from_segments(segments, attributes)
            Generator->>Generator: 创建道路几何
            Generator->>Generator: 添加车道信息
            Generator->>Generator: 设置道路属性
        end
        Generator-->>Main: 道路ID
    end
    
    Main->>Generator: validate_opendrive()
    Generator-->>Main: 验证结果
    
    Main->>Generator: generate_file(output_path)
    Generator->>File: 写入OpenDRIVE XML文件
    File-->>Generator: 文件写入结果
    Generator-->>Main: 生成成功/失败
    
    Main->>Generator: get_statistics()
    Generator-->>Main: 转换统计信息
    
    Main-->>User: 转换结果(成功/失败)
```

## 车道面处理详细流程

```mermaid
sequenceDiagram
    participant Main as ShpToOpenDriveConverter
    participant Reader as ShapefileReader
    participant Converter as GeometryConverter
    participant Generator as OpenDriveGenerator

    Note over Main,Generator: Lane.shp格式专用处理流程
    
    Main->>Reader: extract_road_geometries()
    Reader->>Reader: 按RoadID分组边界线
    Reader->>Reader: 按Index排序边界线
    Reader->>Reader: _build_lanes_from_boundaries()
    
    loop 相邻边界线对
        Reader->>Reader: 构建车道面(左边界+右边界)
        Reader->>Reader: _calculate_center_line()
        Reader->>Reader: _calculate_width_profile()
        Reader->>Reader: _merge_boundary_attributes()
    end
    
    Reader-->>Main: 车道面数据{road_id, lanes, lane_surfaces}
    
    Main->>Converter: convert_lane_surface_geometry(lane_surfaces)
    
    loop 每个车道面
        Converter->>Converter: 提取边界坐标
        Converter->>Converter: 计算中心线坐标
        Converter->>Converter: 计算宽度剖面
        Converter->>Converter: 生成几何段
    end
    
    Converter-->>Main: 转换后的车道面数据
    
    Main->>Generator: create_road_from_lane_surfaces()
    Generator->>Generator: _calculate_road_reference_line()
    
    Note over Generator: 查找index为'0'的边界线作为planview参考线
    
    loop 遍历所有车道面
        alt 找到index='0'的左边界
            Generator->>Generator: 使用左边界坐标作为参考线
            Note over Generator: 优先使用index='0'的左边界
        else 找到index='0'的右边界
            Generator->>Generator: 使用右边界坐标作为参考线
            Note over Generator: 回退到index='0'的右边界
        end
    end
    
    alt 未找到index='0'的边界线
        Generator->>Generator: 使用第一个车道面的中心线
        Note over Generator: 最终回退方案
    end
    
    Generator->>Converter: convert_road_geometry(reference_coords)
    Converter-->>Generator: 参考线几何段
    
    Generator->>Generator: _create_lane_section_from_surfaces()
    
    loop 每个车道面
        Generator->>Generator: 检测宽度变化
        alt 变宽车道
            Generator->>Generator: 创建多个width元素
        else 等宽车道
            Generator->>Generator: 创建单个width元素
        end
        Generator->>Generator: 添加车道标线
    end
    
    Generator-->>Main: 道路创建完成
```

## 几何转换详细流程

```mermaid
sequenceDiagram
    participant Converter as GeometryConverter
    participant Math as 数学计算模块
    participant Scipy as SciPy库

    Note over Converter,Scipy: 几何参数化处理
    
    Converter->>Converter: convert_road_geometry(coordinates)
    Converter->>Math: 计算线段长度和方向
    Converter->>Math: 检测直线段
    
    alt 使用圆弧拟合
        Converter->>Scipy: 圆弧拟合算法
        Scipy-->>Converter: 圆弧参数(半径, 中心点)
    else 直线拟合
        Converter->>Math: 直线段合并
        Math-->>Converter: 直线参数
    end
    
    alt 使用平滑曲线
        Converter->>Scipy: B样条插值
        Scipy-->>Converter: 平滑后的坐标
    end
    
    Converter->>Converter: validate_geometry_continuity()
    Converter->>Math: 检查几何连续性
    Math-->>Converter: 连续性验证结果
    
    Converter->>Converter: calculate_road_length()
    Converter-->>Converter: 几何段列表
```

## 文件生成流程

```mermaid
sequenceDiagram
    participant Generator as OpenDriveGenerator
    participant XODR as scenariogeneration库
    participant XML as XML处理
    participant File as 文件系统

    Note over Generator,File: OpenDRIVE文件生成
    
    Generator->>XODR: 创建OpenDrive对象
    Generator->>XODR: 设置版本信息(1.7)
    
    loop 每条道路
        Generator->>XODR: 创建Road对象
        Generator->>XODR: 添加几何信息(planView)
        Generator->>XODR: 添加车道信息(lanes)
        Generator->>XODR: 设置道路属性
    end
    
    Generator->>XODR: validate_opendrive()
    XODR-->>Generator: 验证结果
    
    Generator->>XODR: 生成XML内容
    XODR->>XML: 格式化XML
    XML-->>XODR: 格式化后的XML字符串
    XODR-->>Generator: XML内容
    
    Generator->>File: 写入.xodr文件
    File-->>Generator: 写入结果
    
    Generator->>Generator: get_statistics()
    Generator-->>Generator: 统计信息{roads_count, total_length, etc.}
```

## 边界线处理详细流程 (v1.3.0新增)

```mermaid
sequenceDiagram
    participant Reader as ShapefileReader
    participant Generator as OpenDriveGenerator
    participant Converter as GeometryConverter

    Note over Reader,Converter: 边界线到planview参考线的转换流程
    
    Reader->>Reader: extract_lane_geometries()
    Reader->>Reader: 按RoadID分组边界线数据
    
    loop 每个RoadID
        Reader->>Reader: 按Index字段排序边界线
        Reader->>Reader: _build_lanes_from_boundaries()
        
        loop i = 0 to len(boundaries)-2
            Reader->>Reader: 取相邻边界线[i]和[i+1]
            Reader->>Reader: 构建车道面{surface_id, left_boundary, right_boundary}
            Reader->>Reader: _calculate_center_line(left_coords, right_coords)
            Reader->>Reader: _calculate_width_profile(left_coords, right_coords)
            Reader->>Reader: _merge_boundary_attributes(left_attrs, right_attrs)
        end
    end
    
    Reader-->>Generator: lane_surfaces数据
    
    Generator->>Generator: _calculate_road_reference_line(lane_surfaces)
    
    Note over Generator: 查找index='0'的边界线策略
    
    loop 遍历所有车道面
        alt left_boundary.index == '0'
            Generator->>Generator: reference_coords = left_boundary.coordinates
            Note over Generator: 找到index='0'的左边界，优先使用
            break
        else right_boundary.index == '0'
            Generator->>Generator: reference_coords = right_boundary.coordinates
            Note over Generator: 找到index='0'的右边界，次选使用
            break
        end
    end
    
    alt reference_coords为空
        Generator->>Generator: 使用第一个车道面的center_line
        Note over Generator: 回退方案1：使用中心线
        alt center_line不存在
            Generator->>Generator: _calculate_center_line_coords()
            Note over Generator: 回退方案2：动态计算中心线
        end
    end
    
    Generator->>Converter: convert_road_geometry(reference_coords)
    Converter->>Converter: 坐标序列转换为几何段
    Converter-->>Generator: 标准化几何段列表
    
    Generator-->>Generator: planview参考线几何段
```

## 关键组件说明

### ShpToOpenDriveConverter (主控制器)
- 协调整个转换流程
- 管理配置参数和转换统计
- 处理不同格式的输入数据
- 支持Lane.shp和传统道路格式的自动识别

### ShapefileReader (数据读取)
- 读取和解析Shapefile文件
- 坐标系转换(WGS84 → UTM → 局部坐标)
- 数据预处理和过滤
- **新增**: 边界线处理和车道面构建功能
- **新增**: Lane.shp格式的自动检测和处理

### GeometryConverter (几何转换)
- 离散点到参数化几何的转换
- 直线和圆弧拟合算法
- 几何连续性验证
- **新增**: 车道面几何转换和中心线计算

### OpenDriveGenerator (文件生成)
- OpenDRIVE标准格式生成
- 车道面和变宽车道处理
- XML文件输出和验证
- **新增**: 基于边界线index的planview参考线计算
- **新增**: 支持index='0'边界线作为道路参考线

## 支持的数据格式

1. **传统道路格式**: 包含道路中心线的标准shapefile
2. **Lane.shp格式**: 包含车道边界线的详细车道数据，支持变宽车道面

## 输出特性

- 符合OpenDRIVE 1.7标准
- 支持复杂几何(直线、圆弧)
- 支持变宽车道建模
- 包含完整的车道信息和道路标记
- 自动验证和统计报告