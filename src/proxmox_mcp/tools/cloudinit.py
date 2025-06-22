"""
Cloud-Init configuration tools for Proxmox MCP.

This module provides Cloud-Init management tools for VMs:
- Regenerating Cloud-Init configuration drives
- Updating VM network settings via Cloud-Init
- Forcing Cloud-Init configuration updates
"""

import logging
from typing import List
from mcp.types import TextContent as Content
from .base import ProxmoxTool

class CloudInitTools(ProxmoxTool):
    """Cloud-Init configuration tools for Proxmox VMs.
    
    Provides functionality for:
    - Regenerating Cloud-Init configuration drives
    - Updating VM network settings
    - Forcing configuration updates without Guest Agent
    """

    def __init__(self, proxmox_api):
        """Initialize Cloud-Init tools.

        Args:
            proxmox_api: Initialized ProxmoxAPI instance
        """
        super().__init__(proxmox_api)
        self.logger = logging.getLogger("proxmox-mcp.cloudinit")

    def regenerate_cloudinit_drive(self, node: str, vmid: str) -> List[Content]:
        """Regenerate Cloud-Init configuration drive for a VM.

        This forces Proxmox to recreate the Cloud-Init ISO with current configuration.
        Useful when network or other Cloud-Init settings have been changed but not applied.

        Args:
            node: Host node name (e.g., 'pve1')
            vmid: VM ID number (e.g., '100')

        Returns:
            List of Content objects containing operation results
        """
        try:
            self.logger.info(f"Regenerating Cloud-Init drive for VM {vmid} on node {node}")
            
            # Use the cloudinit endpoint to regenerate the drive
            result = self.proxmox.nodes(node).qemu(vmid).cloudinit.put()
            
            return [Content(
                type="text",
                text=f"✅ Successfully regenerated Cloud-Init drive for VM {vmid}\n"
                     f"🔄 The VM needs to be restarted for changes to take effect\n"
                     f"📋 Result: {result}"
            )]

        except Exception as e:
            self.logger.error(f"Failed to regenerate Cloud-Init drive for VM {vmid}: {str(e)}")
            return [Content(
                type="text",
                text=f"❌ Failed to regenerate Cloud-Init drive for VM {vmid}: {str(e)}"
            )]

    def update_vm_network_and_regenerate(self, node: str, vmid: str, ip_address: str, 
                                       gateway: str = "192.168.0.1") -> List[Content]:
        """Update VM network configuration and regenerate Cloud-Init drive.

        This is a complete workflow that:
        1. Updates the VM's network configuration
        2. Regenerates the Cloud-Init drive
        3. Provides restart instructions

        Args:
            node: Host node name (e.g., 'pve1')
            vmid: VM ID number (e.g., '100')
            ip_address: IP address with CIDR (e.g., '192.168.0.106/24')
            gateway: Gateway IP address (default: '192.168.0.1')

        Returns:
            List of Content objects containing operation results
        """
        try:
            self.logger.info(f"Updating network config and regenerating Cloud-Init for VM {vmid}")
            
            # Step 1: Update network configuration
            ipconfig = f"ip={ip_address},gw={gateway}"
            config_result = self.proxmox.nodes(node).qemu(vmid).config.put(ipconfig0=ipconfig)
            
            # Step 2: Regenerate Cloud-Init drive
            cloudinit_result = self.proxmox.nodes(node).qemu(vmid).cloudinit.put()
            
            return [Content(
                type="text",
                text=f"✅ Successfully updated network configuration for VM {vmid}\n"
                     f"🌐 New IP configuration: {ip_address}\n"
                     f"🚪 Gateway: {gateway}\n"
                     f"🔄 Cloud-Init drive regenerated\n"
                     f"⚠️  IMPORTANT: Restart the VM to apply changes\n"
                     f"📋 Config result: {config_result}\n"
                     f"📋 Cloud-Init result: {cloudinit_result}"
            )]

        except Exception as e:
            self.logger.error(f"Failed to update network config for VM {vmid}: {str(e)}")
            return [Content(
                type="text",
                text=f"❌ Failed to update network configuration for VM {vmid}: {str(e)}"
            )]

    def get_cloudinit_config(self, node: str, vmid: str, config_type: str = "user") -> List[Content]:
        """Get Cloud-Init configuration for a VM.

        Args:
            node: Host node name (e.g., 'pve1')
            vmid: VM ID number (e.g., '100')
            config_type: Type of config to retrieve ('user', 'network', 'meta')

        Returns:
            List of Content objects containing configuration data
        """
        try:
            self.logger.info(f"Getting Cloud-Init {config_type} config for VM {vmid}")
            
            # Get the Cloud-Init configuration
            if config_type == "user":
                result = self.proxmox.nodes(node).qemu(vmid).cloudinit.user.get()
            elif config_type == "network":
                result = self.proxmox.nodes(node).qemu(vmid).cloudinit.network.get()
            elif config_type == "meta":
                result = self.proxmox.nodes(node).qemu(vmid).cloudinit.meta.get()
            else:
                raise ValueError(f"Invalid config type: {config_type}")
            
            return [Content(
                type="text",
                text=f"📋 Cloud-Init {config_type} configuration for VM {vmid}:\n\n{result}"
            )]

        except Exception as e:
            self.logger.error(f"Failed to get Cloud-Init config for VM {vmid}: {str(e)}")
            return [Content(
                type="text",
                text=f"❌ Failed to get Cloud-Init {config_type} configuration for VM {vmid}: {str(e)}"
            )]

    def complete_network_reconfiguration(self, node: str, vmid: str, ip_address: str, 
                                       vm_name: str = None, gateway: str = "192.168.0.1") -> List[Content]:
        """Complete network reconfiguration workflow.

        This performs the complete workflow:
        1. Updates VM network configuration
        2. Regenerates Cloud-Init drive
        3. Restarts the VM
        4. Waits for VM to come back online

        Args:
            node: Host node name (e.g., 'pve1')
            vmid: VM ID number (e.g., '100')
            ip_address: IP address with CIDR (e.g., '192.168.0.106/24')
            vm_name: Optional VM name for display
            gateway: Gateway IP address (default: '192.168.0.1')

        Returns:
            List of Content objects containing operation results
        """
        try:
            vm_display = vm_name or f"VM {vmid}"
            self.logger.info(f"Starting complete network reconfiguration for {vm_display}")
            
            results = []
            
            # Step 1: Update network configuration
            ipconfig = f"ip={ip_address},gw={gateway}"
            config_result = self.proxmox.nodes(node).qemu(vmid).config.put(ipconfig0=ipconfig)
            results.append(f"✅ Network configuration updated: {ip_address}")
            
            # Step 2: Regenerate Cloud-Init drive
            cloudinit_result = self.proxmox.nodes(node).qemu(vmid).cloudinit.put()
            results.append("✅ Cloud-Init drive regenerated")
            
            # Step 3: Restart VM
            restart_result = self.proxmox.nodes(node).qemu(vmid).status.reboot.post()
            results.append("🔄 VM restart initiated")
            
            return [Content(
                type="text",
                text=f"🎉 Complete network reconfiguration for {vm_display}:\n\n" + 
                     "\n".join(results) + 
                     f"\n\n🌐 New IP: {ip_address}\n" +
                     f"🚪 Gateway: {gateway}\n" +
                     "⏳ Please wait for VM to restart and apply new configuration"
            )]

        except Exception as e:
            self.logger.error(f"Failed complete network reconfiguration for VM {vmid}: {str(e)}")
            return [Content(
                type="text",
                text=f"❌ Failed complete network reconfiguration for VM {vmid}: {str(e)}"
            )]
