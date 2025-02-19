"""
VM-related tools for Proxmox MCP.
"""
from typing import List
from mcp.types import TextContent as Content
from .base import ProxmoxTool
from .definitions import GET_VMS_DESC, EXECUTE_VM_COMMAND_DESC
from .console.manager import VMConsoleManager

class VMTools(ProxmoxTool):
    """Tools for managing Proxmox VMs."""

    def __init__(self, proxmox_api):
        """Initialize VM tools.

        Args:
            proxmox_api: Initialized ProxmoxAPI instance
        """
        super().__init__(proxmox_api)
        self.console_manager = VMConsoleManager(proxmox_api)

    def get_vms(self) -> List[Content]:
        """List all virtual machines across the cluster.

        Returns:
            List of Content objects containing VM information

        Raises:
            RuntimeError: If the operation fails
        """
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
            return self._format_response(result)
        except Exception as e:
            self._handle_error("get VMs", e)

    async def execute_command(self, node: str, vmid: str, command: str) -> List[Content]:
        """Execute a command in a VM via QEMU guest agent.

        Args:
            node: Host node name
            vmid: VM ID number
            command: Shell command to run

        Returns:
            List of Content objects containing command output

        Raises:
            ValueError: If VM is not found or not running
            RuntimeError: If command execution fails
        """
        try:
            result = await self.console_manager.execute_command(node, vmid, command)
            return self._format_response(result)
        except Exception as e:
            self._handle_error(f"execute command on VM {vmid}", e)
