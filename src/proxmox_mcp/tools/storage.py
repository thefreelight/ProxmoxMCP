"""
Storage-related tools for Proxmox MCP.
"""
from typing import List
from mcp.types import TextContent as Content
from .base import ProxmoxTool
from .definitions import GET_STORAGE_DESC

class StorageTools(ProxmoxTool):
    """Tools for managing Proxmox storage."""

    def get_storage(self) -> List[Content]:
        """List storage pools across the cluster.

        Returns:
            List of Content objects containing storage information

        Raises:
            RuntimeError: If the operation fails
        """
        try:
            result = self.proxmox.storage.get()
            storage = [{
                "storage": storage["storage"],
                "type": storage["type"],
                "content": storage.get("content", []),
                "enabled": storage.get("enabled", True)
            } for storage in result]
            return self._format_response(storage)
        except Exception as e:
            self._handle_error("get storage", e)
