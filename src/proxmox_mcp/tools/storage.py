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
            storage = []
            
            for store in result:
                # Get detailed storage info including usage
                try:
                    status = self.proxmox.nodes(store.get("node", "localhost")).storage(store["storage"]).status.get()
                    storage.append({
                        "storage": store["storage"],
                        "type": store["type"],
                        "content": store.get("content", []),
                        "status": "online" if store.get("enabled", True) else "offline",
                        "used": status.get("used", 0),
                        "total": status.get("total", 0),
                        "available": status.get("avail", 0)
                    })
                except Exception:
                    # If detailed status fails, add basic info
                    storage.append({
                        "storage": store["storage"],
                        "type": store["type"],
                        "content": store.get("content", []),
                        "status": "online" if store.get("enabled", True) else "offline",
                        "used": 0,
                        "total": 0,
                        "available": 0
                    })
                    
            return self._format_response(storage, "storage")
        except Exception as e:
            self._handle_error("get storage", e)
