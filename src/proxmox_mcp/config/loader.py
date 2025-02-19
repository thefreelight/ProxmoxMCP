"""
Configuration loading utilities for the Proxmox MCP server.
"""
import json
import os
from typing import Optional
from .models import Config

def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from file.

    Args:
        config_path: Path to the configuration file

    Returns:
        Config object containing the loaded configuration

    Raises:
        ValueError: If config path is not provided or config is invalid
    """
    if not config_path:
        raise ValueError("PROXMOX_MCP_CONFIG environment variable must be set")

    try:
        with open(config_path) as f:
            config_data = json.load(f)
            if not config_data.get('proxmox', {}).get('host'):
                raise ValueError("Proxmox host cannot be empty")
            return Config(**config_data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file: {e}")
    except Exception as e:
        raise ValueError(f"Failed to load config: {e}")
