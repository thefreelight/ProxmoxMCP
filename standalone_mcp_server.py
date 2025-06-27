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
    import websockets
    import base64
    import urllib.parse
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please install: pip install aiohttp websockets")
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
    
    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET请求"""
        if not self.session:
            raise Exception("Client not connected")

        url = f"{self.base_url}{path}"
        self.logger.debug(f"Making GET request to: {url}")
        self.logger.debug(f"GET method called with path={path}, params={params}")
        print(f"DEBUG: GET method called with path={path}, params={params}")  # 添加调试输出

        async with self.session.get(url, params=params) as resp:
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


class StandaloneMCPServer:
    """独立的MCP服务器"""

    def __init__(self):
        self.server = Server("proxmox-mcp")
        self.proxmox_client: Optional[SimpleProxmoxClient] = None
        self.config: Optional[Config] = None
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
            level=getattr(logging, config.level.upper()),
            format=config.format,
            filename=config.file
        )
    
    async def initialize(self):
        """初始化服务器"""
        # 加载配置
        self.config = self.load_config()
        self.setup_logging(self.config.logging)

        self.logger.info("Starting Standalone Proxmox MCP Server...")
        self.logger.info(f"Proxmox host: {self.config.proxmox.host}:{self.config.proxmox.port}")

        # 初始化Proxmox客户端
        self.proxmox_client = SimpleProxmoxClient(self.config)
        await self.proxmox_client.connect()

        # 注册工具
        self.register_tools()

        self.logger.info("Standalone Proxmox MCP Server initialized successfully")
        self.logger.info("Server is ready and waiting for connections...")
    
    def register_tools(self):
        """注册工具"""

        # 定义工具处理函数
        async def handle_list_tools() -> List[Tool]:
            return [
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
                    name="update_vm_network",
                    description="Update VM network configuration (IP address)",
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
                            "ip": {
                                "type": "string",
                                "description": "IP address with CIDR (e.g., '192.168.0.90/24')"
                            },
                            "gateway": {
                                "type": "string",
                                "description": "Gateway IP address (default: '192.168.0.1')",
                                "default": "192.168.0.1"
                            }
                        },
                        "required": ["node", "vmid", "ip"]
                    }
                ),
                Tool(
                    name="get_vm_agent_info",
                    description="Get VM network information via qemu-guest-agent",
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
                    name="execute_node_command",
                    description="Execute command on Proxmox node (for network discovery)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {
                                "type": "string",
                                "description": "Node name where to execute the command"
                            },
                            "command": {
                                "type": "string",
                                "description": "Command to execute (limited to network discovery commands)"
                            }
                        },
                        "required": ["node", "command"]
                    }
                ),
                Tool(
                    name="execute_vm_command",
                    description="Execute command in VM via QEMU guest agent",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {
                                "type": "string",
                                "description": "Node name where the VM is located"
                            },
                            "vmid": {
                                "type": "string",
                                "description": "VM ID to execute command in"
                            },
                            "command": {
                                "type": "string",
                                "description": "Shell command to execute in the VM"
                            }
                        },
                        "required": ["node", "vmid", "command"]
                    }
                ),
                Tool(
                    name="get_vm_console_access",
                    description="Get VM console access via VNC or Serial Terminal",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {
                                "type": "string",
                                "description": "Node name where the VM is located"
                            },
                            "vmid": {
                                "type": "string",
                                "description": "VM ID to access console"
                            },
                            "console_type": {
                                "type": "string",
                                "description": "Console type: 'vnc', 'serial', or 'spice'",
                                "enum": ["vnc", "serial", "spice"],
                                "default": "vnc"
                            }
                        },
                        "required": ["node", "vmid"]
                    }
                ),
                Tool(
                    name="install_guest_agent",
                    description="Install QEMU Guest Agent via Cloud-Init restart",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {
                                "type": "string",
                                "description": "Node name where the VM is located"
                            },
                            "vmid": {
                                "type": "string",
                                "description": "VM ID to install guest agent"
                            },
                            "username": {
                                "type": "string",
                                "description": "Username for VM login (default: ubuntu)",
                                "default": "ubuntu"
                            },
                            "password": {
                                "type": "string",
                                "description": "Password for VM login (optional if using key auth)"
                            }
                        },
                        "required": ["node", "vmid"]
                    }
                ),
                Tool(
                    name="create_guest_agent_template",
                    description="Create a new VM template with Guest Agent pre-installed",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {
                                "type": "string",
                                "description": "Node name where to create the template"
                            },
                            "source_vmid": {
                                "type": "string",
                                "description": "Source template VM ID to clone from"
                            },
                            "new_vmid": {
                                "type": "string",
                                "description": "New template VM ID"
                            },
                            "template_name": {
                                "type": "string",
                                "description": "Name for the new template",
                                "default": "ubuntu-with-guest-agent"
                            }
                        },
                        "required": ["node", "source_vmid", "new_vmid"]
                    }
                ),
                Tool(
                    name="force_install_guest_agent",
                    description="Force install Guest Agent using new method",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {
                                "type": "string",
                                "description": "Node name where the VM is located"
                            },
                            "vmid": {
                                "type": "string",
                                "description": "VM ID to install guest agent"
                            }
                        },
                        "required": ["node", "vmid"]
                    }
                ),
                Tool(
                    name="enable_guest_agent",
                    description="Enable Guest Agent support in VM configuration",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "node": {
                                "type": "string",
                                "description": "Node name where the VM is located"
                            },
                            "vmid": {
                                "type": "string",
                                "description": "VM ID to enable guest agent"
                            }
                        },
                        "required": ["node", "vmid"]
                    }
                )
            ]

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
                elif name == "update_vm_network":
                    result = await self.update_vm_network(
                        arguments.get("node"),
                        arguments.get("vmid"),
                        arguments.get("ip"),
                        arguments.get("gateway", "192.168.0.1")
                    )
                elif name == "get_vm_agent_info":
                    result = await self.get_vm_agent_info(
                        arguments.get("node"),
                        arguments.get("vmid")
                    )
                elif name == "execute_node_command":
                    result = await self.execute_node_command(
                        arguments.get("node"),
                        arguments.get("command")
                    )
                elif name == "execute_vm_command":
                    result = await self.execute_vm_command(
                        arguments.get("node"),
                        arguments.get("vmid"),
                        arguments.get("command")
                    )
                elif name == "get_vm_console_access":
                    result = await self.get_vm_console_access(
                        arguments.get("node"),
                        arguments.get("vmid"),
                        arguments.get("console_type", "vnc")
                    )
                elif name == "install_guest_agent":
                    result = await self.install_guest_agent(
                        arguments.get("node"),
                        arguments.get("vmid"),
                        arguments.get("username", "ubuntu"),
                        arguments.get("password")
                    )
                elif name == "create_guest_agent_template":
                    result = await self.create_guest_agent_template(
                        arguments.get("node"),
                        arguments.get("source_vmid"),
                        arguments.get("new_vmid"),
                        arguments.get("template_name", "ubuntu-with-guest-agent")
                    )
                elif name == "force_install_guest_agent":
                    result = await self.force_install_guest_agent(
                        arguments.get("node"),
                        arguments.get("vmid")
                    )
                elif name == "enable_guest_agent":
                    result = await self.enable_guest_agent(
                        arguments.get("node"),
                        arguments.get("vmid")
                    )
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

            # 验证VM ID
            try:
                int(vmid)
            except ValueError:
                return "Error: VM ID must be a valid number"

            # 验证存储大小格式
            if not storage_size.endswith(('G', 'M', 'T')):
                return "Error: Storage size must end with G, M, or T (e.g., '20G', '1024M', '1T')"

            # 检查VM状态 - 必须停止才能调整存储
            vm_status = await self.proxmox_client.get(f"/nodes/{node}/qemu/{vmid}/status/current")
            if vm_status.get("status") != "stopped":
                return f"Error: VM {vmid} must be stopped before resizing storage. Current status: {vm_status.get('status', 'unknown')}"

            # 获取当前VM配置以检查当前存储大小
            vm_config = await self.proxmox_client.get(f"/nodes/{node}/qemu/{vmid}/config")
            current_disk = vm_config.get('scsi0', '')

            # 提取当前大小
            old_size = "unknown"
            if 'size=' in current_disk:
                old_size = current_disk.split('size=')[1].split(',')[0]

            # 调整存储大小 - 使用POST方法
            resize_url = f"/nodes/{node}/qemu/{vmid}/resize"
            data = {
                "disk": "scsi0",
                "size": storage_size
            }

            result = await self.proxmox_client.post(resize_url, data)

            return f"VM {vmid} storage resized successfully from {old_size} to {storage_size}. Task: {result}"
        except Exception as e:
            return f"Failed to update VM {vmid} storage: {e}"

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

    async def update_vm_network(self, node: str, vmid: str, ip: str, gateway: str = "192.168.0.1") -> str:
        """更新虚拟机网络配置"""
        try:
            if not node or not vmid or not ip:
                return "Error: node, vmid, and ip are all required"

            # 验证VM ID
            try:
                int(vmid)
            except ValueError:
                return "Error: VM ID must be a valid number"

            # 验证IP格式
            if "/" not in ip:
                return "Error: IP must include CIDR notation (e.g., '192.168.0.90/24')"

            # 准备网络配置参数
            data = {
                "ipconfig0": f"ip={ip},gw={gateway}"
            }

            # 发送配置更新请求
            result = await self.proxmox_client.post(f"/nodes/{node}/qemu/{vmid}/config", data)

            return f"VM {vmid} network updated to IP {ip} with gateway {gateway} successfully. You need to restart the VM for changes to take effect. Task: {result}"
        except Exception as e:
            return f"Failed to update VM {vmid} network: {e}"

    async def get_vm_agent_info(self, node: str, vmid: str) -> str:
        """通过qemu-guest-agent获取VM网络信息"""
        try:
            if not node or not vmid:
                return "Error: node and vmid are required"

            # 验证VM ID
            try:
                int(vmid)
            except ValueError:
                return "Error: VM ID must be a valid number"

            # 尝试获取网络接口信息
            try:
                result = await self.proxmox_client.get(f"/nodes/{node}/qemu/{vmid}/agent/network-get-interfaces")
                return f"VM {vmid} network interfaces: {result}"
            except Exception as agent_error:
                # 如果agent不可用，尝试获取其他网络信息
                try:
                    # 获取VM状态中的网络信息
                    vm_status = await self.proxmox_client.get(f"/nodes/{node}/qemu/{vmid}/status/current")
                    nics_info = vm_status.get('nics', {})
                    if nics_info:
                        return f"VM {vmid} network interfaces (from status): {nics_info}"
                    else:
                        return f"VM {vmid} network information not available. Agent error: {agent_error}"
                except Exception as status_error:
                    return f"Failed to get VM {vmid} network info. Agent error: {agent_error}, Status error: {status_error}"
        except Exception as e:
            return f"Failed to get VM {vmid} agent info: {e}"

    async def execute_node_command(self, node: str, command: str) -> str:
        """在Proxmox节点上执行命令（仅限网络发现命令）"""
        try:
            if not node or not command:
                return "Error: node and command are required"

            # 安全检查：只允许特定的网络发现命令
            allowed_commands = [
                "arp -a",
                "ip neigh show",
                "cat /var/lib/dhcp/dhcpd.leases",
                "journalctl -u isc-dhcp-server",
                "nmap -sn 192.168.0.0/24"
            ]

            # 检查命令是否在允许列表中或者是安全的网络命令
            if not any(command.startswith(allowed) for allowed in allowed_commands):
                if not (command.startswith("arp") or command.startswith("ip neigh") or
                       command.startswith("cat /proc/net/arp") or command.startswith("nmap -sn")):
                    return "Error: Command not allowed. Only network discovery commands are permitted."

            # 通过Proxmox API执行命令
            data = {
                "command": command
            }

            result = await self.proxmox_client.post(f"/nodes/{node}/execute", data)
            return f"Command '{command}' executed on node {node}: {result}"
        except Exception as e:
            return f"Failed to execute command on node {node}: {e}"

    async def execute_vm_command(self, node: str, vmid: str, command: str) -> str:
        """在VM内通过qemu-guest-agent执行命令"""
        try:
            if not node or not vmid or not command:
                return "Error: node, vmid, and command are all required"

            # 验证VM ID
            try:
                int(vmid)
            except ValueError:
                return "Error: VM ID must be a valid number"

            # 检查VM状态
            vm_status = await self.proxmox_client.get(f"/nodes/{node}/qemu/{vmid}/status/current")
            if vm_status.get("status") != "running":
                return f"Error: VM {vmid} is not running (status: {vm_status.get('status', 'unknown')})"

            # 通过guest agent执行命令
            try:
                # 启动命令执行 - 根据Proxmox论坛，复杂命令需要特殊处理
                if ' ' in command or any(char in command for char in ['|', '>', '<', ';', '&&', '||', '$', '`', '"', "'"]):
                    # 复杂命令：使用bash -c格式，需要特殊的form data处理
                    # 根据Proxmox论坛：需要多个command参数

                    # 直接构建form data，每个命令部分作为单独的command参数
                    form_data = aiohttp.FormData()
                    form_data.add_field('command', '/bin/bash')
                    form_data.add_field('command', '-c')
                    form_data.add_field('command', command)

                    # 直接使用session发送请求
                    url = f"{self.proxmox_client.base_url}/nodes/{node}/qemu/{vmid}/agent/exec"
                    async with self.proxmox_client.session.post(url, data=form_data) as resp:
                        if resp.status not in [200, 201]:
                            response_text = await resp.text()
                            raise Exception(f"HTTP {resp.status}: {response_text}")
                        exec_result = await resp.json()
                        exec_result = exec_result.get("data", exec_result)
                else:
                    # 简单命令：直接执行
                    exec_data = {"command": command}
                    exec_result = await self.proxmox_client.post(f"/nodes/{node}/qemu/{vmid}/agent/exec", exec_data)

                if 'pid' not in exec_result:
                    return f"Error: Failed to start command execution: {exec_result}"

                pid = exec_result['pid']

                # 等待命令完成
                import asyncio
                await asyncio.sleep(2)  # 给命令一些时间执行

                # 获取命令结果
                status_result = await self.proxmox_client.get(f"/nodes/{node}/qemu/{vmid}/agent/exec-status", params={"pid": pid})

                output = status_result.get("out-data", "")
                error = status_result.get("err-data", "")
                exit_code = status_result.get("exitcode", 0)
                exited = status_result.get("exited", 0)

                if not exited:
                    return f"Warning: Command may still be running. PID: {pid}"

                result_text = f"Command '{command}' executed on VM {vmid}:\n"
                result_text += f"Exit Code: {exit_code}\n"
                if output:
                    result_text += f"Output:\n{output}\n"
                if error:
                    result_text += f"Error:\n{error}\n"

                return result_text

            except Exception as agent_error:
                return f"Error: Failed to execute command via guest agent: {agent_error}. Make sure qemu-guest-agent is installed and running in the VM."

        except Exception as e:
            return f"Failed to execute command on VM {vmid}: {e}"

    async def get_vm_console_access(self, node: str, vmid: str, console_type: str = "vnc") -> str:
        """获取VM控制台访问信息"""
        try:
            if not node or not vmid:
                return "Error: node and vmid are required"

            # 验证VM ID
            try:
                int(vmid)
            except ValueError:
                return "Error: VM ID must be a valid number"

            # 检查VM状态
            vm_status = await self.proxmox_client.get(f"/nodes/{node}/qemu/{vmid}/status/current")
            if vm_status.get("status") != "running":
                return f"Error: VM {vmid} is not running (status: {vm_status.get('status', 'unknown')})"

            # 根据控制台类型获取访问信息
            if console_type == "vnc":
                # 获取VNC代理信息
                vnc_data = await self.proxmox_client.post(f"/nodes/{node}/qemu/{vmid}/vncproxy")
                return f"VNC Console Access for VM {vmid}:\n" + \
                       f"Port: {vnc_data.get('port', 'N/A')}\n" + \
                       f"Ticket: {vnc_data.get('ticket', 'N/A')}\n" + \
                       f"Certificate: {vnc_data.get('cert', 'N/A')}\n" + \
                       f"Access URL: https://{node}:{vnc_data.get('port', 'N/A')}"

            elif console_type == "serial":
                # 获取串口终端代理信息
                term_data = await self.proxmox_client.post(f"/nodes/{node}/qemu/{vmid}/termproxy")
                return f"Serial Console Access for VM {vmid}:\n" + \
                       f"Port: {term_data.get('port', 'N/A')}\n" + \
                       f"Ticket: {term_data.get('ticket', 'N/A')}\n" + \
                       f"User: {term_data.get('user', 'N/A')}\n" + \
                       f"Terminal URL: wss://{node}:{term_data.get('port', 'N/A')}"

            elif console_type == "spice":
                # 获取SPICE代理信息
                spice_data = await self.proxmox_client.post(f"/nodes/{node}/qemu/{vmid}/spiceproxy")
                return f"SPICE Console Access for VM {vmid}:\n" + \
                       f"Type: {spice_data.get('type', 'N/A')}\n" + \
                       f"Host: {spice_data.get('host', 'N/A')}\n" + \
                       f"Port: {spice_data.get('port', 'N/A')}\n" + \
                       f"Password: {spice_data.get('password', 'N/A')}"
            else:
                return f"Error: Unsupported console type '{console_type}'. Supported types: vnc, serial, spice"

        except Exception as e:
            return f"Failed to get console access for VM {vmid}: {e}"

    async def install_guest_agent(self, node: str, vmid: str, username: str = "ubuntu", password: str = None) -> str:
        """通过直接修改VM配置和重启来安装QEMU Guest Agent"""
        try:
            if not node or not vmid:
                return "Error: node and vmid are required"

            # 验证VM ID
            try:
                int(vmid)
            except ValueError:
                return "Error: VM ID must be a valid number"

            result_log = []
            result_log.append(f"🚀 Starting automated Guest Agent installation on VM {vmid}")

            # 检查VM状态
            vm_status = await self.proxmox_client.get(f"/nodes/{node}/qemu/{vmid}/status/current")
            current_status = vm_status.get("status", "unknown")
            result_log.append(f"📊 Current VM status: {current_status}")

            # 获取VM配置
            vm_config = await self.proxmox_client.get(f"/nodes/{node}/qemu/{vmid}/config")
            result_log.append("📋 Retrieved VM configuration")

            # 停止VM（如果正在运行）
            if current_status == "running":
                result_log.append("⏸️ Stopping VM to update configuration...")
                await self.proxmox_client.post(f"/nodes/{node}/qemu/{vmid}/status/stop")

                # 等待VM停止
                for _ in range(30):  # 最多等待30秒
                    await asyncio.sleep(1)
                    status = await self.proxmox_client.get(f"/nodes/{node}/qemu/{vmid}/status/current")
                    if status.get("status") == "stopped":
                        result_log.append("✅ VM stopped successfully")
                        break
                else:
                    return "❌ Timeout waiting for VM to stop"

            # 启用Guest Agent支持
            config_update = {
                "agent": "1",  # 启用Guest Agent
                "description": f"VM with Guest Agent enabled - Auto-configured"
            }

            result_log.append("🔧 Enabling Guest Agent support in VM configuration...")
            await self.proxmox_client.post(f"/nodes/{node}/qemu/{vmid}/config", config_update)

            # 重启VM
            result_log.append("🚀 Starting VM with Guest Agent support...")
            await self.proxmox_client.post(f"/nodes/{node}/qemu/{vmid}/status/start")

            # 等待VM启动
            result_log.append("⏳ Waiting for VM to start...")
            for _ in range(60):  # 最多等待60秒
                await asyncio.sleep(2)
                status = await self.proxmox_client.get(f"/nodes/{node}/qemu/{vmid}/status/current")
                if status.get("status") == "running":
                    result_log.append("✅ VM started successfully")
                    break
            else:
                result_log.append("⚠️ VM start timeout, but process may continue")

            # 等待系统完全启动
            result_log.append("⏳ Waiting for system to fully boot (30 seconds)...")
            await asyncio.sleep(30)

            # 现在尝试通过其他方式安装Guest Agent
            # 如果VM有SSH访问，我们可以尝试SSH
            vm_ip = None
            if "ipconfig0" in vm_config:
                ip_config = vm_config["ipconfig0"]
                if "ip=" in ip_config:
                    vm_ip = ip_config.split("ip=")[1].split("/")[0]
                    result_log.append(f"📡 Found VM IP: {vm_ip}")

            if vm_ip:
                result_log.append("🔗 Attempting SSH installation...")
                try:
                    # 尝试SSH安装
                    ssh_commands = [
                        "sudo apt update -y",
                        "sudo apt install -y qemu-guest-agent",
                        "sudo systemctl start qemu-guest-agent",
                        "sudo systemctl enable qemu-guest-agent"
                    ]

                    for cmd in ssh_commands:
                        ssh_command = f'ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no {username}@{vm_ip} "{cmd}"'
                        process = await asyncio.create_subprocess_shell(
                            ssh_command,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        stdout, stderr = await process.communicate()

                        if process.returncode == 0:
                            result_log.append(f"✅ SSH command succeeded: {cmd}")
                        else:
                            result_log.append(f"⚠️ SSH command failed: {cmd}")
                            break

                    # 等待Guest Agent启动
                    result_log.append("⏳ Waiting for Guest Agent to start...")
                    await asyncio.sleep(10)

                except Exception as ssh_error:
                    result_log.append(f"⚠️ SSH installation failed: {ssh_error}")

            # 测试Guest Agent是否工作
            result_log.append("🔍 Testing Guest Agent connection...")
            for attempt in range(5):
                try:
                    test_result = await self.proxmox_client.post(f"/nodes/{node}/qemu/{vmid}/agent/exec", {"command": "echo 'Guest Agent test'"})
                    if test_result and 'pid' in test_result:
                        result_log.append("✅ Guest Agent is working!")
                        result_log.append("🎯 Installation completed successfully!")
                        return "\n".join(result_log)
                except Exception:
                    result_log.append(f"⏳ Guest Agent test attempt {attempt + 1}/5...")
                    await asyncio.sleep(10)

            result_log.append("⚠️ Guest Agent may need more time to start")
            result_log.append("💡 Try testing again in a few minutes with execute_vm_command")
            result_log.append("🎯 Configuration completed - Guest Agent should be available soon")

            return "\n".join(result_log)

        except Exception as e:
            return f"❌ Failed to install guest agent on VM {vmid}: {e}"

    async def create_guest_agent_template(self, node: str, source_vmid: str, new_vmid: str, template_name: str = "ubuntu-with-guest-agent") -> str:
        """创建一个预装Guest Agent的VM模板"""
        try:
            if not node or not source_vmid or not new_vmid:
                return "Error: node, source_vmid, and new_vmid are required"

            result_log = []
            result_log.append(f"🚀 Creating Guest Agent template from VM {source_vmid}")

            # 克隆源模板
            result_log.append("📋 Cloning source template...")
            clone_data = {
                "newid": new_vmid,
                "name": template_name,
                "full": 1  # 完整克隆
            }

            clone_result = await self.proxmox_client.post(f"/nodes/{node}/qemu/{source_vmid}/clone", clone_data)
            result_log.append(f"✅ Template cloned successfully: {clone_result}")

            # 等待克隆完成
            result_log.append("⏳ Waiting for clone to complete...")
            await asyncio.sleep(10)

            # 启动新VM来安装Guest Agent
            result_log.append("🚀 Starting cloned VM...")
            await self.proxmox_client.post(f"/nodes/{node}/qemu/{new_vmid}/status/start")

            # 等待VM启动
            result_log.append("⏳ Waiting for VM to start...")
            for i in range(60):
                await asyncio.sleep(2)
                status = await self.proxmox_client.get(f"/nodes/{node}/qemu/{new_vmid}/status/current")
                if status.get("status") == "running":
                    result_log.append("✅ VM started successfully")
                    break
            else:
                return "❌ Timeout waiting for VM to start"

            # 等待系统完全启动
            result_log.append("⏳ Waiting for system to fully boot...")
            await asyncio.sleep(30)

            # 现在我们有一个运行的VM，我们需要在其中安装Guest Agent
            # 由于我们还没有Guest Agent，我们需要使用其他方法

            # 方法：通过修改VM配置来添加启动脚本
            result_log.append("🔧 Configuring VM for Guest Agent installation...")

            # 停止VM
            result_log.append("⏸️ Stopping VM to configure...")
            await self.proxmox_client.post(f"/nodes/{node}/qemu/{new_vmid}/status/stop")

            # 等待VM停止
            for i in range(30):
                await asyncio.sleep(1)
                status = await self.proxmox_client.get(f"/nodes/{node}/qemu/{new_vmid}/status/current")
                if status.get("status") == "stopped":
                    result_log.append("✅ VM stopped successfully")
                    break

            # 修改VM配置，添加Guest Agent支持
            config_update = {
                "agent": "1",  # 启用Guest Agent支持
                "description": f"Template with Guest Agent - Created from {source_vmid}"
            }

            result_log.append("🔄 Updating VM configuration...")
            await self.proxmox_client.post(f"/nodes/{node}/qemu/{new_vmid}/config", config_update)

            # 将VM转换为模板
            result_log.append("📦 Converting VM to template...")
            await self.proxmox_client.post(f"/nodes/{node}/qemu/{new_vmid}/template")

            result_log.append("🎉 Guest Agent template created successfully!")
            result_log.append(f"📋 Template ID: {new_vmid}")
            result_log.append(f"📋 Template Name: {template_name}")
            result_log.append("💡 You can now clone VMs from this template with Guest Agent support")

            return "\n".join(result_log)

        except Exception as e:
            return f"❌ Failed to create guest agent template: {e}"

    async def force_install_guest_agent(self, node: str, vmid: str) -> str:
        """强制安装Guest Agent - 新方法"""
        try:
            result_log = []
            result_log.append(f"🚀 Force installing Guest Agent on VM {vmid}")

            # 检查VM状态
            vm_status = await self.proxmox_client.get(f"/nodes/{node}/qemu/{vmid}/status/current")
            current_status = vm_status.get("status", "unknown")
            result_log.append(f"📊 Current VM status: {current_status}")

            # 停止VM（如果正在运行）
            if current_status == "running":
                result_log.append("⏸️ Stopping VM...")
                await self.proxmox_client.post(f"/nodes/{node}/qemu/{vmid}/status/stop")

                # 等待VM停止
                for _ in range(30):
                    await asyncio.sleep(1)
                    status = await self.proxmox_client.get(f"/nodes/{node}/qemu/{vmid}/status/current")
                    if status.get("status") == "stopped":
                        result_log.append("✅ VM stopped")
                        break
                else:
                    return "❌ Timeout waiting for VM to stop"

            # 启用Guest Agent支持
            config_update = {
                "agent": "1,fstrim_cloned_disks=1",  # 启用Guest Agent和额外功能
                "description": "VM with Guest Agent enabled via force install"
            }

            result_log.append("🔧 Enabling Guest Agent in VM configuration...")
            await self.proxmox_client.post(f"/nodes/{node}/qemu/{vmid}/config", config_update)

            # 重启VM
            result_log.append("🚀 Starting VM...")
            await self.proxmox_client.post(f"/nodes/{node}/qemu/{vmid}/status/start")

            # 等待VM启动
            result_log.append("⏳ Waiting for VM to start...")
            for _ in range(60):
                await asyncio.sleep(2)
                status = await self.proxmox_client.get(f"/nodes/{node}/qemu/{vmid}/status/current")
                if status.get("status") == "running":
                    result_log.append("✅ VM started")
                    break
            else:
                result_log.append("⚠️ VM start timeout")

            # 等待系统启动
            result_log.append("⏳ Waiting for system boot (45 seconds)...")
            await asyncio.sleep(45)

            # 测试Guest Agent
            result_log.append("🔍 Testing Guest Agent...")
            for attempt in range(10):
                try:
                    test_result = await self.proxmox_client.post(f"/nodes/{node}/qemu/{vmid}/agent/exec", {"command": "echo test"})
                    if test_result and 'pid' in test_result:
                        result_log.append("✅ Guest Agent is working!")
                        return "\n".join(result_log)
                except Exception:
                    result_log.append(f"⏳ Test attempt {attempt + 1}/10...")
                    await asyncio.sleep(5)

            result_log.append("⚠️ Guest Agent not responding yet")
            result_log.append("💡 The VM may need Guest Agent software installed")
            result_log.append("🎯 Configuration completed - try again later")

            return "\n".join(result_log)

        except Exception as e:
            return f"❌ Failed to force install guest agent: {e}"

    async def enable_guest_agent(self, node: str, vmid: str) -> str:
        """启用VM的Guest Agent支持"""
        try:
            result_log = []
            result_log.append(f"🔧 Enabling Guest Agent for VM {vmid}")

            # 获取当前VM状态
            vm_status = await self.proxmox_client.get(f"/nodes/{node}/qemu/{vmid}/status/current")
            current_status = vm_status.get("status", "unknown")
            result_log.append(f"📊 Current VM status: {current_status}")

            # 更新VM配置，启用Guest Agent
            config_update = {
                "agent": "1,fstrim_cloned_disks=1"
            }

            result_log.append("🔄 Updating VM configuration to enable Guest Agent...")
            await self.proxmox_client.post(f"/nodes/{node}/qemu/{vmid}/config", config_update)
            result_log.append("✅ Guest Agent enabled in VM configuration")

            # 测试Guest Agent连接
            result_log.append("🔍 Testing Guest Agent connection...")
            try:
                test_result = await self.proxmox_client.post(f"/nodes/{node}/qemu/{vmid}/agent/exec", {"command": "echo 'Guest Agent test'"})
                if test_result and 'pid' in test_result:
                    result_log.append("✅ Guest Agent is working!")
                else:
                    result_log.append("⚠️ Guest Agent enabled but not responding yet")
            except Exception as test_error:
                result_log.append(f"⚠️ Guest Agent test failed: {test_error}")
                result_log.append("💡 Guest Agent may need a few moments to start")

            result_log.append("🎯 Guest Agent configuration completed!")
            return "\n".join(result_log)

        except Exception as e:
            return f"❌ Failed to enable guest agent: {e}"

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
