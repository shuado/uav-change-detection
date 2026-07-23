"""
主处理流程

将整个变化检测流程整合成一个完整的Pipeline
"""
from pathlib import Path
from typing import Dict, Optional
from loguru import logger
import time

from .data_loader import DataLoader
from .preprocessor import Preprocessor
from .segmentation import SemanticSegmentation
from .vectorization import Vectorization
from .change_detection import ChangeDetection
from .report_generator import ReportGenerator
from .config import Config


class ChangeDetectionPipeline:
    """变化检测主流程"""
    
    def __init__(self, config: Optional[Config] = None):
        """
        初始化Pipeline
        
        Args:
            config: 配置对象，默认使用全局配置
        """
        self.config = config or Config()
        
        logger.info("=" * 80)
        logger.info("初始化变化检测Pipeline")
        logger.info("=" * 80)
        
        # 初始化各模块
        self.data_loader = DataLoader(target_crs=self.config.processing.target_crs)
        self.preprocessor = Preprocessor(target_crs=self.config.processing.target_crs)
        self.segmentation = SemanticSegmentation(
            model_name=self.config.model.name,
            checkpoint=self.config.model.checkpoint,
            device=self.config.model.device
        )
        self.vectorization = Vectorization(
            min_area=self.config.processing.min_polygon_area,
            simplify_tolerance=self.config.processing.simplify_tolerance
        )
        self.change_detector = ChangeDetection(iou_threshold=0.5)
        self.report_generator = ReportGenerator(
            class_names=[info['name'] for info in self.config.land_cover_classes.values()],
            class_colors=[info['color'] for info in self.config.land_cover_classes.values()]
        )
        
        logger.info("Pipeline初始化完成")
    
    def run(self, image_t1_path: str, image_t2_path: str, output_dir: str) -> Dict:
        """
        执行完整的处理流程
        
        Args:
            image_t1_path: 时期1影像路径
            image_t2_path: 时期2影像路径
            output_dir: 输出目录
            
        Returns:
            处理结果字典
        """
        start_time = time.time()
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("=" * 80)
        logger.info(f"开始处理: {image_t1_path} vs {image_t2_path}")
        logger.info(f"输出目录: {output_dir}")
        logger.info("=" * 80)
        
        try:
            # Step 1: 加载数据
            logger.info("\n[1/6] 加载影像数据...")
            image_t1 = self.data_loader.load_image(image_t1_path)
            image_t2 = self.data_loader.load_image(image_t2_path)
            
            # 验证数据
            report_t1 = self.data_loader.validate_image(image_t1)
            report_t2 = self.data_loader.validate_image(image_t2)
            
            if not report_t1['valid'] or not report_t2['valid']:
                raise ValueError(f"数据验证失败:\nT1: {report_t1}\nT2: {report_t2}")
            
            logger.info(f"原始坐标系 T1: {image_t1.original_crs}")
            logger.info(f"原始坐标系 T2: {image_t2.original_crs}")
            
            # Step 2: 预处理（坐标系统一化到WGS84）
            logger.info("\n[2/6] 预处理影像数据...")
            
            t1_reprojected_path = output_path / "t1_wgs84.tif"
            t2_reprojected_path = output_path / "t2_wgs84.tif"
            
            image_t1_wgs84 = self.preprocessor.reproject_to_wgs84(image_t1, str(t1_reprojected_path))
            image_t2_wgs84 = self.preprocessor.reproject_to_wgs84(image_t2, str(t2_reprojected_path))
            
            # 配准
            image_t1_aligned, image_t2_aligned = self.preprocessor.co_register(image_t1_wgs84, image_t2_wgs84)
            
            # 辐射校正
            image_t1_normalized = self.preprocessor.normalize_radiometry(image_t1_aligned)
            image_t2_normalized = self.preprocessor.normalize_radiometry(image_t2_aligned)
            
            # Step 3: 语义分割
            logger.info("\n[3/6] 执行语义分割...")
            
            logger.info("分割T1影像...")
            result_t1 = self.segmentation.predict(image_t1_normalized.data)
            
            logger.info("分割T2影像...")
            result_t2 = self.segmentation.predict(image_t2_normalized.data)
            
            logger.info(f"T1分割耗时: {result_t1.inference_time:.2f}s")
            logger.info(f"T2分割耗时: {result_t2.inference_time:.2f}s")
            
            # Step 4: 图斑矢量化
            logger.info("\n[4/6] 图斑矢量化...")
            
            gdf_t1 = self.vectorization.mask_to_polygons(
                result_t1.mask,
                image_t1_wgs84.metadata.transform,
                crs=self.config.processing.target_crs
            )
            gdf_t1 = self.vectorization.add_class_names(gdf_t1, result_t1.class_names)
            
            gdf_t2 = self.vectorization.mask_to_polygons(
                result_t2.mask,
                image_t2_wgs84.metadata.transform,
                crs=self.config.processing.target_crs
            )
            gdf_t2 = self.vectorization.add_class_names(gdf_t2, result_t2.class_names)
            
            # 导出中间结果
            self.vectorization.to_geojson(gdf_t1, str(output_path / "polygons_t1.geojson"))
            self.vectorization.to_geojson(gdf_t2, str(output_path / "polygons_t2.geojson"))
            
            logger.info(f"T1图斑数: {len(gdf_t1)}")
            logger.info(f"T2图斑数: {len(gdf_t2)}")
            
            # Step 5: 变化检测
            logger.info("\n[5/6] 执行变化检测...")
            
            changes = self.change_detector.detect_changes(gdf_t1, gdf_t2)
            change_gdf = self.change_detector.changes_to_geodataframe(changes)
            
            if len(change_gdf) > 0:
                change_gdf.crs = self.config.processing.target_crs
            
            stats = self.change_detector.calculate_statistics(changes)
            
            # Step 6: 生成报告
            logger.info("\n[6/6] 生成检测报告...")
            
            result_files = self.report_generator.generate_full_report(
                changes=changes,
                change_gdf=change_gdf,
                image_t1=image_t1_normalized.data,
                image_t2=image_t2_normalized.data,
                output_dir=str(output_path),
                transform=image_t1_wgs84.metadata.transform
            )
            
            # 计算总耗时
            total_time = time.time() - start_time
            
            # 汇总结果
            result = {
                'success': True,
                'total_time': total_time,
                'statistics': stats,
                'files': result_files,
                'metadata': {
                    'image_t1': {
                        'path': image_t1_path,
                        'original_crs': image_t1.original_crs,
                        'size': f"{image_t1.metadata.width}x{image_t1.metadata.height}"
                    },
                    'image_t2': {
                        'path': image_t2_path,
                        'original_crs': image_t2.original_crs,
                        'size': f"{image_t2.metadata.width}x{image_t2.metadata.height}"
                    },
                    'polygons_t1': len(gdf_t1),
                    'polygons_t2': len(gdf_t2),
                    'changes': len(change_gdf)
                }
            }
            
            logger.info("\n" + "=" * 80)
            logger.info("处理完成！")
            logger.info(f"总耗时: {total_time:.2f}秒")
            logger.info(f"变化图斑数: {len(change_gdf)}")
            logger.info(f"输出目录: {output_dir}")
            logger.info("=" * 80)
            
            return result
            
        except Exception as e:
            logger.error(f"处理失败: {e}")
            raise


def run_pipeline(image_t1: str, image_t2: str, output_dir: str, config_path: Optional[str] = None) -> Dict:
    """
    便捷函数：运行完整的变化检测流程
    
    Args:
        image_t1: 时期1影像路径
        image_t2: 时期2影像路径
        output_dir: 输出目录
        config_path: 可选的配置文件路径
        
    Returns:
        处理结果
    """
    # 加载配置
    if config_path:
        config = Config.from_yaml(config_path)
    else:
        config = Config()
    
    # 创建Pipeline并运行
    pipeline = ChangeDetectionPipeline(config)
    return pipeline.run(image_t1, image_t2, output_dir)


# 命令行入口
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="无人机正射影像变化检测")
    parser.add_argument("--t1", required=True, help="时期1影像路径")
    parser.add_argument("--t2", required=True, help="时期2影像路径")
    parser.add_argument("--output", required=True, help="输出目录")
    parser.add_argument("--config", help="配置文件路径")
    
    args = parser.parse_args()
    
    result = run_pipeline(args.t1, args.t2, args.output, args.config)
    
    print("\n处理结果:")
    print(f"  成功: {result['success']}")
    print(f"  耗时: {result['total_time']:.2f}秒")
    print(f"  变化数: {result['metadata']['changes']}")
    print(f"\n输出文件:")
    for key, path in result['files'].items():
        print(f"  {key}: {path}")
