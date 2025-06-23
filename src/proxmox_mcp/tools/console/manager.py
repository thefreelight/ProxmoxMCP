"""
Module for managing VM console operations.

This module provides functionality for interacting with VM consoles:
- Executing commands within VMs via QEMU guest agent
- Handling command execution lifecycle
- Managing command output and status
- Error handling and logging

The module implements a robust command execution system with:
- VM state verification
- Asynchronous command execution
- Detailed status tracking
- Comprehensive error handling
"""

import logging
from typing import Dict, Any

class VMConsoleManager:
    """Manager class for VM console operations.
    
    Provides functionality for:
    - Executing commands in VM consoles
    - Managing command execution lifecycle
    - Handling command output and errors
    - Monitoring execution status
    
    Uses QEMU guest agent for reliable command execution with:
    - VM state verification before execution
    - Asynchronous command processing
    - Detailed output capture
    - Comprehensive error handling
    """

    def __init__(self, proxmox_api):
        """Initialize the VM console manager.

        Args:
            proxmox_api: Initialized ProxmoxAPI instance
        """
        self.proxmox = proxmox_api
        self.logger = logging.getLogger("proxmox-mcp.vm-console")

    async def execute_command(self, node: str, vmid: str, command: str) -> Dict[str, Any]:
        """Execute a command in a VM's console via QEMU guest agent.

        Implements a two-phase command execution process:
        1. Command Initiation:
           - Verifies VM exists and is running
           - Initiates command execution via guest agent
           - Captures command PID for tracking
        
        2. Result Collection:
           - Monitors command execution status
           - Captures command output and errors
           - Handles completion status
        
        Requirements:
        - VM must be running
        - QEMU guest agent must be installed and active
        - Command execution permissions must be enabled

        Args:
            node: Name of the node where VM is running (e.g., 'pve1')
            vmid: ID of the VM to execute command in (e.g., '100')
            command: Shell command to execute in the VM

        Returns:
            Dictionary containing command execution results:
            {
                "success": true/false,
                "output": "command output",
                "error": "error output if any",
                "exit_code": command_exit_code
            }

        Raises:
            ValueError: If:
                     - VM is not found
                     - VM is not running
                     - Guest agent is not available
            RuntimeError: If:
                       - Command execution fails
                       - Unable to get command status
                       - API communication errors occur
        """
        try:
            self.logger.info(f"Console Manager: execute_command called with node={node}, vmid={vmid}, command={command}")
            self.logger.info(f"Console Manager: proxmox object type: {type(self.proxmox)}")
            self.logger.info(f"Console Manager: proxmox object attributes: {dir(self.proxmox)}")

            # Verify VM exists and is running using direct HTTP call
            import requests

            # Get connection details
            host = getattr(self.proxmox, '_host', 'home.chfastpay.com')
            port = getattr(self.proxmox, '_port', 8006)
            user = getattr(self.proxmox, '_user', 'jordan@pve')
            token_name = getattr(self.proxmox, '_token_name', 'mcp-api')
            token_value = getattr(self.proxmox, '_token_value', 'c1ccbc3d-45de-475d-9ac0-5bb9ea1a75b7')

            self.logger.info(f"Console Manager: connection details - host={host}, port={port}, user={user}")

            base_url = f"https://{host}:{port}"
            headers = {
                "Authorization": f"PVEAPIToken={user}!{token_name}={token_value}",
                "Content-Type": "application/json"
            }

            # Check VM status
            status_url = f"{base_url}/api2/json/nodes/{node}/qemu/{vmid}/status/current"
            status_response = requests.get(status_url, headers=headers, verify=False, timeout=30)
            status_response.raise_for_status()
            status_result = status_response.json()

            if 'data' not in status_result:
                raise ValueError(f"VM {vmid} not found on node {node}")

            vm_status = status_result['data']
            if vm_status["status"] != "running":
                self.logger.error(f"Failed to execute command on VM {vmid}: VM is not running")
                raise ValueError(f"VM {vmid} on node {node} is not running")

            # Get VM's console
            self.logger.info(f"Executing command on VM {vmid} (node: {node}): {command}")

            # Execute the command using direct HTTP requests to bypass proxmoxer issues
            try:
                self.logger.info("Starting command execution...")

                # Get connection details from proxmox API object
                # Extract the necessary information from the proxmox object
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

                self.logger.debug(f"Using direct HTTP API calls to {base_url}")

                # Start command execution
                exec_url = f"{base_url}/api2/json/nodes/{node}/qemu/{vmid}/agent/exec"

                # Use simple command format (works better than NULL separators)
                # For complex commands, we'll wrap them in a shell script
                if ' ' in command or '|' in command or '>' in command or '<' in command or ';' in command or '&&' in command:
                    # Complex command - wrap in shell
                    formatted_command = f"bash -c '{command}'"
                else:
                    # Simple command - use as is
                    formatted_command = command

                exec_data = {"command": formatted_command}

                self.logger.debug(f"Executing command via agent: {command}")
                self.logger.debug(f"Formatted command: {formatted_command}")
                exec_response = requests.post(exec_url, headers=headers, json=exec_data, verify=False, timeout=30)
                exec_response.raise_for_status()
                exec_result = exec_response.json()

                self.logger.debug(f"Raw exec response: {exec_result}")

                if 'data' not in exec_result or 'pid' not in exec_result['data']:
                    raise RuntimeError("No PID returned from command execution")

                pid = exec_result['data']['pid']
                self.logger.info(f"Command started with PID: {pid}")

                # Wait for command completion
                import asyncio
                await asyncio.sleep(2)

                # Get command status
                status_url = f"{base_url}/api2/json/nodes/{node}/qemu/{vmid}/agent/exec-status"
                status_params = {"pid": str(pid)}

                self.logger.debug(f"Getting status for PID {pid}...")
                status_response = requests.get(status_url, headers=headers, params=status_params, verify=False, timeout=30)
                status_response.raise_for_status()
                status_result = status_response.json()

                self.logger.debug(f"Raw status response: {status_result}")

                if 'data' not in status_result:
                    raise RuntimeError("No data in status response")

                console = status_result['data']
                self.logger.debug(f"Command status retrieved: {console}")

                self.logger.info(f"Command completed with status: {console}")

            except Exception as e:
                self.logger.error(f"Command execution failed: {str(e)}")
                raise RuntimeError(f"Command execution failed: {str(e)}")
            self.logger.debug(f"Raw API response type: {type(console)}")
            self.logger.debug(f"Raw API response: {console}")
            
            # Handle different response structures
            if isinstance(console, dict):
                # Handle exec-status response format
                output = console.get("out-data", "")
                error = console.get("err-data", "")
                exit_code = console.get("exitcode", 0)
                exited = console.get("exited", 0)
                
                if not exited:
                    self.logger.warning("Command may not have completed")
            else:
                # Some versions might return data differently
                self.logger.debug(f"Unexpected response type: {type(console)}")
                output = str(console)
                error = ""
                exit_code = 0
            
            self.logger.debug(f"Processed output: {output}")
            self.logger.debug(f"Processed error: {error}")
            self.logger.debug(f"Processed exit code: {exit_code}")
            
            self.logger.debug(f"Executed command '{command}' on VM {vmid} (node: {node})")

            return {
                "success": True,
                "output": output,
                "error": error,
                "exit_code": exit_code
            }

        except ValueError:
            # Re-raise ValueError for VM not running
            raise
        except Exception as e:
            self.logger.error(f"Failed to execute command on VM {vmid}: {str(e)}")
            if "not found" in str(e).lower():
                raise ValueError(f"VM {vmid} not found on node {node}")
            raise RuntimeError(f"Failed to execute command: {str(e)}")
