#!/bin/bash

# 设置脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 如果没有设置 PROXMOX_MCP_CONFIG，使用默认值
if [ -z "$PROXMOX_MCP_CONFIG" ]; then
    export PROXMOX_MCP_CONFIG="$SCRIPT_DIR/proxmox-config/config.json"
fi

# 切换到脚本目录
cd "$SCRIPT_DIR"

# 启动独立MCP服务器
exec "$SCRIPT_DIR/.venv_new/bin/python" standalone_mcp_server.py
