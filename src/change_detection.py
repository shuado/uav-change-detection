"""
变化检测模块

功能：
- 对比两个时期的图斑
- 识别新增、消失、变化的图斑
- 计算变化面积和坐标
"""
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
import numpy as np
from typing import Tuple, Dict
from loguru import logger


class ChangeDetection:
    """变化检测器"""
    
    def __init__(self, iou_threshold: float = 0.5):
        """
        初始化变化检测器
        
        Args:
            iou_threshold: IoU阈值，用于判断是否为同一图斑
        """
        self.iou_threshold = iou_threshold
        logger.info(f"变化检测器初始化，IoU阈值: {iou_threshold}")
    
    def calculate_iou(self, geom1: Polygon, geom2: Polygon) -> float:
        """
        计算两个多边形的IoU（交并比）
        
        Args:
            geom1: 多边形1
            geom2: 多边形2
            
        Returns:
            IoU值
        """
        if not geom1.intersects(geom2):
            return 0.0
        
        intersection = geom1.intersection(geom2).area
        union = geom1.union(geom2).area
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def detect_changes(self, gdf_t1: gpd.GeoDataFrame, gdf_t2: gpd.GeoDataFrame) -> Dict:
        """
        检测两个时期图斑的变化
        
        Args:
            gdf_t1: 时期1的图斑GeoDataFrame
            gdf_t2: 时期2的图斑GeoDataFrame
            
        Returns:
            包含新增、消失、变化图斑的字典
        """
        logger.info(f"开始变化检测，T1: {len(gdf_t1)}个图斑, T2: {len(gdf_t2)}个图斑")
        
        # 新增图斑（T2有但T1没有）
        new_polygons = []
        # 消失图斑（T1有但T2没有）
        disappeared_polygons = []
        # 变化图斑（类别或形状变化）
        changed_polygons = []
        
        # 标记T1中已匹配的图斑
        t1_matched = set()
        
        # 遍历T2图斑
        for idx2, row2 in gdf_t2.iterrows():
            geom2 = row2.geometry
            class2 = row2.class_id
            
            # 查找与当前T2图斑最匹配的T1图斑
            best_iou = 0
            best_idx1 = None
            
            for idx1, row1 in gdf_t1.iterrows():
                if idx1 in t1_matched:
                    continue
                
                geom1 = row1.geometry
                iou = self.calculate_iou(geom1, geom2)
                
                if iou > best_iou:
                    best_iou = iou
                    best_idx1 = idx1
            
            # 判断变化类型
            if best_iou < self.iou_threshold:
                # 新增图斑
                new_polygons.append({
                    'geometry': geom2,
                    'class_id': class2,
                    'class_name': row2.get('class_name', f"类别_{class2}"),
                    'area_m2': geom2.area,
                    'centroid_x': geom2.centroid.x,
                    'centroid_y': geom2.centroid.y,
                    'change_type': '新增'
                })
            else:
                # 匹配到T1图斑
                t1_matched.add(best_idx1)
                row1 = gdf_t1.loc[best_idx1]
                geom1 = row1.geometry
                class1 = row1.class_id
                
                # 检查类别是否变化
                if class1 != class2:
                    changed_polygons.append({
                        'geometry_t1': geom1,
                        'geometry_t2': geom2,
                        'class_id_t1': class1,
                        'class_id_t2': class2,
                        'class_name_t1': row1.get('class_name', f"类别_{class1}"),
                        'class_name_t2': row2.get('class_name', f"类别_{class2}"),
                        'area_m2_t1': geom1.area,
                        'area_m2_t2': geom2.area,
                        'area_change_m2': geom2.area - geom1.area,
                        'centroid_x': geom2.centroid.x,
                        'centroid_y': geom2.centroid.y,
                        'iou': best_iou,
                        'change_type': '类别变化'
                    })
                # 如果类别相同但面积变化超过20%，也记录
                elif abs(geom2.area - geom1.area) / geom1.area > 0.2:
                    changed_polygons.append({
                        'geometry_t1': geom1,
                        'geometry_t2': geom2,
                        'class_id_t1': class1,
                        'class_id_t2': class2,
                        'class_name_t1': row1.get('class_name', f"类别_{class1}"),
                        'class_name_t2': row2.get('class_name', f"类别_{class2}"),
                        'area_m2_t1': geom1.area,
                        'area_m2_t2': geom2.area,
                        'area_change_m2': geom2.area - geom1.area,
                        'centroid_x': geom2.centroid.x,
                        'centroid_y': geom2.centroid.y,
                        'iou': best_iou,
                        'change_type': '面积变化'
                    })
        
        # 消失图斑（T1中未被匹配的）
        for idx1 in set(gdf_t1.index) - t1_matched:
            row1 = gdf_t1.loc[idx1]
            geom1 = row1.geometry
            disappeared_polygons.append({
                'geometry': geom1,
                'class_id': row1.class_id,
                'class_name': row1.get('class_name', f"类别_{row1.class_id}"),
                'area_m2': geom1.area,
                'centroid_x': geom1.centroid.x,
                'centroid_y': geom1.centroid.y,
                'change_type': '消失'
            })
        
        logger.info(f"变化检测完成: 新增{len(new_polygons)}个, 消失{len(disappeared_polygons)}个, 变化{len(changed_polygons)}个")
        
        return {
            'new': new_polygons,
            'disappeared': disappeared_polygons,
            'changed': changed_polygons
        }
    
    def changes_to_geodataframe(self, changes: Dict) -> gpd.GeoDataFrame:
        """
        将变化结果转换为GeoDataFrame
        
        Args:
            changes: 变化检测结果字典
            
        Returns:
            合并的GeoDataFrame
        """
        all_features = []
        
        # 新增图斑
        for item in changes['new']:
            all_features.append({
                'geometry': item['geometry'],
                'class_id': item['class_id'],
                'class_name': item['class_name'],
                'area_m2': item['area_m2'],
                'centroid_x': item['centroid_x'],
                'centroid_y': item['centroid_y'],
                'change_type': '新增',
                'area_change_m2': item['area_m2'],
                'class_name_from': '',
                'class_name_to': item['class_name']
            })
        
        # 消失图斑
        for item in changes['disappeared']:
            all_features.append({
                'geometry': item['geometry'],
                'class_id': item['class_id'],
                'class_name': item['class_name'],
                'area_m2': item['area_m2'],
                'centroid_x': item['centroid_x'],
                'centroid_y': item['centroid_y'],
                'change_type': '消失',
                'area_change_m2': -item['area_m2'],
                'class_name_from': item['class_name'],
                'class_name_to': ''
            })
        
        # 变化图斑（使用T2的几何）
        for item in changes['changed']:
            all_features.append({
                'geometry': item['geometry_t2'],
                'class_id': item['class_id_t2'],
                'class_name': item['class_name_t2'],
                'area_m2': item['area_m2_t2'],
                'centroid_x': item['centroid_x'],
                'centroid_y': item['centroid_y'],
                'change_type': item['change_type'],
                'area_change_m2': item['area_change_m2'],
                'class_name_from': item['class_name_t1'],
                'class_name_to': item['class_name_t2']
            })
        
        if not all_features:
            return gpd.GeoDataFrame()
        
        gdf = gpd.GeoDataFrame(all_features, crs="EPSG:4326")
        logger.info(f"创建变化GeoDataFrame，共 {len(gdf)} 个变化图斑")
        
        return gdf
    
    def calculate_statistics(self, changes: Dict) -> Dict:
        """
        计算变化统计信息
        
        Args:
            changes: 变化检测结果
            
        Returns:
            统计字典
        """
        stats = {
            'total_changes': len(changes['new']) + len(changes['disappeared']) + len(changes['changed']),
            'new_count': len(changes['new']),
            'disappeared_count': len(changes['disappeared']),
            'changed_count': len(changes['changed']),
            'new_area': sum(item['area_m2'] for item in changes['new']),
            'disappeared_area': sum(item['area_m2'] for item in changes['disappeared']),
            'changed_area': sum(abs(item['area_change_m2']) for item in changes['changed'])
        }
        
        logger.info(f"变化统计: 总计{stats['total_changes']}个变化, "
                   f"新增{stats['new_count']}个({stats['new_area']:.2f}m²), "
                   f"消失{stats['disappeared_count']}个({stats['disappeared_area']:.2f}m²), "
                   f"变化{stats['changed_count']}个({stats['changed_area']:.2f}m²)")
        
        return stats


# 使用示例
if __name__ == "__main__":
    # 测试变化检测
    detector = ChangeDetection(iou_threshold=0.5)
    
    # 需要实际的gdf_t1和gdf_t2数据
    # changes = detector.detect_changes(gdf_t1, gdf_t2)
    # change_gdf = detector.changes_to_geodataframe(changes)
    # stats = detector.calculate_statistics(changes)
