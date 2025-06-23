# ProxmoxMCP - Augment Optimized / Augment优化版

[English](#english) | [中文](#中文)

---

## English

This is an **Augment-optimized fork** of [ProxmoxMCP](https://github.com/canvrno/ProxmoxMCP) that resolves module import issues and provides seamless integration with Augment.

### 🚀 What's New in This Fork

- 🤖 **Full integration with Augment and Cline**
- 🛠️ **Built with the official MCP SDK**
- 🔒 **Secure token-based authentication with Proxmox**
- 🖥️ **Comprehensive node and VM management**
- 💻 **VM console command execution via Guest Agent**
- 🌐 **Advanced network configuration and Cloud-Init support**
- 🔄 **Automated VM deployment and configuration workflows**
- 📝 **Configurable logging system**
- ✅ **Type-safe implementation with Pydantic**
- 🎨 **Rich output formatting with customizable themes**
- 🌍 **Remote access support (no same-network requirement)**
- ✅ **Standalone Server**: All code in a single file (`standalone_mcp_server.py`)
- ✅ **No Module Cache Issues**: Eliminates Python RuntimeWarning and import problems
- ✅ **Augment Ready**: Perfect compatibility with Augment's MCP architecture

### 🔄 Original vs Augment-Optimized

| Feature | Original | Augment-Optimized |
|---------|----------|-------------------|
| Module Structure | Complex package structure | Single standalone file |
| Dependencies | Multiple packages | Minimal (aiohttp + mcp) |
| Startup Method | `python -m proxmox_mcp.server` | `./start_standalone.sh` |
| Module Cache Issues | ❌ Present | ✅ Resolved |
| Augment Compatibility | ⚠️ Problematic | ✅ Perfect |

### 🎯 Features

- **Proxmox VE Integration**: Full API access to your Proxmox cluster
- **MCP Protocol**: Standard Model Context Protocol implementation
- **Real-time Monitoring**: Cluster status, node information, VM management
- **Secure Authentication**: Token-based API authentication
- **Comprehensive Logging**: Detailed operation logs

### 📦 Quick Start

#### 1. Clone and Setup
```bash
git clone https://github.com/thefreelight/ProxmoxMCP.git
cd ProxmoxMCP

# Run automated installation
./install.sh

# Configure Proxmox credentials
edit proxmox-config/config.json

# Test the server
./start_standalone.sh
```

#### 2. Configure Augment
Add to your Augment configuration:
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

### 🛠️ Available Tools

- `get_cluster_status` - Get overall cluster status and resource summary
- `list_nodes` - List all nodes in the Proxmox cluster  
- `list_vms` - List all virtual machines (with optional node filter)

### 📚 Documentation

- [Detailed Setup Guide](AUGMENT_SETUP.md) - Complete installation and configuration
- [Original Project](https://github.com/canvrno/ProxmoxMCP) - Credit to the original authors

### 🙏 Credits

This fork is based on the excellent work by [canvrno](https://github.com/canvrno) in the original [ProxmoxMCP](https://github.com/canvrno/ProxmoxMCP) project. We've optimized it specifically for Augment compatibility while maintaining all the original functionality.

---

## 中文

这是 [ProxmoxMCP](https://github.com/canvrno/ProxmoxMCP) 的 **Augment优化分支**，解决了模块导入问题，并提供与Augment的无缝集成。

### 🚀 此分支的新特性

- ✅ **独立服务器**: 所有代码都在单个文件中 (`standalone_mcp_server.py`)
- ✅ **无模块缓存问题**: 消除Python RuntimeWarning和导入问题
- ✅ **Augment就绪**: 与Augment的MCP架构完美兼容
- ✅ **简化设置**: 最少依赖的简易安装
- ✅ **双语文档**: 支持英文和中文

### 🔄 原版 vs Augment优化版

| 特性 | 原版 | Augment优化版 |
|------|------|---------------|
| 模块结构 | 复杂的包结构 | 单个独立文件 |
| 依赖管理 | 多个包 | 最小化 (aiohttp + mcp) |
| 启动方式 | `python -m proxmox_mcp.server` | `./start_standalone.sh` |
| 模块缓存问题 | ❌ 存在 | ✅ 已解决 |
| Augment兼容性 | ⚠️ 有问题 | ✅ 完美 |

### 🎯 功能特性

- **Proxmox VE集成**: 完整的Proxmox集群API访问
- **MCP协议**: 标准模型上下文协议实现
- **实时监控**: 集群状态、节点信息、VM管理
- **安全认证**: 基于令牌的API认证
- **全面日志**: 详细的操作日志

### 📦 忩速开始

#### 1. 克隆和设置
```bash
git clone https://github.com/thefreelight/ProxmoxMCP.git
cd ProxmoxMCP

# 运行自动化安装
./install.sh

# 编辑Proxmox凭据
edit proxmox-config/config.json

# 测试服务器
./start_standalone.sh
```

#### 2. 配置Augment
添加到你的Augment配置中：
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

### 🛠️ 可用工具

- `get_cluster_status` - 获取集群状态和资源摘要
- `list_nodes` - 列出Proxmox集群中的所有节点
- `list_vms` - 列出所有虚拟机（可选节点过滤）

### 📚 文档

- [详细设置指南](AUGMENT_SETUP.md) - 完整的安装和配置说明
- [原始项目](https://github.com/canvrno/ProxmoxMCP) - 致敬原作者

### 🙏 致谢

此分支基于 [canvrno](https://github.com/canvrno) 在原始 [ProxmoxMCP](https://github.com/canvrno/ProxmoxMCP) 项目中的出色工作。我们专门为Augment兼容性进行了优化，同时保持了所有原始功能。
