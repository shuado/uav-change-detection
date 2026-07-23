# 使用官方GDAL镜像作为基础
FROM osgeo/gdal:ubuntu-small-3.8.0

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    python3-venv \
    build-essential \
    libproj-dev \
    proj-data \
    proj-bin \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 升级pip并安装Python依赖
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir numpy==1.26.4 && \
    pip3 install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 安装项目本身
RUN pip3 install -e .

# 暴露API端口
EXPOSE 8000

# 默认命令：启动API服务
CMD ["python3", "detect.py", "--api"]
