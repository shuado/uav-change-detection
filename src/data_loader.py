"""
数据加载模块

功能：
- 加载TIFF/GeoTIFF影像
- 自动识别坐标系
- 提取元数据
- 验证数据完整性
"""
import rasterio
from rasterio.crs import CRS
from dataclasses import dataclass
from typing import Tuple, Dict, Optional
import numpy as np
from loguru import logger


@dataclass
class ImageMetadata:
    """影像元数据"""
    crs: str  # 坐标系（原始）
    crs_epsg: Optional[int]  # EPSG代码
    transform: rasterio.Affine  # 仿射变换
    bounds: Tuple[float, float, float, float]  # (left, bottom, right, top)
    width: int
    height: int
    bands: int
    dtype: str
    nodata: Optional[float]
    resolution: Tuple[float, float]  # (x_res, y_res) 米/像素


@dataclass
class ImageData:
    """影像数据"""
    path: str
    data: np.ndarray  # (bands, height, width)
    metadata: ImageMetadata
    original_crs: str  # 原始坐标系


class DataLoader:
    """数据加载器"""
    
    def __init__(self, target_crs: str = "EPSG:4326"):
        """
        初始化数据加载器
        
        Args:
            target_crs: 目标坐标系（默认WGS84）
        """
        self.target_crs = CRS.from_string(target_crs)
        logger.info(f"数据加载器初始化，目标坐标系: {target_crs}")
    
    def load_image(self, image_path: str) -> ImageData:
        """
        加载单张影像
        
        Args:
            image_path: 影像文件路径
            
        Returns:
            ImageData: 影像数据对象
        """
        logger.info(f"加载影像: {image_path}")
        
        with rasterio.open(image_path) as src:
            # 读取影像数据
            data = src.read()
            
            # 提取元数据
            metadata = ImageMetadata(
                crs=str(src.crs) if src.crs else "Unknown",
                crs_epsg=src.crs.to_epsg() if src.crs and src.crs.to_epsg() else None,
                transform=src.transform,
                bounds=src.bounds,
                width=src.width,
                height=src.height,
                bands=src.count,
                dtype=str(src.dtypes[0]),
                nodata=src.nodata,
                resolution=(src.res[0], src.res[1])
            )
            
            # 记录坐标系信息
            logger.info(f"原始坐标系: {metadata.crs}")
            logger.info(f"EPSG代码: {metadata.crs_epsg}")
            logger.info(f"影像尺寸: {metadata.width}x{metadata.height}")
            logger.info(f"波段数: {metadata.bands}")
            logger.info(f"分辨率: {metadata.resolution[0]:.2f}m x {metadata.resolution[1]:.2f}m")
            
            return ImageData(
                path=image_path,
                data=data,
                metadata=metadata,
                original_crs=metadata.crs
            )
    
    def validate_image(self, image_data: ImageData) -> Dict[str, any]:
        """
        验证影像数据
        
        Args:
            image_data: 影像数据对象
            
        Returns:
            验证报告
        """
        report = {
            "valid": True,
            "issues": [],
            "warnings": []
        }
        
        # 检查坐标系
        if image_data.metadata.crs == "Unknown":
            report["valid"] = False
            report["issues"].append("未定义坐标系")
        
        # 检查波段数
        if image_data.metadata.bands not in [1, 3, 4]:
            report["warnings"].append(f"非标准波段数: {image_data.metadata.bands}")
        
        # 检查数据类型
        if image_data.metadata.dtype not in ["uint8", "uint16", "float32"]:
            report["warnings"].append(f"非标准数据类型: {image_data.metadata.dtype}")
        
        # 检查nodata
        if image_data.metadata.nodata is None:
            report["warnings"].append("未定义nodata值")
        
        if report["valid"]:
            logger.info("影像验证通过")
        else:
            logger.warning(f"影像验证失败: {report['issues']}")
        
        return report
    
    def detect_crs(self, image_path: str) -> Tuple[str, Optional[int]]:
        """
        检测影像坐标系
        
        Args:
            image_path: 影像文件路径
            
        Returns:
            (CRS字符串, EPSG代码)
        """
        with rasterio.open(image_path) as src:
            crs_str = str(src.crs) if src.crs else "Unknown"
            epsg = src.crs.to_epsg() if src.crs and src.crs.to_epsg() else None
            
            logger.info(f"检测到坐标系: {crs_str} (EPSG:{epsg})")
            return crs_str, epsg


# 使用示例
if __name__ == "__main__":
    # 测试数据加载
    loader = DataLoader()
    
    # 加载测试影像（需要实际的测试数据）
    # image = loader.load_image("test.tif")
    # report = loader.validate_image(image)
    # print(report)
