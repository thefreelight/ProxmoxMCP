#!/usr/bin/env python3
"""
简单的Netmaker VM创建测试 - 和之前K8s VM创建一样的方法
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from standalone_mcp_server import StandaloneMCPServer
except ImportError as e:
    print(f"导入错误: {e}")
    sys.exit(1)

async def simple_netmaker_test():
    """简单测试 - 和之前成功的方法一样"""
    os.environ["PROXMOX_MCP_CONFIG"] = "proxmox-config/config.json"
    
    server = StandaloneMCPServer()
    
    try:
        await server.initialize()
        print("✅ MCP服务器初始化成功")
        
        # 使用和之前K8s VM完全相同的方法
        print("📋 克隆VM 9000到VM 102...")
        
        # 直接API调用 - 和之前成功的方法一样
        clone_result = await server.proxmox_client.post("/nodes/pve/qemu/9000/clone", {
            "newid": "102",
            "name": "netmaker",
            "full": "1"
        })
        print(f"✅ 克隆成功: {clone_result}")
        
        # 等待克隆完成
        print("⏳ 等待克隆完成...")
        await asyncio.sleep(45)
        
        # 配置VM - 使用现有的MCP工具
        print("🔧 配置VM...")
        
        memory_result = await server.update_vm_memory("pve", "102", "4096")
        print(f"✅ 内存: {memory_result}")
        
        cpu_result = await server.update_vm_cpu("pve", "102", "2")
        print(f"✅ CPU: {cpu_result}")
        
        storage_result = await server.update_vm_storage("pve", "102", "20G")
        print(f"✅ 存储: {storage_result}")
        
        # 配置网络
        print("🌐 配置网络...")
        network_result = await server.update_vm_network("pve", "102", "192.168.0.102/24", "192.168.0.1")
        print(f"✅ 网络: {network_result}")
        
        # 启动VM
        print("🚀 启动VM...")
        start_result = await server.start_vm("pve", "102")
        print(f"✅ 启动: {start_result}")
        
        print("\n🎉 Netmaker VM创建完成!")
        print("IP: 192.168.0.102")
        
    except Exception as e:
        print(f"❌ 失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if server.proxmox_client:
            await server.proxmox_client.close()

if __name__ == "__main__":
    asyncio.run(simple_netmaker_test())
