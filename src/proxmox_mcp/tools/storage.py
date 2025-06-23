"""
Storage-related tools for Proxmox MCP.

This module provides tools for managing and monitoring Proxmox storage:
- Listing all storage pools across the cluster
- Retrieving detailed storage information including:
  * Storage type and content types
  * Usage statistics and capacity
  * Availability status
  * Node assignments

The tools implement fallback mechanisms for scenarios where
detailed storage information might be temporarily unavailable.
"""
from typing import List
from mcp.types import TextContent as Content
from .base import ProxmoxTool
from .definitions import GET_STORAGE_DESC

class StorageTools(ProxmoxTool):
    """Tools for managing Proxmox storage.
    
    Provides functionality for:
    - Retrieving cluster-wide storage information
    - Monitoring storage pool status and health
    - Tracking storage utilization and capacity
    - Managing storage content types
    
    Implements fallback mechanisms for scenarios where detailed
    storage information might be temporarily unavailable.
    """

    def get_storage(self) -> List[Content]:
        """List storage pools across the cluster with detailed status.

        Retrieves comprehensive information for each storage pool including:
        - Basic identification (name, type)
        - Content types supported (VM disks, backups, ISO images, etc.)
        - Availability status (online/offline)
        - Usage statistics:
          * Used space
          * Total capacity
          * Available space
        
        Implements a fallback mechanism that returns basic information
        if detailed status retrieval fails for any storage pool.

        Returns:
            List of Content objects containing formatted storage information:
            {
                "storage": "storage-name",
                "type": "storage-type",
                "content": ["content-types"],
                "status": "online/offline",
                "used": bytes,
                "total": bytes,
                "available": bytes
            }

        Raises:
            RuntimeError: If the cluster-wide storage query fails
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

            # Get storage list
            storage_url = f"{base_url}/api2/json/storage"
            storage_response = requests.get(storage_url, headers=headers, verify=False, timeout=30)
            storage_response.raise_for_status()
            storage_result = storage_response.json()

            if 'data' not in storage_result:
                raise RuntimeError("No data in storage response")

            result = storage_result['data']
            storage = []

            for store in result:
                # Get detailed storage info including usage
                try:
                    node_name = store.get("node", "localhost")
                    storage_name = store["storage"]
                    status_url = f"{base_url}/api2/json/nodes/{node_name}/storage/{storage_name}/status"
                    status_response = requests.get(status_url, headers=headers, verify=False, timeout=30)
                    status_response.raise_for_status()
                    status_result = status_response.json()

                    if 'data' in status_result:
                        status = status_result['data']
                        storage.append({
                            "storage": store["storage"],
                            "type": store["type"],
                            "content": store.get("content", []),
                            "status": "online" if store.get("enabled", True) else "offline",
                            "used": status.get("used", 0),
                            "total": status.get("total", 0),
                            "available": status.get("avail", 0)
                        })
                    else:
                        raise Exception("No status data")
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
