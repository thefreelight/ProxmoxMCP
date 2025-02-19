"""
Proxmox API setup and management.
"""
import logging
from typing import Dict, Any
from proxmoxer import ProxmoxAPI
from ..config.models import ProxmoxConfig, AuthConfig

class ProxmoxManager:
    """Manager class for Proxmox API operations."""
    
    def __init__(self, proxmox_config: ProxmoxConfig, auth_config: AuthConfig):
        """Initialize the Proxmox API manager.

        Args:
            proxmox_config: Proxmox connection configuration
            auth_config: Authentication configuration
        """
        self.logger = logging.getLogger("proxmox-mcp.proxmox")
        self.config = self._create_config(proxmox_config, auth_config)
        self.api = self._setup_api()

    def _create_config(self, proxmox_config: ProxmoxConfig, auth_config: AuthConfig) -> Dict[str, Any]:
        """Create a configuration dictionary for ProxmoxAPI.

        Args:
            proxmox_config: Proxmox connection configuration
            auth_config: Authentication configuration

        Returns:
            Dictionary containing merged configuration
        """
        return {
            'host': proxmox_config.host,
            'port': proxmox_config.port,
            'user': auth_config.user,
            'token_name': auth_config.token_name,
            'token_value': auth_config.token_value,
            'verify_ssl': proxmox_config.verify_ssl,
            'service': proxmox_config.service
        }

    def _setup_api(self) -> ProxmoxAPI:
        """Initialize and test Proxmox API connection.

        Returns:
            Initialized ProxmoxAPI instance

        Raises:
            RuntimeError: If connection fails
        """
        try:
            self.logger.info(f"Connecting to Proxmox host: {self.config['host']}")
            api = ProxmoxAPI(**self.config)
            
            # Test connection
            api.version.get()
            self.logger.info("Successfully connected to Proxmox API")
            
            return api
        except Exception as e:
            self.logger.error(f"Failed to connect to Proxmox: {e}")
            raise RuntimeError(f"Failed to connect to Proxmox: {e}")

    def get_api(self) -> ProxmoxAPI:
        """Get the initialized Proxmox API instance.

        Returns:
            ProxmoxAPI instance
        """
        return self.api
