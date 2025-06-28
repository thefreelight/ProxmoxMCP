# ProxmoxMCP VM Renaming Guide

## 🎯 **新功能概述**

我已经为ProxmoxMCP添加了专业的VM重命名功能，支持：

- ✅ **单个VM重命名**: 重命名单个VM为专业命名规范
- ✅ **批量VM重命名**: 一次性重命名多个VM
- ✅ **命名规范验证**: 自动验证专业命名格式
- ✅ **名称冲突检测**: 防止重复命名
- ✅ **交互式脚本**: 用户友好的重命名工具

## 🔧 **新增的MCP工具**

### 1. `rename_vm` - 单个VM重命名
```json
{
  "name": "rename_vm",
  "description": "Rename a virtual machine to professional naming convention",
  "parameters": {
    "node": "pve",
    "vmid": "101", 
    "new_name": "infra-identity-01"
  }
}
```

### 2. `batch_rename_vms` - 批量VM重命名
```json
{
  "name": "batch_rename_vms", 
  "description": "Batch rename multiple VMs to professional naming convention",
  "parameters": {
    "node": "pve",
    "rename_map": {
      "101": "infra-identity-01",
      "102": "infra-vpn-01",
      "103": "infra-bastion-01"
    }
  }
}
```

## 📋 **专业命名规范**

### **格式**: `[layer]-[function]-[number]`

| Layer | Prefix | 用途 | 示例 |
|-------|--------|------|------|
| **Infrastructure** | `infra-` | 基础设施服务 | `infra-identity-01` |
| **Kubernetes** | `k8s-` | K8s集群节点 | `k8s-master-01` |
| **Development** | `dev-` | 开发平台 | `dev-gitlab-01` |
| **Production** | `prod-` | 生产应用 | `prod-app-01` |

### **验证规则**
- ✅ 必须以有效前缀开头 (infra-, k8s-, dev-, prod-)
- ✅ 功能部分只能包含小写字母和连字符
- ✅ 必须以两位数字结尾 (01, 02, 03...)
- ✅ 示例: `infra-database-01`, `k8s-worker-02`

## 🚀 **使用方法**

### **方法1: 直接使用MCP工具**

通过Augment或其他MCP客户端调用：

```python
# 重命名单个VM
rename_vm(node="pve", vmid="101", new_name="infra-identity-01")

# 批量重命名
batch_rename_vms(node="pve", rename_map={
    "101": "infra-identity-01",
    "102": "infra-vpn-01", 
    "103": "infra-bastion-01"
})
```

### **方法2: 使用交互式脚本**

```bash
# 设置环境变量
export PROXMOX_MCP_CONFIG=/path/to/config.json

# 运行交互式重命名脚本
python3 scripts/mcp-rename-vms.py
```

脚本功能：
- 📋 加载预定义的重命名映射
- 🔍 预览将要进行的更改
- 🤔 交互式确认每个操作
- 🔄 支持批量或逐个重命名

### **方法3: 使用预定义映射**

重命名映射文件 `scripts/professional-rename-map.json` 包含：

```json
{
  "rename_mappings": {
    "101": "infra-identity-01",
    "102": "infra-vpn-01",
    "103": "infra-bastion-01",
    "106": "infra-database-01",
    "109": "infra-gateway-01",
    "110": "infra-monitor-01",
    "113": "k8s-master-01",
    "114": "k8s-worker-01",
    "115": "k8s-worker-02",
    "116": "k8s-worker-03",
    "104": "dev-gitlab-01",
    "105": "dev-remote-01",
    "111": "dev-sandbox-01",
    "112": "dev-registry-01",
    "107": "prod-app-01",
    "108": "prod-app-02"
  }
}
```

## 🛡️ **安全特性**

### **验证机制**
- ✅ **格式验证**: 确保新名称符合专业命名规范
- ✅ **存在性检查**: 验证VM是否存在
- ✅ **冲突检测**: 防止名称重复
- ✅ **权限验证**: 通过Proxmox API权限控制

### **错误处理**
- ❌ 无效的命名格式
- ❌ VM不存在
- ❌ 名称已被使用
- ❌ 权限不足
- ❌ 网络连接问题

## 📊 **批量重命名示例输出**

```
🔄 Starting batch VM renaming...
📋 Processing 16 VMs on node 'pve'
==================================================
✅ VM 101: 'freeipa-identity' → 'infra-identity-01'
✅ VM 102: 'netbird-vpn' → 'infra-vpn-01'
✅ VM 103: 'jumpserver-ops' → 'infra-bastion-01'
✅ VM 106: 'database-cluster' → 'infra-database-01'
✅ VM 109: 'nginx-gateway' → 'infra-gateway-01'
✅ VM 110: 'monitoring-backup' → 'infra-monitor-01'
✅ VM 113: 'k8s-master' → 'k8s-master-01'
✅ VM 114: 'k8s-worker-1' → 'k8s-worker-01'
✅ VM 115: 'k8s-worker-2' → 'k8s-worker-02'
✅ VM 116: 'k8s-worker-3' → 'k8s-worker-03'
✅ VM 104: 'gitlab-platform' → 'dev-gitlab-01'
✅ VM 105: 'rustdesk-server' → 'dev-remote-01'
✅ VM 111: 'dev-environment' → 'dev-sandbox-01'
✅ VM 112: 'container-registry' → 'dev-registry-01'
✅ VM 107: 'app-server-1' → 'prod-app-01'
✅ VM 108: 'app-server-2' → 'prod-app-02'
==================================================
🎉 Batch rename completed!
✅ Successful: 16
❌ Failed: 0
📊 Total: 16
```

## 🔧 **技术实现**

### **新增的MCP方法**
1. `rename_vm()` - 单个VM重命名
2. `batch_rename_vms()` - 批量VM重命名
3. `_validate_professional_name()` - 命名格式验证
4. `_is_vm_name_taken()` - 名称冲突检测

### **API调用**
使用Proxmox API的 `POST /nodes/{node}/qemu/{vmid}/config` 端点，传递 `{"name": "new_name"}` 参数。

### **集成位置**
- 添加到 `standalone_mcp_server.py`
- 注册为MCP工具
- 包含完整的错误处理和验证

## 🎯 **下一步使用**

1. **立即可用**: 新的MCP工具已经集成到ProxmoxMCP中
2. **测试重命名**: 先用单个VM测试功能
3. **批量应用**: 确认无误后进行批量重命名
4. **验证结果**: 检查Proxmox界面确认重命名成功

你现在可以通过Augment直接调用这些新的MCP工具来重命名VM了！🚀
