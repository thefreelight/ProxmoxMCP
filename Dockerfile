FROM python:3.11-slim

WORKDIR /app

# 安装 git 和构建依赖
RUN apt-get update && apt-get install -y git build-essential

COPY . .

# 安装 Python 依赖
RUN pip install --upgrade pip \
    && pip install -e ".[dev]"

CMD ["python", "-m", "proxmox_mcp.server"]
