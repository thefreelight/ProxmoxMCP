"""
Base classes and utilities for Proxmox MCP tools.
"""
import logging
from typing import Any, Dict, List, Optional
from mcp.types import TextContent as Content
from proxmoxer import ProxmoxAPI

class ProxmoxTool:
    """Base class for Proxmox MCP tools."""

    def __init__(self, proxmox_api: ProxmoxAPI):
        """Initialize the tool.

        Args:
            proxmox_api: Initialized ProxmoxAPI instance
        """
        self.proxmox = proxmox_api
        self.logger = logging.getLogger(f"proxmox-mcp.{self.__class__.__name__.lower()}")

    def _format_response(self, data: Any) -> List[Content]:
        """Format response data into MCP content.

        Args:
            data: Data to format

        Returns:
            List of Content objects
        """
        import json
        return [Content(type="text", text=json.dumps(data, indent=2))]

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
