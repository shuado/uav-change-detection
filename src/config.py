"""
系统配置管理
"""
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class ModelConfig:
    """模型配置"""
    name: str = "segformer"  # segformer, unet, deeplabv3
    backbone: str = "mit-b2"  # MiT backbone
    checkpoint: Optional[str] = None
    confidence_threshold: float = 0.7
    device: str = "cuda"  # cuda, cpu
    batch_size: int = 4
    num_workers: int = 4


@dataclass
class ProcessingConfig:
    """处理配置"""
    tile_size: int = 512
    overlap: int = 64
    min_polygon_area: float = 100.0  # 平方米
    simplify_tolerance: float = 1.0  # 米
    target_crs: str = "EPSG:4326"  # WGS84


@dataclass
class APIConfig:
    """API服务配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    max_upload_size: int = 500 * 1024 * 1024  # 500MB
    task_timeout: int = 3600  # 1小时
    result_expire_days: int = 7


@dataclass
class StorageConfig:
    """存储配置"""
    data_dir: str = "./data"
    results_dir: str = "./results"
    models_dir: str = "./models"
    temp_dir: str = "./temp"


@dataclass
class Config:
    """主配置"""
    model: ModelConfig = ModelConfig()
    processing: ProcessingConfig = ProcessingConfig()
    api: APIConfig = APIConfig()
    storage: StorageConfig = StorageConfig()
    
    # 地物类别定义
    land_cover_classes: dict = None
    
    def __post_init__(self):
        if self.land_cover_classes is None:
            self.land_cover_classes = {
                0: {"name": "背景", "color": "#000000"},
                1: {"name": "林地", "color": "#228B22"},
                2: {"name": "草地", "color": "#90EE90"},
                3: {"name": "水域", "color": "#1E90FF"},
                4: {"name": "道路", "color": "#696969"},
                5: {"name": "建筑", "color": "#FF6347"},
            }
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> "Config":
        """从YAML文件加载配置"""
        import yaml
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    def to_yaml(self, yaml_path: str):
        """保存配置到YAML文件"""
        import yaml
        data = {
            'model': vars(self.model),
            'processing': vars(self.processing),
            'api': vars(self.api),
            'storage': vars(self.storage),
            'land_cover_classes': self.land_cover_classes,
        }
        os.makedirs(os.path.dirname(yaml_path), exist_ok=True)
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, indent=2)


# 全局配置实例
config = Config()
