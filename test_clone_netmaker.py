#!/usr/bin/env python3
"""
测试克隆Netmaker VM - 使用新添加的clone_vm功能
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

async def test_clone_netmaker():
    """测试克隆Netmaker VM"""
    os.environ["PROXMOX_MCP_CONFIG"] = "proxmox-config/config.json"
    
    server = StandaloneMCPServer()
    
    try:
        await server.initialize()
        print("✅ MCP服务器初始化成功")
        
        # 1. 使用新的clone_vm方法
        print("📋 使用clone_vm方法克隆VM 9000到VM 102...")
        clone_result = await server.clone_vm("pve", "9000", "102", "netmaker", True)
        print(f"✅ 克隆结果: {clone_result}")
        
        # 2. 等待克隆完成
        print("⏳ 等待克隆完成...")
        await asyncio.sleep(45)
        
        # 3. 配置VM资源
        print("🔧 配置VM资源...")
        
        # 配置内存
        memory_result = await server.update_vm_memory("pve", "102", "4096")
        print(f"✅ 内存配置: {memory_result}")
        
        # 配置CPU
        cpu_result = await server.update_vm_cpu("pve", "102", "2")
        print(f"✅ CPU配置: {cpu_result}")
        
        # 扩展存储
        storage_result = await server.update_vm_storage("pve", "102", "20G")
        print(f"✅ 存储配置: {storage_result}")
        
        # 4. 配置网络
        print("🌐 配置静态IP...")
        network_result = await server.update_vm_network("pve", "102", "192.168.0.102/24", "192.168.0.1")
        print(f"✅ 网络配置: {network_result}")
        
        # 5. 启动VM
        print("🚀 启动VM...")
        start_result = await server.start_vm("pve", "102")
        print(f"✅ VM启动: {start_result}")
        
        print("\n🎉 Netmaker VM创建完成!")
        print("📋 VM信息:")
        print("- VM ID: 102")
        print("- 名称: netmaker")
        print("- IP: 192.168.0.102")
        print("- 配置: 2核4GB, 20GB存储")
        
        print("\n📋 下一步:")
        print("1. 等待VM完全启动")
        print("2. SSH连接: ssh ubuntu@192.168.0.102")
        print("3. 安装Netmaker服务")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if server.proxmox_client:
            await server.proxmox_client.close()

if __name__ == "__main__":
    asyncio.run(test_clone_netmaker())
