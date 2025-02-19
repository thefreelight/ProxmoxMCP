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
from urllib.parse import urljoin

class CustomProxmoxAPI(ProxmoxAPI):
    def __init__(self, host, **kwargs):
        self._host = host  # Store the host
        super().__init__(host, **kwargs)
    
    def get(self, *args, **kwargs):
        try:
            # Always ensure base_url is set correctly
            self._store['base_url'] = f'https://{self._host}:{self._store.get("port", "8006")}/api2/json'
            print(f"Using base_url: {self._store['base_url']}")
            
            # Handle both dotted and string notation
            if args and isinstance(args[0], str):
                path = args[0]
                print(f"Making request to path: {path}")
                full_url = f"{self._store['base_url']}/{path}"
                print(f"Full URL: {full_url}")
                return self._backend.get(full_url)
            
            print("Using dotted notation")
            return super().get(*args, **kwargs)
        except Exception as e:
            print(f"Error in CustomProxmoxAPI.get: {e}")
            raise

# Import from the same directory
import sys
import os.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.vm_console import VMConsoleManager

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
        print(f"Loading config from path: {config_path}")
        if not config_path:
            raise ValueError("PROXMOX_MCP_CONFIG environment variable must be set")

        try:
            with open(config_path) as f:
                config_data = json.load(f)
                print(f"Raw config data: {config_data}")
                
                # Ensure host is not empty
                if not config_data.get('proxmox', {}).get('host'):
                    raise ValueError("Proxmox host cannot be empty")
                    
                print(f"Using host: {config_data['proxmox']['host']}")
                return Config(**config_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load config: {e}")

    def _setup_logging(self) -> None:
        """Configure logging based on settings."""
        import os
        
        # Convert relative path to absolute
        log_file = self.config.logging.file
        if log_file and not os.path.isabs(log_file):
            log_file = os.path.join(os.getcwd(), log_file)
            
        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, self.config.logging.level.upper()),
            format=self.config.logging.format,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()  # Also log to console
            ]
        )
        
        self.logger = logging.getLogger("proxmox-mcp")
        self.logger.info(f"Logging initialized. File: {log_file}, Level: {self.config.logging.level}")

    def _setup_proxmox(self) -> ProxmoxAPI:
        """Initialize Proxmox API connection."""
        try:
            self.logger.info(f"Connecting to Proxmox with config: {self.config.proxmox}")
            print(f"Initializing ProxmoxAPI with host={self.config.proxmox.host}, port={self.config.proxmox.port}")
            
            print(f"Creating ProxmoxAPI with host={self.config.proxmox.host}")
            
            # Store the working configuration for reuse
            self.proxmox_config = {
                'host': self.config.proxmox.host,
                'user': self.config.auth.user,
                'token_name': self.config.auth.token_name,
                'token_value': self.config.auth.token_value,
                'verify_ssl': self.config.proxmox.verify_ssl,
                'service': 'PVE'
            }
            
            # Create CustomProxmoxAPI instance with stored config
            api = CustomProxmoxAPI(**self.proxmox_config)
            print("ProxmoxAPI initialized successfully")
            # Test the connection by making a simple request
            print("Testing API connection...")
            test_result = api.version.get()
            print(f"Connection test result: {test_result}")
            
            # Test nodes endpoint specifically
            print("Testing nodes endpoint...")
            nodes_result = api.nodes.get()
            print(f"Nodes test result: {nodes_result}")
            
            return api
        except Exception as e:
            self.logger.error(f"Failed to connect to Proxmox: {e}")
            raise

    def _setup_tools(self) -> None:
        """Register MCP tools."""

        @self.mcp.tool()
        def get_nodes() -> List[Content]:
            """List all nodes in the Proxmox cluster."""
            try:
                print(f"Using ProxmoxAPI instance with config: {self.proxmox_config}")
                print("Getting nodes using dotted notation...")
                result = self.proxmox.nodes.get()
                print(f"Raw nodes result: {result}")
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

    def start(self) -> None:
        """Start the MCP server."""
        import anyio
        import signal
        import sys

        def signal_handler(signum, frame):
            print("Received signal to shutdown...")
            sys.exit(0)

        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            print("Starting MCP server...")
            anyio.run(self.mcp.run_stdio_async)
        except Exception as e:
            print(f"Server error: {e}")
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
