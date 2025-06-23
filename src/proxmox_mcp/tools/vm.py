"""
VM-related tools for Proxmox MCP.

This module provides tools for managing and interacting with Proxmox VMs:
- Listing all VMs across the cluster with their status
- Retrieving detailed VM information including:
  * Resource allocation (CPU, memory)
  * Runtime status
  * Node placement
- Executing commands within VMs via QEMU guest agent
- Handling VM console operations

The tools implement fallback mechanisms for scenarios where
detailed VM information might be temporarily unavailable.
"""
from typing import List
from mcp.types import TextContent as Content
from .base import ProxmoxTool
from .definitions import GET_VMS_DESC, EXECUTE_VM_COMMAND_DESC
from .console.manager import VMConsoleManager

class VMTools(ProxmoxTool):
    """Tools for managing Proxmox VMs.
    
    Provides functionality for:
    - Retrieving cluster-wide VM information
    - Getting detailed VM status and configuration
    - Executing commands within VMs
    - Managing VM console operations
    
    Implements fallback mechanisms for scenarios where detailed
    VM information might be temporarily unavailable. Integrates
    with QEMU guest agent for VM command execution.
    """

    def __init__(self, proxmox_api):
        """Initialize VM tools.

        Args:
            proxmox_api: Initialized ProxmoxAPI instance
        """
        super().__init__(proxmox_api)
        self.console_manager = VMConsoleManager(proxmox_api)

    def get_vms(self) -> List[Content]:
        """List all virtual machines across the cluster with detailed status.

        Retrieves comprehensive information for each VM including:
        - Basic identification (ID, name)
        - Runtime status (running, stopped)
        - Resource allocation and usage:
          * CPU cores
          * Memory allocation and usage
        - Node placement
        
        Implements a fallback mechanism that returns basic information
        if detailed configuration retrieval fails for any VM.

        Returns:
            List of Content objects containing formatted VM information:
            {
                "vmid": "100",
                "name": "vm-name",
                "status": "running/stopped",
                "node": "node-name",
                "cpus": core_count,
                "memory": {
                    "used": bytes,
                    "total": bytes
                }
            }

        Raises:
            RuntimeError: If the cluster-wide VM query fails
        """
        try:
            import requests

            # Get connection details from proxmox API object
            host = getattr(self.proxmox, '_host', 'home.chfastpay.com')
            port = getattr(self.proxmox, '_port', 8006)
            user = getattr(self.proxmox, '_user', 'jordan@pve')
            token_name = getattr(self.proxmox, '_token_name', 'mcp-api')
            token_value = getattr(self.proxmox, '_token_value', 'c1ccbc3d-45de-475d-9ac0-5bb9ea1a75b7')

            base_url = f"https://{host}:{port}"
            headers = {
                "Authorization": f"PVEAPIToken={user}!{token_name}={token_value}",
                "Content-Type": "application/json"
            }

            result = []

            # Get nodes list first
            nodes_url = f"{base_url}/api2/json/nodes"
            nodes_response = requests.get(nodes_url, headers=headers, verify=False, timeout=30)
            nodes_response.raise_for_status()
            nodes_result = nodes_response.json()

            if 'data' not in nodes_result:
                raise RuntimeError("No data in nodes response")

            for node in nodes_result['data']:
                node_name = node["node"]

                # Get VMs for this node
                vms_url = f"{base_url}/api2/json/nodes/{node_name}/qemu"
                vms_response = requests.get(vms_url, headers=headers, verify=False, timeout=30)
                vms_response.raise_for_status()
                vms_result = vms_response.json()

                if 'data' not in vms_result:
                    continue

                vms = vms_result['data']
                for vm in vms:
                    vmid = vm["vmid"]
                    # Get VM config for CPU cores
                    try:
                        config_url = f"{base_url}/api2/json/nodes/{node_name}/qemu/{vmid}/config"
                        config_response = requests.get(config_url, headers=headers, verify=False, timeout=30)
                        config_response.raise_for_status()
                        config_result = config_response.json()

                        if 'data' in config_result:
                            config = config_result['data']
                            result.append({
                                "vmid": vmid,
                                "name": vm["name"],
                                "status": vm["status"],
                                "node": node_name,
                                "cpus": config.get("cores", "N/A"),
                                "memory": {
                                    "used": vm.get("mem", 0),
                                    "total": vm.get("maxmem", 0)
                                }
                            })
                        else:
                            raise Exception("No config data")
                    except Exception:
                        # Fallback if can't get config
                        result.append({
                            "vmid": vmid,
                            "name": vm["name"],
                            "status": vm["status"],
                            "node": node_name,
                            "cpus": "N/A",
                            "memory": {
                                "used": vm.get("mem", 0),
                                "total": vm.get("maxmem", 0)
                            }
                        })
            return self._format_response(result, "vms")
        except Exception as e:
            self._handle_error("get VMs", e)

    async def execute_command(self, node: str, vmid: str, command: str) -> List[Content]:
        """Execute a command in a VM via QEMU guest agent.

        Uses the QEMU guest agent to execute commands within a running VM.
        Requires:
        - VM must be running
        - QEMU guest agent must be installed and running in the VM
        - Command execution permissions must be enabled

        Args:
            node: Host node name (e.g., 'pve1', 'proxmox-node2')
            vmid: VM ID number (e.g., '100', '101')
            command: Shell command to run (e.g., 'uname -a', 'systemctl status nginx')

        Returns:
            List of Content objects containing formatted command output:
            {
                "success": true/false,
                "output": "command output",
                "error": "error message if any"
            }

        Raises:
            ValueError: If VM is not found, not running, or guest agent is not available
            RuntimeError: If command execution fails due to permissions or other issues
        """
        try:
            self.logger.info(f"VM Tools: execute_command called with node={node}, vmid={vmid}, command={command}")
            self.logger.info(f"VM Tools: console_manager type: {type(self.console_manager)}")

            result = await self.console_manager.execute_command(node, vmid, command)

            self.logger.info(f"VM Tools: console_manager.execute_command completed successfully")
            self.logger.info(f"VM Tools: result type: {type(result)}, content: {result}")

            # Use the command output formatter from ProxmoxFormatters
            from ..formatting import ProxmoxFormatters
            formatted = ProxmoxFormatters.format_command_output(
                success=result["success"],
                command=command,
                output=result["output"],
                error=result.get("error")
            )

            self.logger.info(f"VM Tools: formatted result successfully")
            return [Content(type="text", text=formatted)]
        except Exception as e:
            self.logger.error(f"VM Tools: execute_command failed: {str(e)}")
            import traceback
            self.logger.error(f"VM Tools: Full traceback: {traceback.format_exc()}")
            self._handle_error(f"execute command on VM {vmid}", e)
