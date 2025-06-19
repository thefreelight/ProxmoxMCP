# ProxmoxMCP - Augment Optimized / Augment 优化炋

[English](#english) | [中文](#中文\)

---

## English

This is an **Augment-optimized fork** of [ProxmoxMCP](https://github.com/canvrno/ProxmoxMCP) that resolves module import issues and provides seamless integration with Augment.

### 🚀 What's New in This Fork

- ✅ **Standalone Server**: All code in a single file (`standalone_mcp_server.py`)
- ✅ **No Module Cache Issues**: Eliminates Python RuntimeWarning and import problems
- ✅ **Augment Ready**: Perfect compatibility with Augment's MCP architecture
- ✅ **Simplified Setup**: Easy installation with minimal dependencies
- ✅ **Bilingual Documentation**: English and Chinese support

### 🔄 Original vs Augment-Optimized

| Feature | Original | Augment-Optimized |
|---------|----------|-------------------|
| Module Structure | Complex package structure | Single standalone file |
| Dependencies | Multiple packages | Minimal (aohttp + mcp) |
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

- [Detailed Setup Guide](AUGMENT_SETUP-md) - Complete installation and configuration
- [Original Project](https://github.com/canvrno/ProxmoxMCP) - Credit to the original authors

### 🙏 Credits

This fork is based on the excellent work by [canvrno](https://github.com/canvrno) in the original [ProxmoxMCP](https://github.com/canvrno/ProxmoxMCP) project. We've optimized it specifically for Augment compatibility while maintaining all the original functionality.

---

## 中文

俙是 [ProxmoxMCP](https://github.com/canvrno/ProxmoxMCP) 的 **Augment优化分支**，解决了模块导入问题，提供与Augment的无缟集合。

### 🚀 此分支的新特性

- ✅ **独立服务器：**所有码码疽在单个文件中 (`standalone_mcp_server.py`)
- ✅ **无模块缓存问题，**:消除了Python RuntimeWarning和导入问题
- ✅ **Augment就尪：**:与Augment的MCP枺构完美兼容
- ✅ **簡化合置：**最少依赖瞨易易的简易安装
- ✅ **双诬文档：**:支持觀文和中文支持

### 👄 原版 vs Augment优化版

| 特性 | 原版 | Augment优化炉 |
|------|------|-------------------|
| 模块结构 | 复杂的包结构 | 单个独立文件 |
| 依赖管理 | 多个�0� | 最小化 (aohttp + mcp) |
| 启动方式 | `python -m proxmox_mcp.server` | `./start_standalone.sh` |
| 模块缓存问题 | ❌ 存在 | ✅ 已解决了 |
| Augment兼容性丌 | ⚠️ 有问题 | ✅ 完美 |

### 🎯 功能珹性

- **Proxmox VE集合**：完整的Proxmox集合API访问
- **MCP协议〒〒:标准模型上下文协议实现
- **实时监控：**：集群状态、节点信息、VM管理
- **安全认证〒〒:基于代特皎API认证
- **全面日志：**：详细的操作日志

### 📦 快鄟开始

#### 1. 克隆和设置
```bash
git clone https://github.com/thefreelight/ProxmoxMCP.git
cd ProxmoxMCP

# 运行自动化安装
./install.sh

# 编辑Proxmox凭据信息
edit proxmox-config/config.json

# 测试服务器�./start_standalone.sh
```

#### 2. 配置Augment
本加到你的Augment配置中：
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

### 🛠ￏ 可用工具

- `get_cluster_status` - 获取集群状态和资源摘要
- `list_nodes` - 列出Proxmox集秤中的所有节点
- `list_vms` - 列出所有虚拟机器（可选节点轇过）

### 📚 文档〒

- [详细设置指南](AUGMENT_SETUP-md) - 完整的安装和配置说昏
- [原始项目](https://github.com/canvrno/ProxmoxMCP) - 致敬原作者

### 🙏 致谢

此分支基于 [canvrno](https://github.com/canvrno) 在原姉[ProxmoxMCP](https://github.com/canvrno/ProxmoxMCP)�h���中的出色工作。保真了所月原始功能，同时本加了Augment特算的改进。