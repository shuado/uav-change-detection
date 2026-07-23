"""
预处理模块

功能：
- 坐标系统一化（转换到WGS84）
- 影像配准
- 辐射校正
- 影像裁剪
- 数据增强
"""
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.crs import CRS
import numpy as np
from typing import Tuple, Optional
from loguru import logger
from .data_loader import ImageData


class Preprocessor:
    """影像预处理器"""
    
    def __init__(self, target_crs: str = "EPSG:4326"):
        """
        初始化预处理器
        
        Args:
            target_crs: 目标坐标系（默认WGS84）
        """
        self.target_crs = CRS.from_string(target_crs)
        logger.info(f"预处理器初始化，目标坐标系: {target_crs}")
    
    def reproject_to_wgs84(self, image_data: ImageData, output_path: str) -> ImageData:
        """
        重投影到WGS84坐标系
        
        Args:
            image_data: 原始影像数据
            output_path: 输出文件路径
            
        Returns:
            重投影后的影像数据
        """
        original_crs = CRS.from_string(image_data.metadata.crs)
        
        # 如果已经是WGS84，直接返回
        if original_crs == self.target_crs:
            logger.info("影像已经是WGS84坐标系，无需重投影")
            return image_data
        
        logger.info(f"重投影: {image_data.metadata.crs} -> WGS84")
        
        with rasterio.open(image_data.path) as src:
            # 计算目标变换参数
            transform, width, height = calculate_default_transform(
                src.crs,
                self.target_crs,
                src.width,
                src.height,
                *src.bounds
            )
            
            # 创建输出文件
            kwargs = src.meta.copy()
            kwargs.update({
                'crs': self.target_crs,
                'transform': transform,
                'width': width,
                'height': height
            })
            
            with rasterio.open(output_path, 'w', **kwargs) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=self.target_crs,
                        resampling=Resampling.nearest
                    )
        
        # 重新加载重投影后的影像
        from .data_loader import DataLoader
        loader = DataLoader(target_crs=str(self.target_crs))
        reprojected_image = loader.load_image(output_path)
        
        logger.info(f"重投影完成，新尺寸: {width}x{height}")
        return reprojected_image
    
    def co_register(self, image_t1: ImageData, image_t2: ImageData) -> Tuple[ImageData, ImageData]:
        """
        双时相影像配准
        
        Args:
            image_t1: 时相1影像
            image_t2: 时相2影像
            
        Returns:
            配准后的两期影像
        """
        logger.info("执行双时相影像配准")
        
        # TODO: 实现基于特征点的自动配准
        # 目前简单返回原图（假设已经配准）
        logger.warning("配准功能待实现，当前直接返回原图")
        
        return image_t1, image_t2
    
    def normalize_radiometry(self, image_data: ImageData) -> ImageData:
        """
        辐射校正（直方图均衡化）
        
        Args:
            image_data: 影像数据
            
        Returns:
            校正后的影像
        """
        logger.info("执行辐射校正")
        
        normalized_data = image_data.data.copy()
        
        # 对每个波段进行直方图均衡化
        for band in range(normalized_data.shape[0]):
            band_data = normalized_data[band]
            
            # 忽略nodata值
            if image_data.metadata.nodata is not None:
                mask = band_data != image_data.metadata.nodata
            else:
                mask = np.ones_like(band_data, dtype=bool)
            
            # 计算直方图
            valid_data = band_data[mask]
            if len(valid_data) == 0:
                continue
            
            # 2%线性拉伸
            p2, p98 = np.percentile(valid_data, (2, 98))
            band_data = np.clip(band_data, p2, p98)
            
            # 归一化到0-255
            if p98 > p2:
                band_data = ((band_data - p2) / (p98 - p2) * 255).astype(np.uint8)
            
            normalized_data[band] = band_data
        
        logger.info("辐射校正完成")
        
        return ImageData(
            path=image_data.path,
            data=normalized_data,
            metadata=image_data.metadata,
            original_crs=image_data.original_crs
        )
    
    def create_tiles(self, image_data: ImageData, tile_size: int = 512, overlap: int = 64) -> list:
        """
        创建影像切片（用于大图处理）
        
        Args:
            image_data: 影像数据
            tile_size: 切片大小（像素）
            overlap: 重叠区域（像素）
            
        Returns:
            切片列表
        """
        logger.info(f"创建影像切片，大小: {tile_size}，重叠: {overlap}")
        
        height, width = image_data.data.shape[1], image_data.data.shape[2]
        tiles = []
        
        step = tile_size - overlap
        
        for y in range(0, height, step):
            for x in range(0, width, step):
                # 计算切片范围
                y_end = min(y + tile_size, height)
                x_end = min(x + tile_size, width)
                
                # 提取切片数据
                tile_data = image_data.data[:, y:y_end, x:x_end]
                
                # 计算切片的地理范围
                transform = image_data.metadata.transform
                tile_transform = rasterio.Affine(
                    transform.a, transform.b, transform.c + x * transform.a,
                    transform.d, transform.e, transform.f + y * transform.e
                )
                
                tiles.append({
                    'data': tile_data,
                    'transform': tile_transform,
                    'x': x,
                    'y': y,
                    'width': x_end - x,
                    'height': y_end - y
                })
        
        logger.info(f"创建 {len(tiles)} 个切片")
        return tiles


# 使用示例
if __name__ == "__main__":
    # 测试预处理功能
    preprocessor = Preprocessor()
    
    # 从data_loader加载测试数据
    # from data_loader import DataLoader
    # loader = DataLoader()
    # image = loader.load_image("test.tif")
    
    # 重投影到WGS84
    # reprojected = preprocessor.reproject_to_wgs84(image, "test_wgs84.tif")
    
    # 辐射校正
    # normalized = preprocessor.normalize_radiometry(reprojected)
