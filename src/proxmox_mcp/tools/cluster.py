"""
Cluster-related tools for Proxmox MCP.
"""
from typing import List
from mcp.types import TextContent as Content
from .base import ProxmoxTool
from .definitions import GET_CLUSTER_STATUS_DESC

class ClusterTools(ProxmoxTool):
    """Tools for managing Proxmox cluster."""

    def get_cluster_status(self) -> List[Content]:
        """Get overall Proxmox cluster health and configuration status.

        Returns:
            List of Content objects containing cluster status

        Raises:
            RuntimeError: If the operation fails
        """
        try:
            result = self.proxmox.cluster.status.get()
            status = {
                "name": result[0].get("name") if result else None,
                "quorum": result[0].get("quorate"),
                "nodes": len([node for node in result if node.get("type") == "node"]),
                "resources": [res for res in result if res.get("type") == "resource"]
            }
            return self._format_response(status, "cluster")
        except Exception as e:
            self._handle_error("get cluster status", e)
