"""
Base classes and utilities for Proxmox MCP tools.
"""
import logging
from typing import Any, Dict, List, Optional, Union
from mcp.types import TextContent as Content
from proxmoxer import ProxmoxAPI
from ..formatting import ProxmoxTemplates

class ProxmoxTool:
    """Base class for Proxmox MCP tools."""

    def __init__(self, proxmox_api: ProxmoxAPI):
        """Initialize the tool.

        Args:
            proxmox_api: Initialized ProxmoxAPI instance
        """
        self.proxmox = proxmox_api
        self.logger = logging.getLogger(f"proxmox-mcp.{self.__class__.__name__.lower()}")

    def _format_response(self, data: Any, resource_type: Optional[str] = None) -> List[Content]:
        """Format response data into MCP content using templates.

        Args:
            data: Data to format
            resource_type: Optional type of resource for template selection

        Returns:
            List of Content objects
        """
        if resource_type == "nodes":
            formatted = ProxmoxTemplates.node_list(data)
        elif resource_type == "node_status":
            # For node_status, data should be a tuple of (node_name, status_dict)
            if isinstance(data, tuple) and len(data) == 2:
                formatted = ProxmoxTemplates.node_status(data[0], data[1])
            else:
                formatted = ProxmoxTemplates.node_status("unknown", data)
        elif resource_type == "vms":
            formatted = ProxmoxTemplates.vm_list(data)
        elif resource_type == "storage":
            formatted = ProxmoxTemplates.storage_list(data)
        elif resource_type == "containers":
            formatted = ProxmoxTemplates.container_list(data)
        elif resource_type == "cluster":
            formatted = ProxmoxTemplates.cluster_status(data)
        else:
            # Fallback to JSON formatting for unknown types
            import json
            formatted = json.dumps(data, indent=2)

        return [Content(type="text", text=formatted)]

    def _handle_error(self, operation: str, error: Exception) -> None:
        """Handle and log errors.

        Args:
            operation: Description of the operation that failed
            error: The exception that occurred

        Raises:
            ValueError: For invalid input or state
            RuntimeError: For other errors
        """
        error_msg = str(error)
        self.logger.error(f"Failed to {operation}: {error_msg}")

        if "not found" in error_msg.lower():
            raise ValueError(f"Resource not found: {error_msg}")
        if "permission denied" in error_msg.lower():
            raise ValueError(f"Permission denied: {error_msg}")
        if "invalid" in error_msg.lower():
            raise ValueError(f"Invalid input: {error_msg}")
        
        raise RuntimeError(f"Failed to {operation}: {error_msg}")
