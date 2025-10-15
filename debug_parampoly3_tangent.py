#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ET
import math

def debug_parampoly3_tangent(xodr_file):
    """调试ParamPoly3的切线方向问题"""
    
    tree = ET.parse(xodr_file)
    root = tree.getroot()

    print(f'=== ParamPoly3切线方向调试: {xodr_file} ===')

    for road in root.findall('.//road'):
        road_id = road.get('id')
        
        for geometry in road.findall('.//geometry'):
            x = float(geometry.get('x'))
            y = float(geometry.get('y'))
            hdg = float(geometry.get('hdg'))
            
            parampoly3 = geometry.find('paramPoly3')
            if parampoly3 is not None:
                aU = float(parampoly3.get('aU'))
                bU = float(parampoly3.get('bU'))
                cU = float(parampoly3.get('cU'))
                dU = float(parampoly3.get('dU'))
                aV = float(parampoly3.get('aV'))
                bV = float(parampoly3.get('bV'))
                cV = float(parampoly3.get('cV'))
                dV = float(parampoly3.get('dV'))
                
                print(f'\n道路 {road_id}:')
                print(f'  XODR定义的起点航向角: {math.degrees(hdg):.2f}°')
                
                # 计算起点切线方向（t=0时的导数）
                du_dt_0 = bU  # t=0时，u'(0) = bU
                dv_dt_0 = bV  # t=0时，v'(0) = bV
                
                # 局部坐标系中的切线角度
                local_tangent_angle = math.atan2(dv_dt_0, du_dt_0)
                print(f'  局部坐标系切线角度: {math.degrees(local_tangent_angle):.2f}°')
                
                # 转换到全局坐标系的切线角度
                global_tangent_angle = hdg + local_tangent_angle
                print(f'  全局坐标系切线角度: {math.degrees(global_tangent_angle):.2f}°')
                
                # 检查是否一致
                angle_diff = abs(global_tangent_angle - hdg)
                if angle_diff > math.pi:
                    angle_diff = 2 * math.pi - angle_diff
                
                print(f'  角度差异: {math.degrees(angle_diff):.2f}°')
                
                if angle_diff > 0.01:  # 0.01弧度 ≈ 0.57度
                    print(f'  ❌ 切线方向不一致！')
                    print(f'     期望的局部切线角度应为: 0.00°')
                    print(f'     期望的bU: {math.sqrt(bU*bU + bV*bV):.6f}')
                    print(f'     期望的bV: 0.000000')
                else:
                    print(f'  ✅ 切线方向一致')
                
                # 分析ParamPoly3参数
                print(f'  ParamPoly3参数分析:')
                print(f'    bU={bU:.6f}, bV={bV:.6f}')
                print(f'    切线长度: {math.sqrt(bU*bU + bV*bV):.6f}')
                print(f'    切线方向: ({bU/math.sqrt(bU*bU + bV*bV):.6f}, {bV/math.sqrt(bU*bU + bV*bV):.6f})')

if __name__ == "__main__":
    debug_parampoly3_tangent('output/simple_test.xodr')