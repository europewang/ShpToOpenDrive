# API Documentation

## `GeometryConverter` Class

### `_apply_connection_consistency(self, center_coords, surface_id, predecessors, successors, connection_manager)`

应用连接一致性调整，确保起终点斜率、宽度和位置与前后继道路面一致。

此方法现在还包括航向角一致性调整，通过调整道路中心线的第二个点（针对前继）或倒数第二个点（针对后继）来匹配连接处的平均航向角。

**Args:**
- `center_coords` (List[Tuple[float, float]]): 原始中心线坐标。
- `surface_id` (str): 当前道路面ID。
- `predecessors` (List[str]): 前继道路面ID列表。
- `successors` (List[str]): 后继道路面ID列表。
- `connection_manager` (RoadConnectionManager): 道路连接管理器。

**Returns:**
- `List[Tuple[float, float]]`: 调整后的中心线坐标。

### `_calculate_heading(self, p1, p2)`

计算两点之间的航向角 (弧度)。

**Args:**
- `p1` (Tuple[float, float]): 第一个点 (x, y)。
- `p2` (Tuple[float, float]): 第二个点 (x, y)。

**Returns:**
- `float`: 航向角 (弧度)。

### `_calculate_center_line(self, left_coords, right_coords)`

计算两条边界线的中心线和对应的宽度变化。宽度现在通过计算左边界起点和右边界起点的距离作为起始宽度，左边界终点和右边界终点的距离作为终点宽度，然后对这些宽度进行平滑插值来确定。

**Args:**
- `left_coords` (List[Tuple[float, float]]): 左边界坐标点。
- `right_coords` (List[Tuple[float, float]]): 右边界坐标点。

**Returns:**
- `Tuple[List[Tuple[float, float]], List[Dict]]`: (中心线坐标点, 宽度变化数据)。

### `_apply_slope_consistency(self, center_coords, surface_id, predecessors, successors, connection_manager)`

此方法现在仅返回原始中心线坐标。所有连接一致性调整（包括斜率）已转移到 `_apply_connection_consistency` 方法中处理。

**Args:**
- `center_coords` (List[Tuple[float, float]]): 原始中心线坐标。
- `surface_id` (str): 当前道路面ID。
- `predecessors` (List[str]): 前继道路面ID列表。
- `successors` (List[str]): 后继道路面ID列表。
- `connection_manager` (RoadConnectionManager): 道路连接管理器。

**Returns:**
- `List[Tuple[float, float]]`: 原始中心线坐标。

### `_calculate_width_profile(self, center_line_coords, left_boundary_coords, right_boundary_coords, length)`

计算道路的宽度剖面。此方法现在通过计算道路起点和终点的宽度，然后对这些宽度进行线性插值来确定每个中心线点的宽度，从而生成更平滑和更准确的宽度变化。

**Args:**
- `center_line_coords` (List[Tuple[float, float]]): 中心线坐标点。
- `left_boundary_coords` (List[Tuple[float, float]]): 左边界坐标点。
- `right_boundary_coords` (List[Tuple[float, float]]): 右边界坐标点。
- `length` (float): 道路的长度。

**Returns:**
- `List[Dict]`: 包含每个中心线点宽度信息的列表。