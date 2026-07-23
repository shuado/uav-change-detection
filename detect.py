#!/usr/bin/env python3
"""
变化检测命令行工具

用法:
    # 基本用法
    python detect.py --t1 image_t1.tif --t2 image_t2.tif --output results/
    
    # 指定配置文件
    python detect.py --t1 image_t1.tif --t2 image_t2.tif --output results/ --config config.yaml
    
    # 启动API服务器
    python detect.py --api --port 8000
"""
import argparse
import sys
from pathlib import Path
from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>")
logger.add("detect.log", rotation="10 MB", retention="7 days")


def main():
    parser = argparse.ArgumentParser(
        description="无人机正射影像变化检测系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 运行变化检测
  python detect.py --t1 t1.tif --t2 t2.tif --output results/
  
  # 使用配置文件
  python detect.py --t1 t1.tif --t2 t2.tif --output results/ --config config.yaml
  
  # 启动API服务器
  python detect.py --api --port 8000
        """
    )
    
    # 变化检测参数
    parser.add_argument("--t1", help="时期1影像路径 (TIFF/GeoTIFF)")
    parser.add_argument("--t2", help="时期2影像路径 (TIFF/GeoTIFF)")
    parser.add_argument("--output", help="输出目录")
    parser.add_argument("--config", help="配置文件路径 (YAML)")
    
    # API服务器参数
    parser.add_argument("--api", action="store_true", help="启动REST API服务器")
    parser.add_argument("--host", default="0.0.0.0", help="API服务器监听地址 (默认: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="API服务器端口 (默认: 8000)")
    
    # 其他参数
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    # 启动API服务器
    if args.api:
        logger.info(f"启动API服务器: {args.host}:{args.port}")
        logger.info(f"API文档: http://{args.host}:{args.port}/docs")
        
        from src.api import start_api_server
        start_api_server(host=args.host, port=args.port)
        return
    
    # 运行变化检测
    if not args.t1 or not args.t2 or not args.output:
        parser.error("变化检测需要 --t1, --t2, --output 参数")
    
    # 检查文件是否存在
    t1_path = Path(args.t1)
    t2_path = Path(args.t2)
    
    if not t1_path.exists():
        logger.error(f"时期1影像不存在: {args.t1}")
        sys.exit(1)
    
    if not t2_path.exists():
        logger.error(f"时期2影像不存在: {args.t2}")
        sys.exit(1)
    
    # 运行Pipeline
    try:
        from src.pipeline import run_pipeline
        
        logger.info("=" * 80)
        logger.info("无人机正射影像变化检测")
        logger.info("=" * 80)
        logger.info(f"时期1影像: {args.t1}")
        logger.info(f"时期2影像: {args.t2}")
        logger.info(f"输出目录: {args.output}")
        
        if args.config:
            logger.info(f"配置文件: {args.config}")
        
        result = run_pipeline(
            image_t1=str(t1_path),
            image_t2=str(t2_path),
            output_dir=args.output,
            config_path=args.config
        )
        
        # 打印结果
        print("\n" + "=" * 80)
        print("处理完成！")
        print("=" * 80)
        print(f"总耗时: {result['total_time']:.2f} 秒")
        print(f"\n统计信息:")
        print(f"  总变化: {result['statistics']['total_changes']} 个")
        print(f"  新增: {result['statistics']['new_count']} 个 ({result['statistics']['new_area']:.2f} m²)")
        print(f"  消失: {result['statistics']['disappeared_count']} 个 ({result['statistics']['disappeared_area']:.2f} m²)")
        print(f"  变化: {result['statistics']['changed_count']} 个 ({result['statistics']['changed_area']:.2f} m²)")
        
        print(f"\n输出文件:")
        for key, path in result['files'].items():
            print(f"  {key}: {path}")
        
        print("=" * 80)
        
    except Exception as e:
        logger.error(f"处理失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
