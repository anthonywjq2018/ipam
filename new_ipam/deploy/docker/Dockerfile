# IPAM Dockerfile - 多阶段构建
FROM python:3.11-slim AS builder

WORKDIR /build

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖到虚拟环境
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ===== 运行时镜像 =====
FROM python:3.11-slim

WORKDIR /app

# 创建非 root 用户
RUN groupadd -r ipam && useradd -r -g ipam -d /app -s /bin/bash ipam

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# 复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 设置 PATH
ENV PATH="/opt/venv/bin:$PATH"

# 复制应用代码
COPY --chown=ipam:ipam . .

# 创建数据目录
RUN mkdir -p /app/data /app/data/backups && chown -R ipam:ipam /app/data

# 切换到非 root 用户
USER ipam

# 暴露端口
EXPOSE 5100

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5100/api/system/health || exit 1

# 启动命令
CMD ["python", "app.py"]