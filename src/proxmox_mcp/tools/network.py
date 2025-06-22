"""
Network configuration tools for Proxmox MCP.

This module provides advanced network configuration tools for VMs:
- Configuring VM internal network settings via guest agent
- Updating netplan configurations
- Applying network changes
- Verifying network connectivity
"""

import logging
import asyncio
from typing import List, Dict, Any
from mcp.types import TextContent as Content
from .base import ProxmoxTool

class NetworkTools(ProxmoxTool):
    """Advanced network configuration tools for Proxmox VMs.
    
    Provides functionality for:
    - Configuring VM internal network settings
    - Updating netplan configurations
    - Applying network changes
    - Verifying network connectivity
    """

    def __init__(self, proxmox_api):
        """Initialize network tools.

        Args:
            proxmox_api: Initialized ProxmoxAPI instance
        """
        super().__init__(proxmox_api)
        self.logger = logging.getLogger("proxmox-mcp.network")

    async def configure_vm_static_ip(self, node: str, vmid: str, ip_address: str, 
                                   gateway: str = "192.168.0.1", 
                                   dns_servers: List[str] = None) -> List[Content]:
        """Configure static IP address inside a VM via guest agent.

        This function directly modifies the VM's internal network configuration
        by updating the netplan configuration file and applying the changes.

        Args:
            node: Host node name (e.g., 'pve1')
            vmid: VM ID number (e.g., '100')
            ip_address: IP address with CIDR (e.g., '192.168.0.106/24')
            gateway: Gateway IP address (default: '192.168.0.1')
            dns_servers: List of DNS servers (default: ['8.8.8.8', '8.8.4.4'])

        Returns:
            List of Content objects containing configuration results

        Raises:
            ValueError: If VM is not found or not running
            RuntimeError: If configuration fails
        """
        if dns_servers is None:
            dns_servers = ['8.8.8.8', '8.8.4.4']

        try:
            self.logger.info(f"Configuring static IP {ip_address} for VM {vmid} on node {node}")

            # Verify VM is running
            vm_status = self.proxmox.nodes(node).qemu(vmid).status.current.get()
            if vm_status["status"] != "running":
                raise ValueError(f"VM {vmid} on node {node} is not running")

            # Create netplan configuration
            netplan_config = f"""network:
  ethernets:
    ens18:
      dhcp4: false
      addresses:
        - {ip_address}
      gateway4: {gateway}
      nameservers:
        addresses: [{', '.join([f'"{dns}"' for dns in dns_servers])}]
  version: 2
"""

            # Step 1: Backup existing netplan configuration
            backup_cmd = "sudo cp /etc/netplan/00-installer-config.yaml /etc/netplan/00-installer-config.yaml.backup"
            await self._execute_vm_command(node, vmid, backup_cmd)

            # Step 2: Write new netplan configuration
            write_cmd = f"echo '{netplan_config}' | sudo tee /etc/netplan/00-installer-config.yaml"
            await self._execute_vm_command(node, vmid, write_cmd)

            # Step 3: Apply netplan configuration
            apply_cmd = "sudo netplan apply"
            await self._execute_vm_command(node, vmid, apply_cmd)

            # Step 4: Verify configuration
            verify_cmd = "ip addr show ens18"
            result = await self._execute_vm_command(node, vmid, verify_cmd)

            self.logger.info(f"Successfully configured static IP {ip_address} for VM {vmid}")

            return [Content(
                type="text",
                text=f"✅ Successfully configured static IP {ip_address} for VM {vmid}\n"
                     f"Gateway: {gateway}\n"
                     f"DNS: {', '.join(dns_servers)}\n"
                     f"Network interface status:\n{result.get('output', 'N/A')}"
            )]

        except Exception as e:
            self.logger.error(f"Failed to configure static IP for VM {vmid}: {str(e)}")
            return [Content(
                type="text",
                text=f"❌ Failed to configure static IP for VM {vmid}: {str(e)}"
            )]

    async def configure_vm_dhcp(self, node: str, vmid: str) -> List[Content]:
        """Configure VM to use DHCP for network configuration.

        Args:
            node: Host node name
            vmid: VM ID number

        Returns:
            List of Content objects containing configuration results
        """
        try:
            self.logger.info(f"Configuring DHCP for VM {vmid} on node {node}")

            # Create DHCP netplan configuration
            netplan_config = """network:
  ethernets:
    ens18:
      dhcp4: true
  version: 2
"""

            # Step 1: Backup existing configuration
            backup_cmd = "sudo cp /etc/netplan/00-installer-config.yaml /etc/netplan/00-installer-config.yaml.backup"
            await self._execute_vm_command(node, vmid, backup_cmd)

            # Step 2: Write DHCP configuration
            write_cmd = f"echo '{netplan_config}' | sudo tee /etc/netplan/00-installer-config.yaml"
            await self._execute_vm_command(node, vmid, write_cmd)

            # Step 3: Apply configuration
            apply_cmd = "sudo netplan apply"
            await self._execute_vm_command(node, vmid, apply_cmd)

            # Step 4: Wait for DHCP to assign IP
            await asyncio.sleep(5)

            # Step 5: Verify configuration
            verify_cmd = "ip addr show ens18"
            result = await self._execute_vm_command(node, vmid, verify_cmd)

            self.logger.info(f"Successfully configured DHCP for VM {vmid}")

            return [Content(
                type="text",
                text=f"✅ Successfully configured DHCP for VM {vmid}\n"
                     f"Network interface status:\n{result.get('output', 'N/A')}"
            )]

        except Exception as e:
            self.logger.error(f"Failed to configure DHCP for VM {vmid}: {str(e)}")
            return [Content(
                type="text",
                text=f"❌ Failed to configure DHCP for VM {vmid}: {str(e)}"
            )]

    async def get_vm_network_info(self, node: str, vmid: str) -> List[Content]:
        """Get detailed network information from a VM.

        Args:
            node: Host node name
            vmid: VM ID number

        Returns:
            List of Content objects containing network information
        """
        try:
            # Get network interface information
            ip_cmd = "ip addr show"
            ip_result = await self._execute_vm_command(node, vmid, ip_cmd)

            # Get routing information
            route_cmd = "ip route show"
            route_result = await self._execute_vm_command(node, vmid, route_cmd)

            # Get DNS configuration
            dns_cmd = "cat /etc/resolv.conf"
            dns_result = await self._execute_vm_command(node, vmid, dns_cmd)

            # Get netplan configuration
            netplan_cmd = "cat /etc/netplan/00-installer-config.yaml"
            netplan_result = await self._execute_vm_command(node, vmid, netplan_cmd)

            return [Content(
                type="text",
                text=f"🔍 Network Information for VM {vmid}\n\n"
                     f"📡 Network Interfaces:\n{ip_result.get('output', 'N/A')}\n\n"
                     f"🛣️ Routing Table:\n{route_result.get('output', 'N/A')}\n\n"
                     f"🌐 DNS Configuration:\n{dns_result.get('output', 'N/A')}\n\n"
                     f"⚙️ Netplan Configuration:\n{netplan_result.get('output', 'N/A')}"
            )]

        except Exception as e:
            self.logger.error(f"Failed to get network info for VM {vmid}: {str(e)}")
            return [Content(
                type="text",
                text=f"❌ Failed to get network info for VM {vmid}: {str(e)}"
            )]

    async def _execute_vm_command(self, node: str, vmid: str, command: str) -> Dict[str, Any]:
        """Execute a command in a VM via guest agent.

        Args:
            node: Host node name
            vmid: VM ID number
            command: Command to execute

        Returns:
            Dictionary containing command execution results

        Raises:
            RuntimeError: If command execution fails
        """
        try:
            # Get the API endpoint
            endpoint = self.proxmox.nodes(node).qemu(vmid).agent

            # Execute the command
            exec_result = endpoint("exec").post(command=command)
            if 'pid' not in exec_result:
                raise RuntimeError("No PID returned from command execution")

            pid = exec_result['pid']
            
            # Wait for command completion
            await asyncio.sleep(2)

            # Get command output
            status_result = endpoint("exec-status").get(pid=pid)
            
            return {
                "success": True,
                "output": status_result.get("out-data", ""),
                "error": status_result.get("err-data", ""),
                "exit_code": status_result.get("exitcode", 0)
            }

        except Exception as e:
            self.logger.error(f"Failed to execute command '{command}' on VM {vmid}: {str(e)}")
            raise RuntimeError(f"Failed to execute command: {str(e)}")
