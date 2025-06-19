# Augment-Optimized Proxmox MCP Server / Augment优化的Proxmox MCP服务器

[English](#english) | [中文](#中文)

---

## English

This is an Augment-optimized version of the Proxmox MCP server that resolves module import issues from the original version.

### 🎯 Features

- ✅ **No module cache issues** - All code in a single standalone file
- ✅ **Simplified dependencies** - Only requires aiohttp and mcp
- ✅ **Independent execution** - No complex module structure dependencies
- ✅ **Augment-optimized** - Avoids Python module import problems

### 📁 File Structure

- `standalone_mcp_server.py` - Standalone MCP server (all code in one file)
- `start_standalone.sh` - Launch script
- `.venv_new/` - Independent virtual environment
- `augment_config_example.json` - Augment configuration example

### 🚀 Installation

#### 1. Setup Virtual Environment
```bash
# Virtual environment already created in .venv_new/
# Dependencies installed: aiohttp, mcp
```

#### 2. Configure Proxmox Connection
Edit `proxmox-config/config.json`:
```json
{
  "proxmox": {
    "host": "your-proxmox-host.com",
    "port": 8006,
    "verify_ssl": false
  },
  "auth": {
    "user": "your-user@pam",
    "token_name": "your-token-name",
    "token_value": "your-token-value"
  },
  "logging": {
    "level": "INFO",
    "file": "proxmox_mcp.log"
  }
}
```

#### 3. Configure Augment
Add this configuration to your Augment config file:

```json
{
  "mcpServers": {
    "proxmox-mcp": {
      "command": "/path/to/ProxmoxMCP/start_standalone.sh",
      "args": [],
      "cwd": "/path/to/ProxmoxMCP",
      "env": {
        "PROXMOX_MCP_CONFIG": "/path/to/ProxmoxMCP/proxmox-config/config.json"
      }
    }
  }
}
```

### 🔧 Testing

#### Manual Server Test
```bash
# Test server startup
./start_standalone.sh

# Check logs
tail -f proxmox_mcp.log
```

#### Verify Augment Connection
1. Restart Augment
2. Check if MCP server appears in available servers list
3. Try using Proxmox-related features

### 🛠️ Available Tools

- `get_cluster_status` - Get cluster status
- `list_nodes` - List all nodes
- `list_vms` - List virtual machines (optional node filter)

### 🐛 Troubleshooting

#### Server Won't Start
1. Check virtual environment: `.venv_new/bin/python --version`
2. Check dependencies: `.venv_new/bin/pip list | grep -E "(aiohttp|mcp)"`
3. Verify config file path and format

#### Authentication Failed
1. Verify Proxmox host address and port
2. Check if API token is valid
3. Confirm user permissions

#### Connection Issues
1. Check network connectivity
2. Verify SSL settings (recommend `verify_ssl: false` for development)
3. Check log file: `tail -f proxmox_mcp.log`

---

## 中文

这是一个专门为Augment优化的Proxmox MCP服务器版本，解决了原版本的模块导入问题。

### 🎯 特性

- ✅ **无模块缓存问题** - 所有代码都在一个独立文件中
- ✅ **简化依赖** - 只需要 aiohttp 和 mcp
- ✅ **独立运行** - 不依赖复杂的模块结构
- ✅ **专为Augment优化** - 避免Python模块导入问题

## 📁 文件说明

- `standalone_mcp_server.py` - 独立的MCP服务器（所有代码在一个文件中）
- `start_standalone.sh` - 启动脚本
- `.venv_new/` - 独立的虚拟环境
- `augment_config_example.json` - Augment配置示例

## 🚀 安装步骤

### 1. 确保虚拟环境已设置
```bash
# 虚拟环境已经创建在 .venv_new/
# 依赖已安装：aiohttp, mcp
```

### 2. 配置Proxmox连接
编辑 `proxmox-config/config.json` 文件：
```json
{
  "proxmox": {
    "host": "your-proxmox-host.com",
    "port": 8006,
    "verify_ssl": false
  },
  "auth": {
    "user": "your-user@pam",
    "token_name": "your-token-name",
    "token_value": "your-token-value"
  },
  "logging": {
    "level": "INFO",
    "file": "proxmox_mcp.log"
  }
}
```

### 3. 配置Augment
将以下配置添加到你的Augment配置文件中：

```json
{
  "mcpServers": {
    "proxmox-mcp": {
      "command": "/Users/jordan/MCP/ProxmoxMCP/start_standalone.sh",
      "args": [],
      "cwd": "/Users/jordan/MCP/ProxmoxMCP",
      "env": {
        "PROXMOX_MCP_CONFIG": "/Users/jordan/MCP/ProxmoxMCP/proxmox-config/config.json"
      }
    }
  }
}
```

## 🔧 测试

### 手动测试服务器
```bash
# 测试服务器启动
./start_standalone.sh

# 检查日志
tail -f proxmox_mcp.log
```

### 验证Augment连接
1. 重启Augment
2. 检查MCP服务器是否出现在可用服务器列表中
3. 尝试使用Proxmox相关功能

## 🛠️ 可用工具

- `get_cluster_status` - 获取集群状态
- `list_nodes` - 列出所有节点
- `list_vms` - 列出虚拟机（可选择特定节点）

## 🐛 故障排除

### 服务器无法启动
1. 检查虚拟环境：`.venv_new/bin/python --version`
2. 检查依赖：`.venv_new/bin/pip list | grep -E "(aiohttp|mcp)"`
3. 检查配置文件路径和格式

### 认证失败
1. 验证Proxmox主机地址和端口
2. 检查API token是否有效
3. 确认用户权限

### 连接问题
1. 检查网络连接
2. 验证SSL设置（建议开发时设置 `verify_ssl: false`）
3. 查看日志文件：`tail -f proxmox_mcp.log`

## 📝 日志

服务器日志保存在 `proxmox_mcp.log` 文件中，包含：
- 服务器启动信息
- 连接状态
- 工具调用记录
- 错误信息

## 🔄 与原版本的区别

| 特性 | 原版本 | Augment优化版 |
|------|--------|---------------|
| 模块结构 | 复杂的包结构 | 单文件结构 |
| 依赖管理 | 多个依赖包 | 最小化依赖 |
| 启动方式 | `python -m proxmox_mcp.server` | `./start_standalone.sh` |
| 模块缓存问题 | ❌ 存在 | ✅ 已解决 |
| Augment兼容性 | ⚠️ 有问题 | ✅ 完全兼容 |
