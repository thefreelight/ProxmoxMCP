"""
Module for managing VM console operations.
"""

import logging
from typing import Dict, Any

class VMConsoleManager:
    """Manager class for VM console operations."""

    def __init__(self, proxmox_api):
        """Initialize the VM console manager.

        Args:
            proxmox_api: Initialized ProxmoxAPI instance
        """
        self.proxmox = proxmox_api
        self.logger = logging.getLogger("proxmox-mcp.vm-console")

    async def execute_command(self, node: str, vmid: str, command: str) -> Dict[str, Any]:
        """Execute a command in a VM's console.

        Args:
            node: Name of the node where VM is running
            vmid: ID of the VM
            command: Command to execute

        Returns:
            Dictionary containing command output and status

        Raises:
            ValueError: If VM is not found or not running
            RuntimeError: If command execution fails
        """
        try:
            # Verify VM exists and is running
            vm_status = self.proxmox.nodes(node).qemu(vmid).status.current.get()
            if vm_status["status"] != "running":
                self.logger.error(f"Failed to execute command on VM {vmid}: VM is not running")
                raise ValueError(f"VM {vmid} on node {node} is not running")

            # Get VM's console
            console = self.proxmox.nodes(node).qemu(vmid).agent.exec.post(
                command=command
            )

            self.logger.debug(f"Executed command '{command}' on VM {vmid} (node: {node})")

            return {
                "success": True,
                "output": console.get("out", ""),
                "error": console.get("err", ""),
                "exit_code": console.get("exitcode", 0)
            }

        except ValueError:
            # Re-raise ValueError for VM not running
            raise
        except Exception as e:
            self.logger.error(f"Failed to execute command on VM {vmid}: {str(e)}")
            if "not found" in str(e).lower():
                raise ValueError(f"VM {vmid} not found on node {node}")
            raise RuntimeError(f"Failed to execute command: {str(e)}")
