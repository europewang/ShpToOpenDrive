import geopandas as gpd
import sys

try:
    # 读取Lane.shp文件
    gdf = gpd.read_file('e:/Code/ShpToOpenDrive/data/testODsample/wh2000/Lane.shp')
    
    print('总记录数:', len(gdf))
    print('列名:', list(gdf.columns))
    
    print('\n前10条记录的RoadID和Index:')
    for i in range(min(10, len(gdf))):
        row = gdf.iloc[i]
        print(f'  记录{i}: RoadID={row["RoadID"]}, Index={row["Index"]}')
    
    print('\nRoadID统计 (前10个):')
    roadid_counts = gdf['RoadID'].value_counts().head(10)
    for roadid, count in roadid_counts.items():
        print(f'  RoadID {roadid}: {count} 条记录')
    
    # 查看第一个RoadID的所有Index
    first_roadid = roadid_counts.index[0]
    first_road_data = gdf[gdf['RoadID'] == first_roadid]
    print(f'\nRoadID {first_roadid} 的所有Index:')
    indices = sorted(first_road_data['Index'].tolist())
    print(f'  Index列表: {indices}')
    print(f'  Index数据类型: {type(indices[0])}')
    
except Exception as e:
    print(f'错误: {e}')
    import traceback
    traceback.print_exc()