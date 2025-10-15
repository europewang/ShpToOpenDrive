#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ET
import math

def analyze_xodr_geometry(xodr_file):
    """详细分析XODR文件中的几何定义"""
    
    # 解析XODR文件
    tree = ET.parse(xodr_file)
    root = tree.getroot()

    print(f'=== 详细几何分析: {xodr_file} ===')

    for road in root.findall('.//road'):
        road_id = road.get('id')
        print(f'\n道路 {road_id}:')
        
        # 查找几何定义
        for geometry in road.findall('.//geometry'):
            s = float(geometry.get('s'))
            x = float(geometry.get('x'))
            y = float(geometry.get('y'))
            hdg = float(geometry.get('hdg'))
            length = float(geometry.get('length'))
            
            print(f'  起点: s={s}, x={x:.6f}, y={y:.6f}')
            print(f'  起点航向角: {hdg:.6f} 弧度 = {math.degrees(hdg):.2f}°')
            print(f'  长度: {length}')
            
            # 检查是否有ParamPoly3
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
                
                print(f'  ParamPoly3: aU={aU}, bU={bU}, cU={cU}, dU={dU}')
                print(f'             aV={aV}, bV={bV}, cV={cV}, dV={dV}')
                
                # 计算终点坐标 (t=1)
                u_end = aU + bU + cU + dU
                v_end = aV + bV + cV + dV
                
                # 计算终点在全局坐标系中的位置
                cos_hdg = math.cos(hdg)
                sin_hdg = math.sin(hdg)
                x_end = x + u_end * cos_hdg - v_end * sin_hdg
                y_end = y + u_end * sin_hdg + v_end * cos_hdg
                
                print(f'  终点: x={x_end:.6f}, y={y_end:.6f}')
                
                # 计算终点航向角
                du_dt = bU + 2*cU + 3*dU  # t=1时的导数
                dv_dt = bV + 2*cV + 3*dV
                
                # 局部坐标系中的航向角
                local_hdg = math.atan2(dv_dt, du_dt)
                # 转换到全局坐标系
                global_end_hdg = hdg + local_hdg
                
                print(f'  终点航向角: {global_end_hdg:.6f} 弧度 = {math.degrees(global_end_hdg):.2f}°')
                
                # 检查中间点的曲率变化
                print(f'  曲线分析:')
                for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
                    u_t = aU + bU*t + cU*t*t + dU*t*t*t
                    v_t = aV + bV*t + cV*t*t + dV*t*t*t
                    
                    x_t = x + u_t * cos_hdg - v_t * sin_hdg
                    y_t = y + u_t * sin_hdg + v_t * cos_hdg
                    
                    du_dt_t = bU + 2*cU*t + 3*dU*t*t
                    dv_dt_t = bV + 2*cV*t + 3*dV*t*t
                    
                    local_hdg_t = math.atan2(dv_dt_t, du_dt_t)
                    global_hdg_t = hdg + local_hdg_t
                    
                    print(f'    t={t}: ({x_t:.2f}, {y_t:.2f}), hdg={math.degrees(global_hdg_t):.2f}°')
                    
            else:
                # 直线段
                cos_hdg = math.cos(hdg)
                sin_hdg = math.sin(hdg)
                x_end = x + length * cos_hdg
                y_end = y + length * sin_hdg
                print(f'  终点: x={x_end:.6f}, y={y_end:.6f}')
                print(f'  终点航向角: {hdg:.6f} 弧度 = {math.degrees(hdg):.2f}°')

if __name__ == "__main__":
    analyze_xodr_geometry('output/simple_test.xodr')