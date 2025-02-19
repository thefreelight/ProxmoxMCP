#!/usr/bin/env python3
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.tools import Tool
from mcp.server.fastmcp.tools.base import Tool as BaseTool
from mcp.types import CallToolResult as Response, TextContent as Content
from proxmoxer import ProxmoxAPI
from pydantic import BaseModel

from .tools.vm_console import VMConsoleManager

class ProxmoxConfig(BaseModel):
    host: str
    port: int = 8006
    verify_ssl: bool = True
    service: str = "PVE"

class AuthConfig(BaseModel):
    user: str
    token_name: str
    token_value: str

class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None

class Config(BaseModel):
    proxmox: ProxmoxConfig
    auth: AuthConfig
    logging: LoggingConfig

class ProxmoxMCPServer:
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self._setup_logging()
        self.proxmox = self._setup_proxmox()
        self.vm_console = VMConsoleManager(self.proxmox)
        self.mcp = FastMCP("ProxmoxMCP")
        self._setup_tools()

    def _load_config(self, config_path: Optional[str]) -> Config:
        """Load configuration from file or environment variables."""
        if config_path:
            with open(config_path) as f:
                config_data = json.load(f)
        else:
            # Load from environment variables
            config_data = {
                "proxmox": {
                    "host": os.getenv("PROXMOX_HOST", ""),
                    "port": int(os.getenv("PROXMOX_PORT", "8006")),
                    "verify_ssl": os.getenv("PROXMOX_VERIFY_SSL", "true").lower() == "true",
                    "service": os.getenv("PROXMOX_SERVICE", "PVE"),
                },
                "auth": {
                    "user": os.getenv("PROXMOX_USER", ""),
                    "token_name": os.getenv("PROXMOX_TOKEN_NAME", ""),
                    "token_value": os.getenv("PROXMOX_TOKEN_VALUE", ""),
                },
                "logging": {
                    "level": os.getenv("LOG_LEVEL", "INFO"),
                    "format": os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
                    "file": os.getenv("LOG_FILE"),
                },
            }

        return Config(**config_data)

    def _setup_logging(self) -> None:
        """Configure logging based on settings."""
        logging.basicConfig(
            level=getattr(logging, self.config.logging.level.upper()),
            format=self.config.logging.format,
            filename=self.config.logging.file,
        )
        self.logger = logging.getLogger("proxmox-mcp")

    def _setup_proxmox(self) -> ProxmoxAPI:
        """Initialize Proxmox API connection."""
        try:
            return ProxmoxAPI(
                host=self.config.proxmox.host,
                port=self.config.proxmox.port,
                user=self.config.auth.user,
                token_name=self.config.auth.token_name,
                token_value=self.config.auth.token_value,
                verify_ssl=self.config.proxmox.verify_ssl,
                service=self.config.proxmox.service,
            )
        except Exception as e:
            self.logger.error(f"Failed to connect to Proxmox: {e}")
            raise

    def _setup_tools(self) -> None:
        """Register MCP tools."""

        @self.mcp.tool()
        def get_nodes() -> List[Content]:
            """List all nodes in the Proxmox cluster."""
            try:
                result = self.proxmox.nodes.get()
                nodes = [{"node": node["node"], "status": node["status"]} for node in result]
                return [Content(type="text", text=json.dumps(nodes))]
            except Exception as e:
                self.logger.error(f"Failed to get nodes: {e}")
                raise

        @self.mcp.tool()
        def get_node_status(node: str) -> List[Content]:
            """Get detailed status of a specific node.

            Args:
                node: Name of the node to get status for
            """
            try:
                result = self.proxmox.nodes(node).status.get()
                return [Content(type="text", text=json.dumps(result))]
            except Exception as e:
                self.logger.error(f"Failed to get node status: {e}")
                raise

        @self.mcp.tool()
        def get_vms() -> List[Content]:
            """List all VMs across the cluster."""
            try:
                result = []
                for node in self.proxmox.nodes.get():
                    vms = self.proxmox.nodes(node["node"]).qemu.get()
                    result.extend([{
                        "vmid": vm["vmid"],
                        "name": vm["name"],
                        "status": vm["status"],
                        "node": node["node"]
                    } for vm in vms])
                return [Content(type="text", text=json.dumps(result))]
            except Exception as e:
                self.logger.error(f"Failed to get VMs: {e}")
                raise

        @self.mcp.tool()
        def get_containers() -> List[Content]:
            """List all LXC containers."""
            try:
                result = []
                for node in self.proxmox.nodes.get():
                    containers = self.proxmox.nodes(node["node"]).lxc.get()
                    result.extend([{
                        "vmid": container["vmid"],
                        "name": container["name"],
                        "status": container["status"],
                        "node": node["node"]
                    } for container in containers])
                return [Content(type="text", text=json.dumps(result))]
            except Exception as e:
                self.logger.error(f"Failed to get containers: {e}")
                raise

        @self.mcp.tool()
        def get_storage() -> List[Content]:
            """List available storage."""
            try:
                result = self.proxmox.storage.get()
                storage = [{"storage": storage["storage"], "type": storage["type"]} for storage in result]
                return [Content(type="text", text=json.dumps(storage))]
            except Exception as e:
                self.logger.error(f"Failed to get storage: {e}")
                raise

        @self.mcp.tool()
        def get_cluster_status() -> List[Content]:
            """Get overall cluster status."""
            try:
                result = self.proxmox.cluster.status.get()
                return [Content(type="text", text=json.dumps(result))]
            except Exception as e:
                self.logger.error(f"Failed to get cluster status: {e}")
                raise

        @self.mcp.tool()
        async def execute_vm_command(node: str, vmid: str, command: str) -> List[Content]:
            """Execute a command in a VM's console.

            Args:
                node: Name of the node where VM is running
                vmid: ID of the VM
                command: Command to execute
            """
            try:
                result = await self.vm_console.execute_command(node, vmid, command)
                return [Content(type="text", text=json.dumps(result))]
            except Exception as e:
                self.logger.error(f"Failed to execute VM command: {e}")
                raise

    async def run(self) -> None:
        """Start the MCP server."""
        try:
            await self.mcp.run()
            self.logger.info("Proxmox MCP server running")
        except Exception as e:
            self.logger.error(f"Server error: {e}")
            raise

def main():
    """Entry point for the MCP server."""
    import asyncio

    config_path = os.getenv("PROXMOX_MCP_CONFIG")
    server = ProxmoxMCPServer(config_path)

    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
