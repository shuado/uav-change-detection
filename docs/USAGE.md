# 使用指南

## 快速开始

### 1. 安装依赖

```bash
cd uav-change-detection
pip install -r requirements.txt
```

### 2. 命令行使用

#### 基本用法

```bash
python detect.py --t1 image_t1.tif --t2 image_t2.tif --output results/
```

#### 使用配置文件

```bash
python detect.py --t1 image_t1.tif --t2 image_t2.tif --output results/ --config configs/default.yaml
```

### 3. API服务器

#### 启动服务器

```bash
python detect.py --api --port 8000
```

访问 API 文档：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

#### API使用示例

```bash
# 1. 上传影像
curl -X POST "http://localhost:8000/api/v1/upload" \
  -F "file_t1=@image_t1.tif" \
  -F "file_t2=@image_t2.tif"

# 返回: {"task_id": "uuid", "status": "pending", ...}

# 2. 提交检测任务
curl -X POST "http://localhost:8000/api/v1/detect" \
  -H "Content-Type: application/json" \
  -d '{"task_id": "uuid"}'

# 3. 查询任务状态
curl "http://localhost:8000/api/v1/tasks/{task_id}"

# 4. 下载结果
# GeoJSON
curl "http://localhost:8000/api/v1/results/{task_id}/geojson" -o changes.geojson

# 对比图片
curl "http://localhost:8000/api/v1/results/{task_id}/images" -o comparison.png

# 统计信息
curl "http://localhost:8000/api/v1/results/{task_id}/statistics"
```

### 4. Python API

```python
from src.pipeline import run_pipeline

# 运行变化检测
result = run_pipeline(
    image_t1="path/to/image_t1.tif",
    image_t2="path/to/image_t2.tif",
    output_dir="results/",
    config_path="configs/default.yaml"  # 可选
)

print(f"处理完成！耗时: {result['total_time']:.2f}秒")
print(f"变化图斑数: {result['metadata']['changes']}")
```

## 输出文件说明

处理完成后，输出目录包含以下文件：

| 文件 | 说明 |
|------|------|
| `changes.geojson` | 变化图斑GeoJSON（WGS84坐标） |
| `comparison.png` | 前后对比切片图片 |
| `statistics.png` | 统计图表 |
| `report.txt` | 文本报告 |
| `statistics.json` | 统计数据JSON |
| `polygons_t1.geojson` | 时期1图斑 |
| `polygons_t2.geojson` | 时期2图斑 |
| `t1_wgs84.tif` | 时期1影像（WGS84） |
| `t2_wgs84.tif` | 时期2影像（WGS84） |

## 坐标系处理

系统会自动识别输入影像的坐标系，并统一转换为WGS84（EPSG:4326）：

支持的坐标系：
- WGS84 (EPSG:4326)
- UTM (各分带)
- CGCS2000 (EPSG:4490)
- 北京54
- 西安80
- 地方坐标系

## 配置说明

编辑 `configs/default.yaml` 调整参数：

```yaml
# 模型配置
model:
  name: segformer  # 模型名称
  device: cuda  # 使用GPU

# 处理配置
processing:
  min_polygon_area: 100.0  # 最小图斑面积（平方米）
  simplify_tolerance: 1.0  # 多边形简化容差（米）
  target_crs: "EPSG:4326"  # 目标坐标系

# 地物类别
land_cover_classes:
  1: {name: "林地", color: "#228B22"}
  2: {name: "草地", color: "#90EE90"}
  # ...
```

## 硬件要求

### 最低配置
- CPU: 4核
- 内存: 16GB
- GPU: 8GB显存（可选）
- 存储: 100GB

### 推荐配置
- CPU: 8核+
- 内存: 32GB+
- GPU: RTX 4090 / A100 (24GB+显存)
- 存储: 500GB SSD

## 常见问题

### Q: 如何添加自定义地物类别？

编辑 `configs/default.yaml` 中的 `land_cover_classes` 部分，添加新类别。

### Q: 处理速度太慢怎么办？

1. 使用GPU加速：设置 `model.device: cuda`
2. 减小切片大小：`processing.tile_size: 256`
3. 使用更轻量的模型：`model.name: unet`

### Q: 如何批量处理多对影像？

```bash
for t1 in data/t1_*.tif; do
    t2="data/t2_${t1#data/t1_}"
    output="results/${t1%.tif}"
    python detect.py --t1 "$t1" --t2 "$t2" --output "$output"
done
```

### Q: 坐标系转换失败怎么办？

检查输入影像是否包含有效的坐标系信息：

```bash
gdalinfo image.tif | grep "Coordinate System"
```

如果没有坐标系，需要先定义：

```bash
gdal_edit.py -a_srs EPSG:4326 image.tif
```
