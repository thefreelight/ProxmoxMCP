"""
Node-related tools for Proxmox MCP.

This module provides tools for managing and monitoring Proxmox nodes:
- Listing all nodes in the cluster with their status
- Getting detailed node information including:
  * CPU usage and configuration
  * Memory utilization
  * Uptime statistics
  * Health status

The tools handle both basic and detailed node information retrieval,
with fallback mechanisms for partial data availability.
"""
from typing import List
from mcp.types import TextContent as Content
from .base import ProxmoxTool
from .definitions import GET_NODES_DESC, GET_NODE_STATUS_DESC

class NodeTools(ProxmoxTool):
    """Tools for managing Proxmox nodes.
    
    Provides functionality for:
    - Retrieving cluster-wide node information
    - Getting detailed status for specific nodes
    - Monitoring node health and resources
    - Handling node-specific API operations
    
    Implements fallback mechanisms for scenarios where detailed
    node information might be temporarily unavailable.
    """

    def get_nodes(self) -> List[Content]:
        """List all nodes in the Proxmox cluster with detailed status.

        Retrieves comprehensive information for each node including:
        - Basic status (online/offline)
        - Uptime statistics
        - CPU configuration and count
        - Memory usage and capacity
        
        Implements a fallback mechanism that returns basic information
        if detailed status retrieval fails for any node.

        Returns:
            List of Content objects containing formatted node information:
            {
                "node": "node_name",
                "status": "online/offline",
                "uptime": seconds,
                "maxcpu": cpu_count,
                "memory": {
                    "used": bytes,
                    "total": bytes
                }
            }

        Raises:
            RuntimeError: If the cluster-wide node query fails
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

            # Get nodes list
            nodes_url = f"{base_url}/api2/json/nodes"
            nodes_response = requests.get(nodes_url, headers=headers, verify=False, timeout=30)
            nodes_response.raise_for_status()
            nodes_result = nodes_response.json()

            if 'data' not in nodes_result:
                raise RuntimeError("No data in nodes response")

            result = nodes_result['data']
            nodes = []

            # Get detailed info for each node
            for node in result:
                node_name = node["node"]
                try:
                    # Get detailed status for each node
                    status_url = f"{base_url}/api2/json/nodes/{node_name}/status"
                    status_response = requests.get(status_url, headers=headers, verify=False, timeout=30)
                    status_response.raise_for_status()
                    status_result = status_response.json()

                    if 'data' in status_result:
                        status = status_result['data']
                        nodes.append({
                            "node": node_name,
                            "status": node["status"],
                            "uptime": status.get("uptime", 0),
                            "maxcpu": status.get("cpuinfo", {}).get("cpus", "N/A"),
                            "memory": {
                                "used": status.get("memory", {}).get("used", 0),
                                "total": status.get("memory", {}).get("total", 0)
                            }
                        })
                    else:
                        raise Exception("No status data")
                except Exception:
                    # Fallback to basic info if detailed status fails
                    nodes.append({
                        "node": node_name,
                        "status": node["status"],
                        "uptime": 0,
                        "maxcpu": "N/A",
                        "memory": {
                            "used": node.get("maxmem", 0) - node.get("mem", 0),
                            "total": node.get("maxmem", 0)
                        }
                    })
            return self._format_response(nodes, "nodes")
        except Exception as e:
            self._handle_error("get nodes", e)

    def get_node_status(self, node: str) -> List[Content]:
        """Get detailed status information for a specific node.

        Retrieves comprehensive status information including:
        - CPU usage and configuration
        - Memory utilization details
        - Uptime and load statistics
        - Network status
        - Storage health
        - Running tasks and services

        Args:
            node: Name/ID of node to query (e.g., 'pve1', 'proxmox-node2')

        Returns:
            List of Content objects containing detailed node status:
            {
                "uptime": seconds,
                "cpu": {
                    "usage": percentage,
                    "cores": count
                },
                "memory": {
                    "used": bytes,
                    "total": bytes,
                    "free": bytes
                },
                ...additional status fields
            }

        Raises:
            ValueError: If the specified node is not found
            RuntimeError: If status retrieval fails (node offline, network issues)
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

            # Get node status
            status_url = f"{base_url}/api2/json/nodes/{node}/status"
            status_response = requests.get(status_url, headers=headers, verify=False, timeout=30)
            status_response.raise_for_status()
            status_result = status_response.json()

            if 'data' not in status_result:
                raise RuntimeError("No data in node status response")

            result = status_result['data']
            return self._format_response((node, result), "node_status")
        except Exception as e:
            self._handle_error(f"get status for node {node}", e)
