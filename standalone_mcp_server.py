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
        CallToolRequest,
        CallToolResult,
        ListToolsRequest,
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
        self.auth_header = f"PVEAPIToken={config.auth.user}!{config.auth.token_name}={config.auth.token_value}"
        
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
        async with self.session.get(url) as resp:
            if resp.status == 401:
                raise Exception("401 Unauthorized: invalid token value!")
            elif resp.status != 200:
                raise Exception(f"HTTP {resp.status}: {await resp.text()}")
            data = await resp.json()
            return data.get("data", {})
    
    async def post(self, path: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """POST请求"""
        if not self.session:
            raise Exception("Client not connected")
            
        url = f"{self.base_url}{path}"
        async with self.session.post(url, data=data or {}) as resp:
            if resp.status not in [200, 201]:
                raise Exception(f"HTTP {resp.status}: {await resp.text()}")
            response_data = await resp.json()
            return response_data.get("data", {})


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
            level=getattr(logging, config.level.upper()),
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
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
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
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(request: CallToolRequest) -> CallToolResult:
            try:
                tool_name = request.params.name
                arguments = request.params.arguments or {}
                
                if tool_name == "get_cluster_status":
                    result = await self.get_cluster_status()
                elif tool_name == "list_nodes":
                    result = await self.list_nodes()
                elif tool_name == "list_vms":
                    result = await self.list_vms(arguments.get("node"))
                else:
                    return CallToolResult(
                        content=[TextContent(type="text", text=f"Unknown tool: {tool_name}")],
                        isError=True
                    )
                
                return CallToolResult(
                    content=[TextContent(type="text", text=result)]
                )
                
            except Exception as e:
                self.logger.error(f"Tool execution failed: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True
                )
    
    async def get_cluster_status(self) -> str:
        """获取集群状态"""
        try:
            status = await self.proxmox_client.get("/cluster/status")
            return json.dumps(status, indent=2)
        except Exception as e:
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
