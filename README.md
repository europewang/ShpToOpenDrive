# Shapefile到OpenDrive转换器使用说明

## 目录结构
- data/: 放置输入的shapefile文件
- output/: 转换后的OpenDrive文件输出目录
- config/: 配置文件目录

## 使用步骤
1. 将你的shapefile文件（.shp, .shx, .dbf等）放入data/目录
2. 运行 python example.py
3. 在output/目录查看生成的.xodr文件

## 快速转换命令
```bash
# 使用默认配置快速转换
python -c "from src.main import ShpToOpenDriveConverter; import json; config = json.load(open('config/example_config.json', 'r', encoding='utf-8')); converter = ShpToOpenDriveConverter(config); result = converter.convert('data/CenterLane.shp', 'output/CenterLane.xodr'); print('转换成功!' if result else '转换失败!')"

# 使用高精度配置转换
python -c "from src.main import ShpToOpenDriveConverter; import json; config = json.load(open('config/high_precision.json', 'r', encoding='utf-8')); converter = ShpToOpenDriveConverter(config); result = converter.convert('data/sample_roads.shp', 'output/sample_roads.xodr'); print('转换成功!' if result else '转换失败!')"
```

## 配置说明
- geometry_tolerance: 几何拟合容差（米）
- min_road_length: 最小道路长度（米）
- default_lane_width: 默认车道宽度（米）
- default_num_lanes: 默认车道数
- default_speed_limit: 默认限速（km/h）
- use_arc_fitting: 是否使用圆弧拟合
- coordinate_precision: 坐标精度（小数位数）

## 属性映射
如果你的shapefile包含道路属性，可以通过attribute_mapping参数映射到OpenDrive属性：
- WIDTH -> lane_width
- LANES -> num_lanes  
- SPEED -> speed_limit
- TYPE -> road_type