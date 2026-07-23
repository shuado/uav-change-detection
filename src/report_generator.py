"""
报告生成模块

功能：
- 生成变化检测报告
- 输出前后对比切片图片
- 输出GeoJSON数据
- 生成统计图表
"""
import geopandas as gpd
import rasterio
import numpy as np
from PIL import Image, ImageDraw
import json
from pathlib import Path
from typing import Dict, List, Tuple
from loguru import logger
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, class_names: List[str] = None, class_colors: List[str] = None):
        """
        初始化报告生成器
        
        Args:
            class_names: 类别名称列表
            class_colors: 类别颜色列表（十六进制）
        """
        self.class_names = class_names or ['背景', '林地', '草地', '水域', '道路', '建筑']
        self.class_colors = class_colors or ['#000000', '#228B22', '#90EE90', '#1E90FF', '#696969', '#FF6347']
        logger.info(f"报告生成器初始化，类别数: {len(self.class_names)}")
    
    def export_geojson(self, change_gdf: gpd.GeoDataFrame, output_path: str):
        """
        导出GeoJSON文件
        
        Args:
            change_gdf: 变化图斑GeoDataFrame
            output_path: 输出文件路径
        """
        logger.info(f"导出GeoJSON: {output_path}")
        
        # 选择需要的列
        export_columns = ['geometry', 'change_type', 'class_name', 'area_m2', 
                         'centroid_x', 'centroid_y', 'area_change_m2', 
                         'class_name_from', 'class_name_to']
        
        export_gdf = change_gdf[export_columns].copy()
        export_gdf.to_file(output_path, driver='GeoJSON')
        
        logger.info(f"GeoJSON导出完成，共 {len(export_gdf)} 个变化图斑")
    
    def create_comparison_image(self, image_t1: np.ndarray, image_t2: np.ndarray,
                               change_gdf: gpd.GeoDataFrame, output_path: str,
                               transform: rasterio.Affine = None):
        """
        创建前后对比切片图片
        
        Args:
            image_t1: 时期1影像 (H, W, C) 或 (C, H, W)
            image_t2: 时期2影像
            change_gdf: 变化图斑GeoDataFrame
            output_path: 输出图片路径
            transform: 仿射变换参数（用于绘制矢量）
        """
        logger.info(f"创建对比图片: {output_path}")
        
        # 确保是(H, W, C)格式
        if image_t1.shape[0] in [1, 3, 4]:
            image_t1 = np.transpose(image_t1, (1, 2, 0))
        if image_t2.shape[0] in [1, 3, 4]:
            image_t2 = np.transpose(image_t2, (1, 2, 0))
        
        # 如果是单波段，转换为3波段
        if image_t1.shape[2] == 1:
            image_t1 = np.repeat(image_t1, 3, axis=2)
        if image_t2.shape[2] == 1:
            image_t2 = np.repeat(image_t2, 3, axis=2)
        
        # 归一化到0-255
        if image_t1.max() > 1:
            image_t1 = (image_t1 / image_t1.max() * 255).astype(np.uint8)
        if image_t2.max() > 1:
            image_t2 = (image_t2 / image_t2.max() * 255).astype(np.uint8)
        
        # 创建对比图
        fig, axes = plt.subplots(1, 2, figsize=(20, 10))
        
        # T1影像
        axes[0].imshow(image_t1)
        axes[0].set_title('时期1 (T1)', fontsize=16, fontweight='bold')
        axes[0].axis('off')
        
        # T2影像
        axes[1].imshow(image_t2)
        axes[1].set_title('时期2 (T2)', fontsize=16, fontweight='bold')
        axes[1].axis('off')
        
        # 在T2上绘制变化图斑
        if len(change_gdf) > 0 and transform is not None:
            for idx, row in change_gdf.iterrows():
                geom = row.geometry
                change_type = row.change_type
                
                # 选择颜色
                if change_type == '新增':
                    color = 'green'
                    linewidth = 3
                elif change_type == '消失':
                    color = 'red'
                    linewidth = 3
                else:
                    color = 'yellow'
                    linewidth = 2
                
                # 转换坐标到像素坐标
                if geom.geom_type == 'Polygon':
                    coords = list(geom.exterior.coords)
                    pixel_coords = []
                    for x, y in coords:
                        px, py = ~transform * (x, y)
                        pixel_coords.append((px, py))
                    
                    if pixel_coords:
                        poly = plt.Polygon(pixel_coords, fill=False, 
                                         edgecolor=color, linewidth=linewidth)
                        axes[1].add_patch(poly)
        
        # 添加图例
        legend_elements = [
            mpatches.Patch(facecolor='none', edgecolor='green', linewidth=3, label='新增'),
            mpatches.Patch(facecolor='none', edgecolor='red', linewidth=3, label='消失'),
            mpatches.Patch(facecolor='none', edgecolor='yellow', linewidth=2, label='变化')
        ]
        axes[1].legend(handles=legend_elements, loc='upper right', fontsize=12)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"对比图片保存完成: {output_path}")
    
    def generate_statistics_charts(self, stats: Dict, output_path: str):
        """
        生成统计图表
        
        Args:
            stats: 统计信息字典
            output_path: 输出图片路径
        """
        logger.info(f"生成统计图表: {output_path}")
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # 1. 变化类型饼图
        change_types = ['新增', '消失', '变化']
        counts = [stats['new_count'], stats['disappeared_count'], stats['changed_count']]
        colors = ['#4CAF50', '#F44336', '#FFC107']
        
        axes[0, 0].pie(counts, labels=change_types, colors=colors, autopct='%1.1f%%', startangle=90)
        axes[0, 0].set_title('变化类型分布', fontsize=14, fontweight='bold')
        
        # 2. 变化面积柱状图
        areas = [stats['new_area'], stats['disappeared_area'], stats['changed_area']]
        axes[0, 1].bar(change_types, areas, color=colors)
        axes[0, 1].set_ylabel('面积 (m²)', fontsize=12)
        axes[0, 1].set_title('变化面积统计', fontsize=14, fontweight='bold')
        axes[0, 1].grid(axis='y', alpha=0.3)
        
        # 3. 统计汇总表
        axes[1, 0].axis('off')
        table_data = [
            ['变化类型', '数量', '面积 (m²)'],
            ['新增', str(stats['new_count']), f"{stats['new_area']:.2f}"],
            ['消失', str(stats['disappeared_count']), f"{stats['disappeared_area']:.2f}"],
            ['变化', str(stats['changed_count']), f"{stats['changed_area']:.2f}"],
            ['总计', str(stats['total_changes']), 
             f"{stats['new_area'] + stats['disappeared_area'] + stats['changed_area']:.2f}"]
        ]
        
        table = axes[1, 0].table(cellText=table_data, cellLoc='center', loc='center',
                                 colWidths=[0.3, 0.3, 0.4])
        table.auto_set_font_size(False)
        table.set_fontsize(12)
        table.scale(1, 2)
        axes[1, 0].set_title('变化统计汇总表', fontsize=14, fontweight='bold', pad=20)
        
        # 4. 时间戳
        axes[1, 1].axis('off')
        axes[1, 1].text(0.5, 0.5, f'生成时间:\n{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                       ha='center', va='center', fontsize=14)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"统计图表保存完成: {output_path}")
    
    def generate_text_report(self, stats: Dict, change_gdf: gpd.GeoDataFrame, output_path: str):
        """
        生成文本报告
        
        Args:
            stats: 统计信息
            change_gdf: 变化图斑GeoDataFrame
            output_path: 输出文件路径
        """
        logger.info(f"生成文本报告: {output_path}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("无人机正射影像变化检测报告\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("-" * 80 + "\n")
            f.write("一、总体统计\n")
            f.write("-" * 80 + "\n")
            f.write(f"总变化图斑数: {stats['total_changes']}\n")
            f.write(f"  - 新增: {stats['new_count']} 个\n")
            f.write(f"  - 消失: {stats['disappeared_count']} 个\n")
            f.write(f"  - 变化: {stats['changed_count']} 个\n\n")
            
            f.write(f"总变化面积: {stats['new_area'] + stats['disappeared_area'] + stats['changed_area']:.2f} m²\n")
            f.write(f"  - 新增面积: {stats['new_area']:.2f} m²\n")
            f.write(f"  - 消失面积: {stats['disappeared_area']:.2f} m²\n")
            f.write(f"  - 变化面积: {stats['changed_area']:.2f} m²\n\n")
            
            f.write("-" * 80 + "\n")
            f.write("二、变化图斑详情\n")
            f.write("-" * 80 + "\n\n")
            
            for idx, row in change_gdf.iterrows():
                f.write(f"图斑 {idx + 1}:\n")
                f.write(f"  变化类型: {row.change_type}\n")
                f.write(f"  类别: {row.class_name}\n")
                f.write(f"  面积: {row.area_m2:.2f} m²\n")
                f.write(f"  质心坐标: ({row.centroid_x:.6f}, {row.centroid_y:.6f})\n")
                
                if row.change_type == '变化':
                    f.write(f"  变化前类别: {row.class_name_from}\n")
                    f.write(f"  变化后类别: {row.class_name_to}\n")
                    f.write(f"  面积变化: {row.area_change_m2:+.2f} m²\n")
                
                f.write("\n")
        
        logger.info(f"文本报告保存完成: {output_path}")
    
    def generate_full_report(self, changes: Dict, change_gdf: gpd.GeoDataFrame,
                            image_t1: np.ndarray, image_t2: np.ndarray,
                            output_dir: str, transform: rasterio.Affine = None):
        """
        生成完整报告（包含所有文件）
        
        Args:
            changes: 变化检测结果
            change_gdf: 变化图斑GeoDataFrame
            image_t1: 时期1影像
            image_t2: 时期2影像
            output_dir: 输出目录
            transform: 仿射变换参数
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"生成完整报告到: {output_dir}")
        
        # 计算统计信息
        stats = {
            'total_changes': len(changes['new']) + len(changes['disappeared']) + len(changes['changed']),
            'new_count': len(changes['new']),
            'disappeared_count': len(changes['disappeared']),
            'changed_count': len(changes['changed']),
            'new_area': sum(item['area_m2'] for item in changes['new']),
            'disappeared_area': sum(item['area_m2'] for item in changes['disappeared']),
            'changed_area': sum(abs(item['area_change_m2']) for item in changes['changed'])
        }
        
        # 1. 导出GeoJSON
        self.export_geojson(change_gdf, str(output_path / 'changes.geojson'))
        
        # 2. 创建对比图片
        self.create_comparison_image(image_t1, image_t2, change_gdf,
                                    str(output_path / 'comparison.png'), transform)
        
        # 3. 生成统计图表
        self.generate_statistics_charts(stats, str(output_path / 'statistics.png'))
        
        # 4. 生成文本报告
        self.generate_text_report(stats, change_gdf, str(output_path / 'report.txt'))
        
        # 5. 保存统计JSON
        with open(output_path / 'statistics.json', 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        logger.info(f"完整报告生成完成: {output_dir}")
        
        return {
            'geojson': str(output_path / 'changes.geojson'),
            'comparison_image': str(output_path / 'comparison.png'),
            'statistics_chart': str(output_path / 'statistics.png'),
            'text_report': str(output_path / 'report.txt'),
            'statistics_json': str(output_path / 'statistics.json')
        }


# 使用示例
if __name__ == "__main__":
    # 测试报告生成
    generator = ReportGenerator()
    
    # 需要实际的测试数据
    # report_files = generator.generate_full_report(
    #     changes=changes,
    #     change_gdf=change_gdf,
    #     image_t1=image_t1,
    #     image_t2=image_t2,
    #     output_dir='./reports/test_report',
    #     transform=transform
    # )
