# ProxmoxMCP - Augment Optimized

This is an **Augment-optimized fork** of [ProxmoxMCP](https://github.com/canvrno/ProxmoxMCP) that resolves module import issues and provides seamless integration with Augment.

### 🚀 What's New in This Fork

- ✅ **Standalone Server**: All code in a single file (`standalone_mcp_server.py`)
- ✅ **No Module Cache Issues**: Eliminates Python RuntimeWarning and import problems
- ✅ **Augment Ready**: Perfect compatibility with Augment's MCP architecture
- ✅ **Simplified Setup**: Easy installation with minimal dependencies
- ✅ **Complete VM Management**: 20 comprehensive tools for full VM lifecycle management

### 🔄 Original vs Augment-Optimized

| Feature | Original | Augment-Optimized |
|---------|----------|-------------------|
| Module Structure | Complex package structure | Single standalone file |
| Dependencies | Multiple packages | Minimal (aiohttp + mcp) |
| Startup Method | `python -m proxmox_mcp.server` | `./start_standalone.sh` |
| Module Cache Issues | ❌ Present | ✅ Resolved |
| Augment Compatibility | ⚠️ Problematic | ✅ Perfect |

### 🎯 Features

- **Complete VM Management**: 20 comprehensive tools covering full VM lifecycle
- **Proxmox VE Integration**: Full API access to your Proxmox cluster
- **Guest Agent Support**: Execute commands and manage VMs internally
- **Network Configuration**: Static IP configuration and network management
- **VM Cloning**: Create VMs from templates with full/linked clone support
- **Console Access**: VNC and Serial Terminal access to VMs
- **MCP Protocol**: Standard Model Context Protocol implementation
- **Secure Authentication**: Token-based API authentication
- **Enterprise Ready**: Production-grade stability and error handling

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

### 🛠️ Available Tools (20 Complete VM Management Tools)

#### Basic VM Management
- `get_cluster_status` - Get overall cluster status and resource summary
- `list_nodes` - List all nodes in the Proxmox cluster
- `list_vms` - List all virtual machines (with optional node filter)
- `start_vm` - Start a virtual machine
- `stop_vm` - Stop a virtual machine
- `restart_vm` - Restart a virtual machine
- `get_vm_status` - Get detailed status of a specific virtual machine
- `list_storage` - List all storage pools in the cluster

#### VM Configuration Management
- `update_vm_memory` - Update VM memory allocation
- `update_vm_cpu` - Update VM CPU allocation
- `clone_vm` - Clone a VM from template or existing VM
- `update_vm_network` - Update VM network configuration (static IP)

#### Guest Agent Integration
- `get_vm_agent_info` - Get VM network information via qemu-guest-agent
- `execute_vm_command` - Execute command in VM via QEMU guest agent
- `install_guest_agent` - Install QEMU Guest Agent via Cloud-Init restart
- `create_guest_agent_template` - Create a new VM template with Guest Agent pre-installed
- `force_install_guest_agent` - Force install Guest Agent using new method
- `enable_guest_agent` - Enable Guest Agent support in VM configuration

#### Advanced Features
- `execute_node_command` - Execute command on Proxmox node (for network discovery)
- `get_vm_console_access` - Get VM console access via VNC or Serial Terminal

### 📚 Documentation

- [Detailed Setup Guide](AUGMENT_SETUP.md) - Complete installation and configuration
- [Original Project](https://github.com/canvrno/ProxmoxMCP) - Credit to the original authors

### 🙏 Credits

This fork is based on the excellent work by [canvrno](https://github.com/canvrno) in the original [ProxmoxMCP](https://github.com/canvrno/ProxmoxMCP) project. We've optimized it specifically for Augment compatibility while maintaining all the original functionality.

### 🙏 Acknowledgments

This fork is based on the excellent work by [canvrno](https://github.com/canvrno) in the original [ProxmoxMCP](https://github.com/canvrno/ProxmoxMCP) project. We've optimized it specifically for Augment compatibility while maintaining all original functionality.
