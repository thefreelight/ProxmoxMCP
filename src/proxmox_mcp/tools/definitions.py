"""
Tool descriptions for Proxmox MCP tools.
"""

# Node tool descriptions
GET_NODES_DESC = """List all nodes in the Proxmox cluster with their status, CPU, memory, and role information.

Example:
{"node": "pve1", "status": "online", "cpu_usage": 0.15, "memory": {"used": "8GB", "total": "32GB"}}"""

GET_NODE_STATUS_DESC = """Get detailed status information for a specific Proxmox node.

Parameters:
node* - Name/ID of node to query (e.g. 'pve1')

Example:
{"cpu": {"usage": 0.15}, "memory": {"used": "8GB", "total": "32GB"}}"""

# VM tool descriptions
GET_VMS_DESC = """List all virtual machines across the cluster with their status and resource usage.

Example:
{"vmid": "100", "name": "ubuntu", "status": "running", "cpu": 2, "memory": 4096}"""

EXECUTE_VM_COMMAND_DESC = """Execute commands in a VM via QEMU guest agent.

Parameters:
node* - Host node name (e.g. 'pve1')
vmid* - VM ID number (e.g. '100')
command* - Shell command to run (e.g. 'uname -a')

Example:
{"success": true, "output": "Linux vm1 5.4.0", "exit_code": 0}"""

# Container tool descriptions
GET_CONTAINERS_DESC = """List all LXC containers across the cluster with their status and configuration.

Example:
{"vmid": "200", "name": "nginx", "status": "running", "template": "ubuntu-20.04"}"""

# Storage tool descriptions
GET_STORAGE_DESC = """List storage pools across the cluster with their usage and configuration.

Example:
{"storage": "local-lvm", "type": "lvm", "used": "500GB", "total": "1TB"}"""

# Cluster tool descriptions
GET_CLUSTER_STATUS_DESC = """Get overall Proxmox cluster health and configuration status.

Example:
{"name": "proxmox", "quorum": "ok", "nodes": 3, "ha_status": "active"}"""

# Network tool descriptions
CONFIGURE_VM_STATIC_IP_DESC = """Configure static IP address inside a VM via guest agent.

Parameters:
node* - Host node name (e.g. 'pve1')
vmid* - VM ID number (e.g. '100')
ip_address* - IP address with CIDR (e.g. '192.168.0.106/24')
gateway - Gateway IP address (default: '192.168.0.1')
dns_servers - List of DNS servers (default: ['8.8.8.8', '8.8.4.4'])

Example:
Configures VM internal network to use static IP by updating netplan configuration."""

CONFIGURE_VM_DHCP_DESC = """Configure VM to use DHCP for network configuration.

Parameters:
node* - Host node name (e.g. 'pve1')
vmid* - VM ID number (e.g. '100')

Example:
Configures VM internal network to use DHCP by updating netplan configuration."""

GET_VM_NETWORK_INFO_DESC = """Get detailed network information from a VM via guest agent.

Parameters:
node* - Host node name (e.g. 'pve1')
vmid* - VM ID number (e.g. '100')

Example:
Returns network interfaces, routing table, DNS configuration, and netplan settings."""

# Cloud-Init tool descriptions
REGENERATE_CLOUDINIT_DESC = """Regenerate Cloud-Init configuration drive for a VM.

Parameters:
node* - Host node name (e.g. 'pve1')
vmid* - VM ID number (e.g. '100')

Example:
Forces Proxmox to recreate the Cloud-Init ISO with current configuration."""

UPDATE_VM_NETWORK_CLOUDINIT_DESC = """Update VM network configuration and regenerate Cloud-Init drive.

Parameters:
node* - Host node name (e.g. 'pve1')
vmid* - VM ID number (e.g. '100')
ip_address* - IP address with CIDR (e.g. '192.168.0.106/24')
gateway - Gateway IP address (default: '192.168.0.1')

Example:
Complete workflow to update network config and regenerate Cloud-Init drive."""

COMPLETE_NETWORK_RECONFIG_DESC = """Complete network reconfiguration workflow with restart.

Parameters:
node* - Host node name (e.g. 'pve1')
vmid* - VM ID number (e.g. '100')
ip_address* - IP address with CIDR (e.g. '192.168.0.106/24')
vm_name - Optional VM name for display
gateway - Gateway IP address (default: '192.168.0.1')

Example:
Updates config, regenerates Cloud-Init, and restarts VM automatically."""
