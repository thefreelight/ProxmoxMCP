#!/usr/bin/env python3
import json
import logging
import os
import sys
import signal
from pathlib import Path
from typing import Dict, Any, Optional, List, Annotated
from pydantic import BaseModel, Field
from urllib.parse import urljoin

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.tools import Tool
from mcp.server.fastmcp.tools.base import Tool as BaseTool
from mcp.types import CallToolResult as Response, TextContent as Content
from proxmoxer import ProxmoxAPI

# Import from the same directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.vm_console import VMConsoleManager

class NodeStatus(BaseModel):
    node: Annotated[str, Field(description="Name/ID of node to query (e.g. 'pve1', 'proxmox-node2')")]

class VMCommand(BaseModel):
    node: Annotated[str, Field(description="Host node name (e.g. 'pve1', 'proxmox-node2')")]
    vmid: Annotated[str, Field(description="VM ID number (e.g. '100', '101')")]
    command: Annotated[str, Field(description="Shell command to run (e.g. 'uname -a', 'systemctl status nginx')")]

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
        if not config_path:
            raise ValueError("PROXMOX_MCP_CONFIG environment variable must be set")

        try:
            with open(config_path) as f:
                config_data = json.load(f)
                if not config_data.get('proxmox', {}).get('host'):
                    raise ValueError("Proxmox host cannot be empty")
                return Config(**config_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load config: {e}")

    def _setup_logging(self) -> None:
        """Configure logging based on settings."""
        # Convert relative path to absolute
        log_file = self.config.logging.file
        if log_file and not os.path.isabs(log_file):
            log_file = os.path.join(os.getcwd(), log_file)
            
        # Create handlers
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, self.config.logging.level.upper()))
        
        # Console handler for errors only
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)
        
        # Configure formatters
        formatter = logging.Formatter(self.config.logging.format)
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config.logging.level.upper()))
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        self.logger = logging.getLogger("proxmox-mcp")

    def _setup_proxmox(self) -> ProxmoxAPI:
        """Initialize Proxmox API connection."""
        try:
            self.logger.info(f"Connecting to Proxmox with config: {self.config.proxmox}")
            
            # Store the working configuration for reuse
            self.proxmox_config = {
                'host': self.config.proxmox.host,
                'user': self.config.auth.user,
                'token_name': self.config.auth.token_name,
                'token_value': self.config.auth.token_value,
                'verify_ssl': self.config.proxmox.verify_ssl,
                'service': 'PVE'
            }
            
            # Create and test CustomProxmoxAPI instance
            api = ProxmoxAPI(**self.proxmox_config)
            api.version.get()  # Test connection
            return api
        except Exception as e:
            self.logger.error(f"Failed to connect to Proxmox: {e}")
            raise

    def _setup_tools(self) -> None:
        """Register MCP tools."""

        @self.mcp.tool(
            description="List all nodes in the Proxmox cluster with their status, CPU, memory, and role information.\n\n"
                      "Example:\n"
                      '{"node": "pve1", "status": "online", "cpu_usage": 0.15, "memory": {"used": "8GB", "total": "32GB"}}')
        def get_nodes() -> List[Content]:
            try:
                result = self.proxmox.nodes.get()
                nodes = [{"node": node["node"], "status": node["status"]} for node in result]
                return [Content(type="text", text=json.dumps(nodes))]
            except Exception as e:
                self.logger.error(f"Failed to get nodes: {e}")
                raise

        @self.mcp.tool(
            description="Get detailed status information for a specific Proxmox node.\n\n"
                      "Parameters:\n"
                      "node* - Name/ID of node to query (e.g. 'pve1')\n\n"
                      "Example:\n"
                      '{"cpu": {"usage": 0.15}, "memory": {"used": "8GB", "total": "32GB"}}')
        def get_node_status(node: Annotated[str, Field(description="Name/ID of node to query (e.g. 'pve1')")]) -> List[Content]:
            try:
                result = self.proxmox.nodes(node).status.get()
                return [Content(type="text", text=json.dumps(result))]
            except Exception as e:
                self.logger.error(f"Failed to get node status: {e}")
                raise

        @self.mcp.tool(
            description="List all virtual machines across the cluster with their status and resource usage.\n\n"
                      "Example:\n"
                      '{"vmid": "100", "name": "ubuntu", "status": "running", "cpu": 2, "memory": 4096}')
        def get_vms() -> List[Content]:
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

        @self.mcp.tool(
            description="List all LXC containers across the cluster with their status and configuration.\n\n"
                      "Example:\n"
                      '{"vmid": "200", "name": "nginx", "status": "running", "template": "ubuntu-20.04"}')
        def get_containers() -> List[Content]:
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

        @self.mcp.tool(
            description="List storage pools across the cluster with their usage and configuration.\n\n"
                      "Example:\n"
                      '{"storage": "local-lvm", "type": "lvm", "used": "500GB", "total": "1TB"}')
        def get_storage() -> List[Content]:
            try:
                result = self.proxmox.storage.get()
                storage = [{"storage": storage["storage"], "type": storage["type"]} for storage in result]
                return [Content(type="text", text=json.dumps(storage))]
            except Exception as e:
                self.logger.error(f"Failed to get storage: {e}")
                raise

        @self.mcp.tool(
            description="Get overall Proxmox cluster health and configuration status.\n\n"
                      "Example:\n"
                      '{"name": "proxmox", "quorum": "ok", "nodes": 3, "ha_status": "active"}')
        def get_cluster_status() -> List[Content]:
            try:
                result = self.proxmox.cluster.status.get()
                return [Content(type="text", text=json.dumps(result))]
            except Exception as e:
                self.logger.error(f"Failed to get cluster status: {e}")
                raise

        @self.mcp.tool(
            description="Execute commands in a VM via QEMU guest agent.\n\n"
                      "Parameters:\n"
                      "node* - Host node name (e.g. 'pve1')\n"
                      "vmid* - VM ID number (e.g. '100')\n"
                      "command* - Shell command to run (e.g. 'uname -a')\n\n"
                      "Example:\n"
                      '{"success": true, "output": "Linux vm1 5.4.0", "exit_code": 0}')
        async def execute_vm_command(
            node: Annotated[str, Field(description="Host node name (e.g. 'pve1')")],
            vmid: Annotated[str, Field(description="VM ID number (e.g. '100')")],
            command: Annotated[str, Field(description="Shell command to run (e.g. 'uname -a')")]
        ) -> List[Content]:
            try:
                result = await self.vm_console.execute_command(node, vmid, command)
                return [Content(type="text", text=json.dumps(result))]
            except Exception as e:
                self.logger.error(f"Failed to execute VM command: {e}")
                raise

    def start(self) -> None:
        """Start the MCP server."""
        import anyio

        def signal_handler(signum, frame):
            self.logger.info("Received signal to shutdown...")
            sys.exit(0)

        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            self.logger.info("Starting MCP server...")
            anyio.run(self.mcp.run_stdio_async)
        except Exception as e:
            self.logger.error(f"Server error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    config_path = os.getenv("PROXMOX_MCP_CONFIG")
    if not config_path:
        print("PROXMOX_MCP_CONFIG environment variable must be set")
        sys.exit(1)
    
    try:
        server = ProxmoxMCPServer(config_path)
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
