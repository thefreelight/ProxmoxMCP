#!/usr/bin/env python3
"""
独立的Proxmox MCP服务器 - 专为Augment优化
避免复杂的模块导入，所有代码都在一个文件中
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

# MCP imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        TextContent,
        Tool,
    )
except ImportError as e:
    print(f"Error importing MCP modules: {e}")
    print("Please install the MCP package: pip install mcp")
    sys.exit(1)

# Proxmox API imports
try:
    import aiohttp
    import ssl
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please install: pip install aiohttp")
    sys.exit(1)


@dataclass
class ProxmoxConfig:
    """Proxmox连接配置"""
    host: str
    port: int = 8006
    verify_ssl: bool = True
    service: str = "PVE"


@dataclass
class AuthConfig:
    """认证配置"""
    user: str
    token_name: str
    token_value: str


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None


@dataclass
class Config:
    """完整配置"""
    proxmox: ProxmoxConfig
    auth: AuthConfig
    logging: LoggingConfig


class SimpleProxmoxClient:
    """简化的Proxmox API客户端"""
    
    def __init__(self, config: Config):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = f"https://{config.proxmox.host}:{config.proxmox.port}/api2/json"
        # 修复认证头格式 - 确保格式正确
        self.auth_header = f"PVEAPIToken={config.auth.user}!{config.auth.token_name}={config.auth.token_value}"
        self.logger = logging.getLogger("proxmox-mcp.client")
        
    async def connect(self):
        """建立连接"""
        ssl_context = ssl.create_default_context()
        if not self.config.proxmox.verify_ssl:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        connector = aiohttp.TCPConnector(ssl=ssl_context)
        self.session = aiohttp.ClientSession(
            connector=connector,
            headers={"Authorization": self.auth_header}
        )

        # 不在初始化时测试连接，等到实际调用时再验证
        # 这样服务器可以启动，即使认证配置有问题
    
    async def close(self):
        """关闭连接"""
        if self.session:
            await self.session.close()
    
    async def get(self, path: str) -> Dict[str, Any]:
        """GET请求"""
        if not self.session:
            raise Exception("Client not connected")

        url = f"{self.base_url}{path}"
        self.logger.debug(f"Making GET request to: {url}")

        async with self.session.get(url) as resp:
            if resp.status == 401:
                response_text = await resp.text()
                self.logger.error(f"401 Unauthorized response: {response_text}")
                raise Exception(f"401 Unauthorized: {response_text}")
            elif resp.status != 200:
                response_text = await resp.text()
                self.logger.error(f"HTTP {resp.status} response: {response_text}")
                raise Exception(f"HTTP {resp.status}: {response_text}")
            data = await resp.json()
            return data.get("data", {})
    
    async def post(self, path: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """POST请求"""
        if not self.session:
            raise Exception("Client not connected")

        url = f"{self.base_url}{path}"
        self.logger.debug(f"Making POST request to: {url}")

        # Proxmox API需要form data格式
        form_data = aiohttp.FormData()
        if data:
            for key, value in data.items():
                if key == "args" and isinstance(value, list):
                    # 对于args数组，需要特殊处理
                    for arg in value:
                        form_data.add_field("args", str(arg))
                else:
                    form_data.add_field(key, str(value))

        async with self.session.post(url, data=form_data) as resp:
            if resp.status == 401:
                response_text = await resp.text()
                self.logger.error(f"401 Unauthorized response: {response_text}")
                raise Exception(f"401 Unauthorized: {response_text}")
            elif resp.status not in [200, 201]:
                response_text = await resp.text()
                self.logger.error(f"HTTP {resp.status} response: {response_text}")
                raise Exception(f"HTTP {resp.status}: {response_text}")

            try:
                response_data = await resp.json()
                return response_data.get("data", response_data)
            except:
                # 如果不是JSON响应，返回文本
                response_text = await resp.text()
                return {"result": response_text}

    async def put(self, path: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """PUT请求"""
        if not self.session:
            raise Exception("Client not connected")

        url = f"{self.base_url}{path}"
        self.logger.debug(f"Making PUT request to: {url}")

        # Proxmox API需要form data格式
        form_data = aiohttp.FormData()
        if data:
            for key, value in data.items():
                if key == "command" and isinstance(value, list):
                    # 对于command数组，需要特殊处理
                    for cmd in value:
                        form_data.add_field("command", str(cmd))
                else:
                    form_data.add_field(key, str(value))

        async with self.session.put(url, data=form_data) as resp:
            if resp.status == 401:
                response_text = await resp.text()
                self.logger.error(f"401 Unauthorized response: {response_text}")
                raise Exception(f"401 Unauthorized: {response_text}")
            elif resp.status not in [200, 201]:
                response_text = await resp.text()
                self.logger.error(f"HTTP {resp.status} response: {response_text}")
                raise Exception(f"HTTP {resp.status}: {response_text}")

            try:
                response_data = await resp.json()
                return response_data.get("data", response_data)
            except:
                # 如果不是JSON响应，返回文本
                response_text = await resp.text()
                return {"result": response_text}


class StandaloneMCPServer:
    """独立的MCP服务器"""
    
    def __init__(self):
        self.server = Server("proxmox-mcp")
        self.proxmox_client: Optional[SimpleProxmoxClient] = None
        self.logger = logging.getLogger("proxmox-mcp")
        
    def load_config(self) -> Config:
        """加载配置"""
        config_path = os.environ.get("PROXMOX_MCP_CONFIG")
        if not config_path:
            raise ValueError("PROXMOX_MCP_CONFIG environment variable must be set")
        
        try:
            with open(config_path) as f:
                config_data = json.load(f)
            
            return Config(
                proxmox=ProxmoxConfig(**config_data["proxmox"]),
                auth=AuthConfig(**config_data["auth"]),
                logging=LoggingConfig(**config_data.get("logging", {}))
            )
        except Exception as e:
            raise ValueError(f"Failed to load config: {e}")
    
    def setup_logging(self, config: LoggingConfig):
        """设置日志"""
        logging.basicConfig(
            level=logging.DEBUG,  # 强制使用DEBUG级别
            format=config.format,
            filename=config.file
        )
    
    async def initialize(self):
        """初始化服务器"""
        # 加载配置
        config = self.load_config()
        self.setup_logging(config.logging)

        self.logger.info("Starting Standalone Proxmox MCP Server...")
        self.logger.info(f"Proxmox host: {config.proxmox.host}:{config.proxmox.port}")

        # 初始化Proxmox客户端
        self.proxmox_client = SimpleProxmoxClient(config)
        await self.proxmox_client.connect()

        # 注册工具
        self.register_tools()

        self.logger.info("Standalone Proxmox MCP Server initialized successfully")
        self.logger.info("Server is ready and waiting for connections...")
    
    def register_tools(self):
        """注册工具"""

        # 定义工具处理函数
        async def handle_list_tools() -> List[Tool]:
            tools = [
                Tool(
                    name="get_cluster_status",
                    description="Get overall cluster status and resource summary",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="list_nodes",
                    description="List all nodes in the Proxmox cluster",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="list_vms",
                    description="List all virtual machines in the cluster",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {
                                "type": "string",
                                "description": "Optional: Filter by specific node"
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="start_vm",
                    description="Start a virtual machine",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {
                                "type": "string",
                                "description": "Node name where the VM is located"
                            },
                            "vmid": {
                                "type": "string",
                                "description": "VM ID to start"
                            }
                        },
                        "required": ["node", "vmid"]
                    }
                ),
                Tool(
                    name="stop_vm",
                    description="Stop a virtual machine",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {
                                "type": "string",
                                "description": "Node name where the VM is located"
                            },
                            "vmid": {
                                "type": "string",
                                "description": "VM ID to stop"
                            }
                        },
                        "required": ["node", "vmid"]
                    }
                ),
                Tool(
                    name="restart_vm",
                    description="Restart a virtual machine",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {
                                "type": "string",
                                "description": "Node name where the VM is located"
                            },
                            "vmid": {
                                "type": "string",
                                "description": "VM ID to restart"
                            }
                        },
                        "required": ["node", "vmid"]
                    }
                ),
                Tool(
                    name="get_vm_status",
                    description="Get detailed status of a specific virtual machine",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {
                                "type": "string",
                                "description": "Node name where the VM is located"
                            },
                            "vmid": {
                                "type": "string",
                                "description": "VM ID to query"
                            }
                        },
                        "required": ["node", "vmid"]
                    }
                ),
                Tool(
                    name="list_storage",
                    description="List all storage pools in the cluster",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="update_vm_memory",
                    description="Update VM memory allocation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {
                                "type": "string",
                                "description": "Node name where the VM is located"
                            },
                            "vmid": {
                                "type": "string",
                                "description": "VM ID to update"
                            },
                            "memory": {
                                "type": "string",
                                "description": "Memory size in MB (e.g., '6144' for 6GB)"
                            }
                        },
                        "required": ["node", "vmid", "memory"]
                    }
                ),
                Tool(
                    name="update_vm_cpu",
                    description="Update VM CPU allocation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {
                                "type": "string",
                                "description": "Node name where the VM is located"
                            },
                            "vmid": {
                                "type": "string",
                                "description": "VM ID to update"
                            },
                            "cores": {
                                "type": "string",
                                "description": "Number of CPU cores (e.g., '4', '6', '8')"
                            }
                        },
                        "required": ["node", "vmid", "cores"]
                    }
                ),
                Tool(
                    name="update_vm_storage",
                    description="Update VM storage disk size (resize disk)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {
                                "type": "string",
                                "description": "Node name where the VM is located"
                            },
                            "vmid": {
                                "type": "string",
                                "description": "VM ID to update"
                            },
                            "storage_size": {
                                "type": "string",
                                "description": "New disk size (e.g., '20G', '50G', '100G')"
                            }
                        },
                        "required": ["node", "vmid", "storage_size"]
                    }
                ),
                Tool(
                    name="clone_vm",
                    description="Clone a VM from template or existing VM",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {
                                "type": "string",
                                "description": "Node name where to create the VM"
                            },
                            "source_vmid": {
                                "type": "string",
                                "description": "Source VM ID to clone from (template)"
                            },
                            "new_vmid": {
                                "type": "string",
                                "description": "New VM ID for the cloned VM"
                            },
                            "name": {
                                "type": "string",
                                "description": "Name for the new VM"
                            },
                            "full_clone": {
                                "type": "boolean",
                                "description": "Whether to create a full clone (default: true)",
                                "default": True
                            }
                        },
                        "required": ["node", "source_vmid", "new_vmid", "name"]
                    }
                ),
                Tool(
                    name="execute_vm_command",
                    description="Execute commands in a VM via QEMU guest agent",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {
                                "type": "string",
                                "description": "Host node name (e.g. 'pve')"
                            },
                            "vmid": {
                                "type": "string",
                                "description": "VM ID number (e.g. '102')"
                            },
                            "command": {
                                "type": "string",
                                "description": "Shell command to run (e.g. 'df -h')"
                            }
                        },
                        "required": ["node", "vmid", "command"]
                    }
                ),

            ]
            self.logger.info(f"Registered {len(tools)} tools: {[tool.name for tool in tools]}")
            return tools

        async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
            try:
                self.logger.debug(f"Tool called: {name} with args: {arguments}")

                if name == "get_cluster_status":
                    result = await self.get_cluster_status()
                elif name == "list_nodes":
                    result = await self.list_nodes()
                elif name == "list_vms":
                    result = await self.list_vms(arguments.get("node"))
                elif name == "start_vm":
                    result = await self.start_vm(arguments.get("node"), arguments.get("vmid"))
                elif name == "stop_vm":
                    result = await self.stop_vm(arguments.get("node"), arguments.get("vmid"))
                elif name == "restart_vm":
                    result = await self.restart_vm(arguments.get("node"), arguments.get("vmid"))
                elif name == "get_vm_status":
                    result = await self.get_vm_status(arguments.get("node"), arguments.get("vmid"))
                elif name == "list_storage":
                    result = await self.list_storage()
                elif name == "update_vm_memory":
                    result = await self.update_vm_memory(arguments.get("node"), arguments.get("vmid"), arguments.get("memory"))
                elif name == "update_vm_cpu":
                    result = await self.update_vm_cpu(arguments.get("node"), arguments.get("vmid"), arguments.get("cores"))
                elif name == "update_vm_storage":
                    result = await self.update_vm_storage(arguments.get("node"), arguments.get("vmid"), arguments.get("storage_size"))
                elif name == "clone_vm":
                    result = await self.clone_vm(
                        arguments.get("node"),
                        arguments.get("source_vmid"),
                        arguments.get("new_vmid"),
                        arguments.get("name"),
                        arguments.get("full_clone", True)
                    )
                elif name == "execute_vm_command":
                    result = await self.execute_vm_command(arguments.get("node"), arguments.get("vmid"), arguments.get("command"))
                else:
                    result = f"Unknown tool: {name}"

                return [TextContent(type="text", text=result)]

            except Exception as e:
                error_msg = f"Error: {str(e)}"
                self.logger.error(f"Tool execution failed: {error_msg}")
                return [TextContent(type="text", text=error_msg)]

        # 注册处理函数
        self.server.list_tools()(handle_list_tools)
        self.server.call_tool()(handle_call_tool)
    
    async def get_cluster_status(self) -> str:
        """获取集群状态"""
        try:
            if not self.proxmox_client:
                return "Error: Proxmox client not initialized"
            if not self.proxmox_client.session:
                return "Error: Proxmox client session not connected"

            status = await self.proxmox_client.get("/cluster/status")
            return json.dumps(status, indent=2)
        except Exception as e:
            self.logger.error(f"get_cluster_status failed: {e}")
            return f"Failed to get cluster status: {e}"
    
    async def list_nodes(self) -> str:
        """列出所有节点"""
        try:
            nodes = await self.proxmox_client.get("/nodes")
            return json.dumps(nodes, indent=2)
        except Exception as e:
            return f"Failed to list nodes: {e}"
    
    async def list_vms(self, node: Optional[str] = None) -> str:
        """列出虚拟机"""
        try:
            if node:
                vms = await self.proxmox_client.get(f"/nodes/{node}/qemu")
            else:
                # 获取所有节点的VM
                nodes = await self.proxmox_client.get("/nodes")
                all_vms = []
                for node_info in nodes:
                    node_name = node_info["node"]
                    try:
                        vms = await self.proxmox_client.get(f"/nodes/{node_name}/qemu")
                        for vm in vms:
                            vm["node"] = node_name
                        all_vms.extend(vms)
                    except Exception as e:
                        self.logger.warning(f"Failed to get VMs from node {node_name}: {e}")
                vms = all_vms
            
            return json.dumps(vms, indent=2)
        except Exception as e:
            return f"Failed to list VMs: {e}"

    async def start_vm(self, node: str, vmid: str) -> str:
        """启动虚拟机"""
        try:
            if not node or not vmid:
                return "Error: Both node and vmid are required"

            result = await self.proxmox_client.post(f"/nodes/{node}/qemu/{vmid}/status/start")
            return f"VM {vmid} start command sent successfully. Task: {result}"
        except Exception as e:
            return f"Failed to start VM {vmid}: {e}"

    async def stop_vm(self, node: str, vmid: str) -> str:
        """停止虚拟机"""
        try:
            if not node or not vmid:
                return "Error: Both node and vmid are required"

            result = await self.proxmox_client.post(f"/nodes/{node}/qemu/{vmid}/status/stop")
            return f"VM {vmid} stop command sent successfully. Task: {result}"
        except Exception as e:
            return f"Failed to stop VM {vmid}: {e}"

    async def restart_vm(self, node: str, vmid: str) -> str:
        """重启虚拟机"""
        try:
            if not node or not vmid:
                return "Error: Both node and vmid are required"

            result = await self.proxmox_client.post(f"/nodes/{node}/qemu/{vmid}/status/reboot")
            return f"VM {vmid} restart command sent successfully. Task: {result}"
        except Exception as e:
            return f"Failed to restart VM {vmid}: {e}"

    async def get_vm_status(self, node: str, vmid: str) -> str:
        """获取虚拟机详细状态"""
        try:
            if not node or not vmid:
                return "Error: Both node and vmid are required"

            # 获取VM状态
            status = await self.proxmox_client.get(f"/nodes/{node}/qemu/{vmid}/status/current")
            # 获取VM配置
            config = await self.proxmox_client.get(f"/nodes/{node}/qemu/{vmid}/config")

            result = {
                "status": status,
                "config": config
            }
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Failed to get VM {vmid} status: {e}"

    async def list_storage(self) -> str:
        """列出存储池"""
        try:
            storage = await self.proxmox_client.get("/storage")
            return json.dumps(storage, indent=2)
        except Exception as e:
            return f"Failed to list storage: {e}"

    async def update_vm_memory(self, node: str, vmid: str, memory: str) -> str:
        """更新虚拟机内存配置"""
        try:
            if not node or not vmid or not memory:
                return "Error: node, vmid, and memory are all required"

            # 验证内存值
            try:
                memory_mb = int(memory)
                if memory_mb < 512 or memory_mb > 32768:
                    return "Error: Memory must be between 512MB and 32GB"
            except ValueError:
                return "Error: Memory must be a valid number in MB"

            # 发送配置更新请求
            data = {"memory": memory}
            result = await self.proxmox_client.post(f"/nodes/{node}/qemu/{vmid}/config", data)

            return f"VM {vmid} memory updated to {memory}MB successfully. You need to restart the VM for changes to take effect. Task: {result}"
        except Exception as e:
            return f"Failed to update VM {vmid} memory: {e}"

    async def update_vm_cpu(self, node: str, vmid: str, cores: str) -> str:
        """更新虚拟机CPU配置"""
        try:
            if not node or not vmid or not cores:
                return "Error: node, vmid, and cores are all required"

            # 验证CPU核心数
            try:
                cpu_cores = int(cores)
                if cpu_cores < 1 or cpu_cores > 32:
                    return "Error: CPU cores must be between 1 and 32"
            except ValueError:
                return "Error: Cores must be a valid number"

            # 发送配置更新请求
            data = {"cores": cores}
            result = await self.proxmox_client.post(f"/nodes/{node}/qemu/{vmid}/config", data)

            return f"VM {vmid} CPU updated to {cores} cores successfully. You need to restart the VM for changes to take effect. Task: {result}"
        except Exception as e:
            return f"Failed to update VM {vmid} CPU: {e}"

    async def update_vm_storage(self, node: str, vmid: str, storage_size: str) -> str:
        """更新虚拟机存储大小"""
        try:
            if not node or not vmid or not storage_size:
                return "Error: node, vmid, and storage_size are all required"

            # 验证存储大小格式
            if not storage_size.endswith(('G', 'M', 'T')):
                return "Error: Storage size must end with G, M, or T (e.g., '20G', '1024M', '1T')"

            # 获取VM配置以找到主磁盘
            try:
                config = await self.proxmox_client.get(f"/nodes/{node}/qemu/{vmid}/config")

                # 查找主磁盘 (通常是 scsi0, virtio0, ide0, sata0)
                disk_key = None
                for key in ['scsi0', 'virtio0', 'ide0', 'sata0']:
                    if key in config:
                        disk_key = key
                        break

                if not disk_key:
                    return "Error: No primary disk found in VM configuration"

                # 发送磁盘扩容请求
                data = {
                    "disk": disk_key,
                    "size": storage_size
                }
                result = await self.proxmox_client.put(f"/nodes/{node}/qemu/{vmid}/resize", data)

                return f"VM {vmid} storage ({disk_key}) resized to {storage_size} successfully. Task: {result}"
            except Exception as e:
                return f"Failed to get VM configuration or resize disk: {e}"

        except Exception as e:
            return f"Failed to update VM {vmid} storage: {e}"

    async def execute_vm_command(self, node: str, vmid: str, command: str) -> str:
        """在VM中执行命令通过QEMU guest agent"""
        try:
            if not node or not vmid or not command:
                return "Error: node, vmid, and command are all required"

            # 首先检查VM状态
            vm_status = await self.proxmox_client.get(f"/nodes/{node}/qemu/{vmid}/status/current")
            if vm_status.get("status") != "running":
                return f"Error: VM {vmid} is not running (status: {vm_status.get('status', 'unknown')})"

            # 使用QEMU guest agent执行命令
            # 按照Proxmox 8+的新格式，使用数组格式传递命令
            # 对于复杂命令，使用 sh -c 来执行
            data = {
                "command": ["sh", "-c", command]
            }

            # 发送命令执行请求
            self.logger.debug(f"Sending command to guest agent: {data}")
            print(f"DEBUG: Sending command to guest agent: {data}")  # 强制输出到控制台
            try:
                exec_result = await self.proxmox_client.post(f"/nodes/{node}/qemu/{vmid}/agent/exec", data)
                self.logger.debug(f"Guest agent exec result: {exec_result}")
                print(f"DEBUG: Guest agent exec result: {exec_result}")  # 强制输出到控制台
            except Exception as e:
                self.logger.error(f"Failed to execute command via guest agent: {e}")
                print(f"DEBUG: Exception: {e}")  # 强制输出到控制台
                return f"Failed to execute command via guest agent: {e}"

            if "pid" not in exec_result:
                return f"Error: Failed to start command execution: {exec_result}"

            pid = exec_result["pid"]

            # 等待命令完成并获取结果
            import asyncio
            for attempt in range(30):  # 最多等待30秒
                try:
                    status_result = await self.proxmox_client.get(f"/nodes/{node}/qemu/{vmid}/agent/exec-status?pid={pid}")

                    if status_result.get("exited"):
                        exit_code = status_result.get("exitcode", 0)
                        stdout = status_result.get("out-data", "")
                        stderr = status_result.get("err-data", "")

                        result_text = f"Command '{command}' executed on VM {vmid}:\nExit Code: {exit_code}"
                        if stdout:
                            result_text += f"\nOutput:\n{stdout}"
                        if stderr:
                            result_text += f"\nError:\n{stderr}"

                        return result_text

                    await asyncio.sleep(1)
                except Exception as e:
                    self.logger.debug(f"Attempt {attempt + 1} failed: {e}")
                    await asyncio.sleep(1)
                    continue

            return f"Warning: Command may still be running. PID: {pid}"

        except Exception as e:
            return f"Failed to execute command on VM {vmid}: {e}"

    async def clone_vm(self, node: str, source_vmid: str, new_vmid: str, name: str, full_clone: bool = True) -> str:
        """从模板或现有VM克隆新VM"""
        try:
            if not node or not source_vmid or not new_vmid or not name:
                return "Error: node, source_vmid, new_vmid, and name are all required"

            # 验证VM ID
            try:
                int(source_vmid)  # 验证源VM ID是数字
                new_id = int(new_vmid)
                if new_id < 100 or new_id > 999999:
                    return "Error: New VM ID must be between 100 and 999999"
            except ValueError:
                return "Error: VM IDs must be valid numbers"

            # 准备克隆参数
            data = {
                "newid": new_vmid,
                "name": name,
                "full": "1" if full_clone else "0"
            }

            # 发送克隆请求
            result = await self.proxmox_client.post(f"/nodes/{node}/qemu/{source_vmid}/clone", data)

            return f"VM {source_vmid} cloned to new VM {new_vmid} (name: {name}) successfully. Task: {result}"
        except Exception as e:
            return f"Failed to clone VM {source_vmid}: {e}"

    async def run(self):
        """运行服务器"""
        try:
            await self.initialize()
            
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )
        finally:
            if self.proxmox_client:
                await self.proxmox_client.close()


async def main():
    """主函数"""
    server = StandaloneMCPServer()
    await server.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Server failed: {e}")
        sys.exit(1)
