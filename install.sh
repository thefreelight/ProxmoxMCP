#!/bin/bash

# ProxmoxMCP Augment-Optimized Installation Script
# 安装脚本

set -e

echo "🚀 Installing ProxmoxMCP Augment-Optimized..."
echo "🚀 正在安装ProxmoxMCP Augment优化版..."

# Check Python version
echo "📋 Checking Python version..."
echo "📋 检查Python版本..."
python3 --version

# Create virtual environment
echo "🔧 Creating virtual environment..."
echo "🔧 创建虚拟环境..."
python3 -m venv .venv_new

# Install dependencies
echo "📦 Installing dependencies..."
echo "📦 安装依赖..."
.venv_new/bin/pip install --upgrade pip
.venv_new/bin/pip install aiohttp mcp

# Make scripts executable
echo "🔐 Setting permissions..."
echo "🔐 设置权限..."
chmod +x start_standalone.sh

# Create config from example if it doesn't exist
if [ ! -f "proxmox-config/config.json" ]; then
    echo "📝 Creating config file from example..."
    echo "📝 从示例创建配置文件..."
    cp proxmox-config/config.example.json proxmox-config/config.json
    echo "⚠️  Please edit proxmox-config/config.json with your Proxmox details"
    echo "⚠️  请编辑 proxmox-config/config.json 填入你的Proxmox详细信息"
fi

echo ""
echo "✅ Installation completed!"
echo "✅ 安装完成！"
echo ""
echo "📚 Next steps / 下一步:"
echo "1. Edit proxmox-config/config.json with your Proxmox credentials"
echo "   编辑 proxmox-config/config.json 填入你的Proxmox凭据"
echo ""
echo "2. Test the server:"
echo "   测试服务器:"
echo "   ./start_standalone.sh"
echo ""
echo "3. Configure Augment with the example in augment_config_example.json"
echo "   使用 augment_config_example.json 中的示例配置Augment"
echo ""
echo "📖 For detailed setup instructions, see AUGMENT_SETUP.md"
echo "📖 详细设置说明请参见 AUGMENT_SETUP.md"
