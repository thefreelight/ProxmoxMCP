"""
Node-related tools for Proxmox MCP.
"""
from typing import List
from mcp.types import TextContent as Content
from .base import ProxmoxTool
from .definitions import GET_NODES_DESC, GET_NODE_STATUS_DESC

class NodeTools(ProxmoxTool):
    """Tools for managing Proxmox nodes."""

    def get_nodes(self) -> List[Content]:
        """List all nodes in the Proxmox cluster.

        Returns:
            List of Content objects containing node information

        Raises:
            RuntimeError: If the operation fails
        """
        try:
            result = self.proxmox.nodes.get()
            nodes = []
            
            # Get detailed info for each node
            for node in result:
                node_name = node["node"]
                try:
                    # Get detailed status for each node
                    status = self.proxmox.nodes(node_name).status.get()
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

        Args:
            node: Name/ID of node to query

        Returns:
            List of Content objects containing node status

        Raises:
            ValueError: If node is not found
            RuntimeError: If the operation fails
        """
        try:
            result = self.proxmox.nodes(node).status.get()
            return self._format_response((node, result), "node_status")
        except Exception as e:
            self._handle_error(f"get status for node {node}", e)
