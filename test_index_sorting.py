import sys
sys.path.append('src')
from shp_reader import ShapefileReader
import pandas as pd

print("=== 测试Index排序问题 ===")

# 创建测试数据
test_data = {
    'RoadID': [4044, 4044, 4044, 4044, 4044, 4044],
    'Index': ['0', '1', '2', '3', '4', '5']
}

df = pd.DataFrame(test_data)
print("原始数据:")
print(df)

print("\n字符串排序结果:")
df_str_sorted = df.sort_values('Index')
print(df_str_sorted)

print("\n数字排序结果:")
try:
    df_num_sorted = df.sort_values('Index', key=lambda x: x.astype(int))
    print(df_num_sorted)
except Exception as e:
    print(f"数字排序失败: {e}")

# 测试更复杂的Index值
test_data2 = {
    'RoadID': [4044] * 12,
    'Index': ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11']
}

df2 = pd.DataFrame(test_data2)
print("\n=== 复杂Index测试 ===")
print("原始数据:")
print(df2['Index'].tolist())

print("\n字符串排序结果:")
df2_str_sorted = df2.sort_values('Index')
print(df2_str_sorted['Index'].tolist())

print("\n数字排序结果:")
try:
    df2_num_sorted = df2.sort_values('Index', key=lambda x: x.astype(int))
    print(df2_num_sorted['Index'].tolist())
except Exception as e:
    print(f"数字排序失败: {e}")

# 测试实际数据
print("\n=== 测试实际Lane.shp数据 ===")
try:
    reader = ShapefileReader('e:/Code/ShpToOpenDrive/data/testODsample/wh2000/Lane.shp')
    reader.load_shapefile()
    
    # 获取第一个RoadID的数据
    first_roadid = reader.gdf['RoadID'].iloc[0]
    group = reader.gdf[reader.gdf['RoadID'] == first_roadid]
    
    print(f"RoadID {first_roadid} 的Index值:")
    print(f"原始顺序: {group['Index'].tolist()}")
    
    # 字符串排序
    group_str_sorted = group.sort_values('Index')
    print(f"字符串排序: {group_str_sorted['Index'].tolist()}")
    
    # 数字排序
    try:
        group_num_sorted = group.sort_values('Index', key=lambda x: x.astype(int))
        print(f"数字排序: {group_num_sorted['Index'].tolist()}")
    except Exception as e:
        print(f"数字排序失败: {e}")
        
except Exception as e:
    print(f"测试实际数据失败: {e}")

print("\n测试完成")