"""
图斑矢量化模块

功能：
- 从分割掩膜提取多边形
- 图斑简化和过滤
- 输出GeoJSON格式（WGS84坐标）
"""
import numpy as np
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape, mapping
from shapely.ops import transform
import geopandas as gpd
from typing import List, Dict
from loguru import logger
from functools import partial
import pyproj


class Vectorization:
    """图斑矢量化器"""
    
    def __init__(self, min_area: float = 100.0, simplify_tolerance: float = 1.0):
        """
        初始化矢量化器
        
        Args:
            min_area: 最小图斑面积（平方米）
            simplify_tolerance: 简化容差（米）
        """
        self.min_area = min_area
        self.simplify_tolerance = simplify_tolerance
        logger.info(f"矢量化器初始化，最小面积: {min_area}m², 简化容差: {simplify_tolerance}m")
    
    def mask_to_polygons(self, mask: np.ndarray, transform: rasterio.Affine, crs: str = "EPSG:4326") -> gpd.GeoDataFrame:
        """
        将分割掩膜转换为多边形
        
        Args:
            mask: 分割掩膜 (height, width)，值为类别ID
            transform: 仿射变换参数
            crs: 坐标系
            
        Returns:
            GeoDataFrame包含所有图斑
        """
        logger.info(f"开始矢量化，掩膜尺寸: {mask.shape}")
        
        # 提取所有多边形
        polygons = []
        values = []
        
        for geom, val in shapes(mask.astype(np.uint8), mask=mask > 0, transform=transform):
            polygons.append(shape(geom))
            values.append(int(val))
        
        logger.info(f"提取 {len(polygons)} 个原始图斑")
        
        if not polygons:
            logger.warning("未提取到任何图斑")
            return gpd.GeoDataFrame()
        
        # 创建GeoDataFrame
        gdf = gpd.GeoDataFrame({
            'class_id': values,
            'geometry': polygons
        }, crs=crs)
        
        # 计算面积
        gdf['area_m2'] = gdf.geometry.area
        
        # 过滤小图斑
        before_count = len(gdf)
        gdf = gdf[gdf['area_m2'] >= self.min_area].copy()
        logger.info(f"过滤小图斑: {before_count} -> {len(gdf)}")
        
        # 简化多边形
        gdf['geometry'] = gdf.geometry.simplify(self.simplify_tolerance, preserve_topology=True)
        logger.info(f"多边形简化完成，容差: {self.simplify_tolerance}m")
        
        # 计算质心
        gdf['centroid_x'] = gdf.geometry.centroid.x
        gdf['centroid_y'] = gdf.geometry.centroid.y
        
        return gdf
    
    def add_class_names(self, gdf: gpd.GeoDataFrame, class_names: List[str]) -> gpd.GeoDataFrame:
        """
        添加类别名称
        
        Args:
            gdf: GeoDataFrame
            class_names: 类别名称列表
            
        Returns:
            添加了类别名称的GeoDataFrame
        """
        gdf = gdf.copy()
        gdf['class_name'] = gdf['class_id'].apply(lambda x: class_names[x] if x < len(class_names) else f"类别_{x}")
        return gdf
    
    def to_geojson(self, gdf: gpd.GeoDataFrame, output_path: str):
        """
        导出为GeoJSON
        
        Args:
            gdf: GeoDataFrame
            output_path: 输出文件路径
        """
        logger.info(f"导出GeoJSON: {output_path}")
        gdf.to_file(output_path, driver='GeoJSON')
        logger.info(f"GeoJSON导出完成，共 {len(gdf)} 个图斑")
    
    def to_shapefile(self, gdf: gpd.GeoDataFrame, output_path: str):
        """
        导出为Shapefile
        
        Args:
            gdf: GeoDataFrame
            output_path: 输出文件路径
        """
        logger.info(f"导出Shapefile: {output_path}")
        gdf.to_file(output_path)
        logger.info(f"Shapefile导出完成，共 {len(gdf)} 个图斑")
    
    def calculate_statistics(self, gdf: gpd.GeoDataFrame) -> Dict:
        """
        计算图斑统计信息
        
        Args:
            gdf: GeoDataFrame
            
        Returns:
            统计字典
        """
        if len(gdf) == 0:
            return {"total_count": 0, "total_area": 0, "by_class": {}}
        
        stats = {
            "total_count": len(gdf),
            "total_area": float(gdf['area_m2'].sum()),
            "by_class": {}
        }
        
        # 按类别统计
        for class_id in gdf['class_id'].unique():
            class_gdf = gdf[gdf['class_id'] == class_id]
            stats["by_class"][int(class_id)] = {
                "count": len(class_gdf),
                "area": float(class_gdf['area_m2'].sum()),
                "avg_area": float(class_gdf['area_m2'].mean())
            }
        
        return stats


# 使用示例
if __name__ == "__main__":
    # 测试矢量化
    vectorizer = Vectorization(min_area=100.0, simplify_tolerance=1.0)
    
    # 创建测试掩膜
    # test_mask = np.zeros((512, 512), dtype=np.uint8)
    # test_mask[100:200, 100:200] = 1  # 林地
    # test_mask[300:400, 300:400] = 2  # 草地
    
    # 创建测试transform
    # from rasterio.transform import from_bounds
    # transform = from_bounds(116.0, 39.0, 116.1, 39.1, 512, 512)
    
    # 矢量化
    # gdf = vectorizer.mask_to_polygons(test_mask, transform, crs="EPSG:4326")
    # print(f"图斑数量: {len(gdf)}")
    # print(gdf.head())
