"""
Configuration models for the Proxmox MCP server.
"""
from typing import Optional, Annotated
from pydantic import BaseModel, Field

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
