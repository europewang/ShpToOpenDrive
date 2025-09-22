import shapefile

sf = shapefile.Reader('e:/Code/ShpToOpenDrive/data/testODsample/wh2000/Lane.shp')
print('Fields:', [field[0] for field in sf.fields[1:]])

records = sf.records()
print('\nFirst 10 records:')
for i, record in enumerate(records[:10]):
    print(f'Record {i}:', record)

print('\nTotal records:', len(records))

# 分析RoadID和Index字段
if len(records) > 0:
    field_names = [field[0] for field in sf.fields[1:]]
    print('\nField names:', field_names)
    
    # 查找RoadID和Index字段的索引
    roadid_idx = None
    index_idx = None
    
    for i, field_name in enumerate(field_names):
        if 'roadid' in field_name.lower() or 'road_id' in field_name.lower():
            roadid_idx = i
            print(f'Found RoadID field at index {i}: {field_name}')
        if 'index' in field_name.lower():
            index_idx = i
            print(f'Found Index field at index {i}: {field_name}')
    
    if roadid_idx is not None:
        roadids = [record[roadid_idx] for record in records]
        unique_roadids = sorted(set(roadids))
        print(f'\nUnique RoadID values: {unique_roadids[:10]}...' if len(unique_roadids) > 10 else f'\nUnique RoadID values: {unique_roadids}')
        print(f'Total unique RoadIDs: {len(unique_roadids)}')
    
    if index_idx is not None:
        indices = [record[index_idx] for record in records]
        unique_indices = sorted(set(indices))
        print(f'\nUnique Index values: {unique_indices}')
        print(f'Total unique Indices: {len(unique_indices)}')
    
    # 显示一些示例数据
    if roadid_idx is not None and index_idx is not None:
        print('\nSample data (RoadID, Index):')
        for i in range(min(20, len(records))):
            print(f'  {records[i][roadid_idx]}, {records[i][index_idx]}')