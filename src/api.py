"""
REST API服务模块

功能：
- 提供RESTful API接口
- 影像上传
- 变化检测任务提交
- 结果查询和下载
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict
import uuid
import shutil
from pathlib import Path
from datetime import datetime
import json
from loguru import logger
import asyncio

# 创建FastAPI应用
app = FastAPI(
    title="无人机正射影像变化检测系统",
    description="提供影像上传、变化检测、结果查询等RESTful API接口",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# 数据模型
class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str
    created_at: str


class TaskStatus(BaseModel):
    task_id: str
    status: str  # pending, processing, completed, failed
    progress: float  # 0-100
    message: str
    created_at: str
    completed_at: Optional[str] = None
    result_files: Optional[Dict] = None
    error: Optional[str] = None


class DetectRequest(BaseModel):
    task_id: str
    options: Optional[Dict] = None


# 全局任务存储（生产环境应使用数据库）
tasks = {}

# 配置
UPLOAD_DIR = Path("./uploads")
RESULTS_DIR = Path("./results")
UPLOAD_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)


@app.get("/")
async def root():
    """API根路径"""
    return {
        "message": "无人机正射影像变化检测系统 API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.post("/api/v1/upload", response_model=TaskResponse)
async def upload_images(
    file_t1: UploadFile = File(..., description="时期1影像文件"),
    file_t2: UploadFile = File(..., description="时期2影像文件"),
    background_tasks: BackgroundTasks = None
):
    """
    上传两期影像文件
    
    - file_t1: 时期1的TIFF影像文件
    - file_t2: 时期2的TIFF影像文件
    """
    logger.info(f"接收文件上传: {file_t1.filename}, {file_t2.filename}")
    
    # 生成任务ID
    task_id = str(uuid.uuid4())
    
    # 创建任务目录
    task_dir = UPLOAD_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存文件
    t1_path = task_dir / file_t1.filename
    t2_path = task_dir / file_t2.filename
    
    try:
        with open(t1_path, "wb") as f:
            shutil.copyfileobj(file_t1.file, f)
        
        with open(t2_path, "wb") as f:
            shutil.copyfileobj(file_t2.file, f)
        
        logger.info(f"文件保存成功: {t1_path}, {t2_path}")
        
    except Exception as e:
        logger.error(f"文件保存失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")
    
    # 创建任务记录
    tasks[task_id] = {
        'task_id': task_id,
        'status': 'pending',
        'progress': 0,
        'message': '文件上传完成，等待处理',
        'created_at': datetime.now().isoformat(),
        'completed_at': None,
        'files': {
            't1': str(t1_path),
            't2': str(t2_path)
        },
        'result_files': None,
        'error': None
    }
    
    return TaskResponse(
        task_id=task_id,
        status='pending',
        message='文件上传成功',
        created_at=tasks[task_id]['created_at']
    )


@app.post("/api/v1/detect", response_model=TaskResponse)
async def submit_detection_task(
    request: DetectRequest,
    background_tasks: BackgroundTasks
):
    """
    提交变化检测任务
    
    - task_id: 上传任务返回的task_id
    - options: 可选的检测参数
    """
    task_id = request.task_id
    
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    
    task = tasks[task_id]
    
    if task['status'] != 'pending':
        raise HTTPException(status_code=400, detail=f"任务状态不正确: {task['status']}")
    
    # 更新任务状态
    task['status'] = 'processing'
    task['message'] = '开始处理变化检测'
    task['options'] = request.options or {}
    
    # 在后台执行检测任务
    background_tasks.add_task(run_detection_task, task_id)
    
    return TaskResponse(
        task_id=task_id,
        status='processing',
        message='检测任务已提交',
        created_at=task['created_at']
    )


async def run_detection_task(task_id: str):
    """
    后台执行变化检测任务
    
    Args:
        task_id: 任务ID
    """
    logger.info(f"开始执行检测任务: {task_id}")
    
    task = tasks[task_id]
    
    try:
        # 导入处理模块
        from .data_loader import DataLoader
        from .preprocessor import Preprocessor
        from .segmentation import SemanticSegmentation
        from .vectorization import Vectorization
        from .change_detection import ChangeDetection
        from .report_generator import ReportGenerator
        
        # 1. 加载数据
        task['progress'] = 10
        task['message'] = '加载影像数据'
        
        loader = DataLoader()
        image_t1 = loader.load_image(task['files']['t1'])
        image_t2 = loader.load_image(task['files']['t2'])
        
        # 2. 预处理
        task['progress'] = 20
        task['message'] = '预处理影像数据'
        
        preprocessor = Preprocessor()
        image_t1 = preprocessor.reproject_to_wgs84(image_t1)
        image_t2 = preprocessor.reproject_to_wgs84(image_t2)
        
        # 3. 语义分割
        task['progress'] = 40
        task['message'] = '执行语义分割 (T1)'
        
        segmentor = SemanticSegmentation()
        mask_t1 = segmentor.segment(image_t1.data)
        
        task['progress'] = 50
        task['message'] = '执行语义分割 (T2)'
        
        mask_t2 = segmentor.segment(image_t2.data)
        
        # 4. 矢量化
        task['progress'] = 60
        task['message'] = '图斑矢量化 (T1)'
        
        vectorizer = Vectorization()
        polygons_t1 = vectorizer.mask_to_polygons(mask_t1, image_t1.transform)
        
        task['progress'] = 70
        task['message'] = '图斑矢量化 (T2)'
        
        polygons_t2 = vectorizer.mask_to_polygons(mask_t2, image_t2.transform)
        
        # 5. 变化检测
        task['progress'] = 80
        task['message'] = '执行变化检测'
        
        detector = ChangeDetection()
        changes = detector.detect_changes(polygons_t1, polygons_t2)
        change_gdf = detector.changes_to_geodataframe(changes)
        
        # 6. 生成报告
        task['progress'] = 90
        task['message'] = '生成检测报告'
        
        output_dir = RESULTS_DIR / task_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        report_generator = ReportGenerator()
        result_files = report_generator.generate_full_report(
            changes=changes,
            change_gdf=change_gdf,
            image_t1=image_t1.data,
            image_t2=image_t2.data,
            output_dir=str(output_dir),
            transform=image_t1.transform
        )
        
        # 7. 完成任务
        task['progress'] = 100
        task['status'] = 'completed'
        task['message'] = '检测完成'
        task['completed_at'] = datetime.now().isoformat()
        task['result_files'] = result_files
        
        logger.info(f"检测任务完成: {task_id}")
        
    except Exception as e:
        logger.error(f"检测任务失败: {task_id}, 错误: {e}")
        task['status'] = 'failed'
        task['message'] = '检测失败'
        task['error'] = str(e)
        task['completed_at'] = datetime.now().isoformat()


@app.get("/api/v1/tasks/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """
    查询任务状态
    
    - task_id: 任务ID
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    
    task = tasks[task_id]
    
    return TaskStatus(
        task_id=task['task_id'],
        status=task['status'],
        progress=task['progress'],
        message=task['message'],
        created_at=task['created_at'],
        completed_at=task['completed_at'],
        result_files=task['result_files'],
        error=task['error']
    )


@app.get("/api/v1/results/{task_id}/geojson")
async def download_geojson(task_id: str):
    """
    下载GeoJSON结果文件
    
    - task_id: 任务ID
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    
    task = tasks[task_id]
    
    if task['status'] != 'completed':
        raise HTTPException(status_code=400, detail=f"任务未完成: {task['status']}")
    
    geojson_path = Path(task['result_files']['geojson'])
    
    if not geojson_path.exists():
        raise HTTPException(status_code=404, detail="GeoJSON文件不存在")
    
    return FileResponse(
        path=str(geojson_path),
        filename=f"changes_{task_id}.geojson",
        media_type="application/geo+json"
    )


@app.get("/api/v1/results/{task_id}/report")
async def download_report(task_id: str):
    """
    下载文本报告
    
    - task_id: 任务ID
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    
    task = tasks[task_id]
    
    if task['status'] != 'completed':
        raise HTTPException(status_code=400, detail=f"任务未完成: {task['status']}")
    
    report_path = Path(task['result_files']['text_report'])
    
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="报告文件不存在")
    
    return FileResponse(
        path=str(report_path),
        filename=f"report_{task_id}.txt",
        media_type="text/plain"
    )


@app.get("/api/v1/results/{task_id}/images")
async def download_images(task_id: str):
    """
    下载对比图片
    
    - task_id: 任务ID
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    
    task = tasks[task_id]
    
    if task['status'] != 'completed':
        raise HTTPException(status_code=400, detail=f"任务未完成: {task['status']}")
    
    comparison_path = Path(task['result_files']['comparison_image'])
    
    if not comparison_path.exists():
        raise HTTPException(status_code=404, detail="对比图片不存在")
    
    return FileResponse(
        path=str(comparison_path),
        filename=f"comparison_{task_id}.png",
        media_type="image/png"
    )


@app.get("/api/v1/results/{task_id}/statistics")
async def get_statistics(task_id: str):
    """
    获取统计信息
    
    - task_id: 任务ID
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    
    task = tasks[task_id]
    
    if task['status'] != 'completed':
        raise HTTPException(status_code=400, detail=f"任务未完成: {task['status']}")
    
    stats_path = Path(task['result_files']['statistics_json'])
    
    if not stats_path.exists():
        raise HTTPException(status_code=404, detail="统计文件不存在")
    
    with open(stats_path, 'r', encoding='utf-8') as f:
        stats = json.load(f)
    
    return JSONResponse(content=stats)


@app.delete("/api/v1/tasks/{task_id}")
async def delete_task(task_id: str):
    """
    删除任务及其文件
    
    - task_id: 任务ID
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    
    task = tasks[task_id]
    
    if task['status'] == 'processing':
        raise HTTPException(status_code=400, detail="不能删除正在处理的任务")
    
    # 删除文件
    try:
        upload_dir = UPLOAD_DIR / task_id
        if upload_dir.exists():
            shutil.rmtree(upload_dir)
        
        result_dir = RESULTS_DIR / task_id
        if result_dir.exists():
            shutil.rmtree(result_dir)
        
        # 删除任务记录
        del tasks[task_id]
        
        logger.info(f"任务已删除: {task_id}")
        
        return {"message": f"任务 {task_id} 已删除"}
        
    except Exception as e:
        logger.error(f"删除任务失败: {task_id}, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")


def start_api_server(host: str = "0.0.0.0", port: int = 8000):
    """
    启动API服务器
    
    Args:
        host: 监听地址
        port: 监听端口
    """
    import uvicorn
    
    logger.info(f"启动API服务器: {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    # 启动服务器
    start_api_server()
