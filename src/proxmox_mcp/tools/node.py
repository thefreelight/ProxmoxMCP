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
            nodes = [{"node": node["node"], "status": node["status"]} for node in result]
            return self._format_response(nodes)
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
            return self._format_response(result)
        except Exception as e:
            self._handle_error(f"get status for node {node}", e)
