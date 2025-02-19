# Proxmox MCP Server

A Python-based Model Context Protocol (MCP) server for interacting with Proxmox hypervisors, providing a clean interface for managing nodes, VMs, and containers.

## Features

- Built with the official MCP SDK
- Secure token-based authentication with Proxmox
- Tools for managing nodes, VMs, and containers
- VM console command execution
- Configurable logging system
- Type-safe implementation with Pydantic
- Full integration with Claude Desktop

## Installation for Cline Users

If you're using this MCP server with Cline, follow these steps for installation:

1. Create a directory for your MCP servers (if you haven't already):
   ```bash
   mkdir -p ~/Documents/Cline/MCP
   cd ~/Documents/Cline/MCP
   ```

2. Clone and install the package:
   ```bash
   # Clone the repository
   git clone https://github.com/yourusername/proxmox-mcp.git

   # Install in development mode with dependencies
   pip install -e "proxmox-mcp[dev]"
   ```

3. Create your configuration:
   ```bash
   # Create config directory
   mkdir proxmox-config
   cd proxmox-config
   ```

   Create `config.json`:
   ```json
   {
       "proxmox": {
           "host": "your-proxmox-host",
           "port": 8006,
           "verify_ssl": true,
           "service": "PVE"
       },
       "auth": {
           "user": "your-username@pve",
           "token_name": "your-token-name",
           "token_value": "your-token-value"
       },
       "logging": {
           "level": "INFO",
           "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
           "file": "proxmox_mcp.log"
       }
   }
   ```

4. Install in Claude Desktop:
   ```bash
   cd ~/Documents/Cline/MCP
   mcp install proxmox-mcp/src/proxmox_mcp/server.py \
     --name "Proxmox Manager" \
     -v PROXMOX_MCP_CONFIG=./proxmox-config/config.json
   ```

5. The server will now be available in Cline with these tools:
   - `get_nodes`: List all nodes in the cluster
   - `get_node_status`: Get detailed status of a node
   - `get_vms`: List all VMs
   - `get_containers`: List all LXC containers
   - `get_storage`: List available storage
   - `get_cluster_status`: Get cluster status
   - `execute_vm_command`: Run commands in VM consoles

## Development Setup

1. Install UV:
   ```bash
   pip install uv
   ```

2. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/proxmox-mcp.git
   cd proxmox-mcp
   ```

3. Create and activate virtual environment:
   ```bash
   # Create venv
   uv venv

   # Activate venv (Windows)
   .venv\Scripts\activate
   # OR Activate venv (Unix/MacOS)
   source .venv/bin/activate
   ```

4. Install dependencies:
   ```bash
   # Install with development dependencies
   uv pip install -e ".[dev]"
   # OR install only runtime dependencies
   uv pip install -e .
   ```

## Configuration

### Proxmox API Token Setup
1. Log into your Proxmox web interface
2. Navigate to Datacenter -> Permissions -> API Tokens
3. Create a new API token:
   - Select a user (e.g., root@pam)
   - Enter a token ID (e.g., "mcp-token")
   - Uncheck "Privilege Separation" if you want full access
   - Save and copy both the token ID and secret

### Server Configuration
Configure the server using either a JSON file or environment variables:

#### Using JSON Configuration
1. Copy the example configuration:
   ```bash
   cp config/config.example.json config/config.json
   ```

2. Edit `config/config.json`:
   ```json
   {
       "proxmox": {
           "host": "your-proxmox-host",
           "port": 8006,
           "verify_ssl": true,
           "service": "PVE"
       },
       "auth": {
           "user": "username@pve",
           "token_name": "your-token-name",
           "token_value": "your-token-value"
       },
       "logging": {
           "level": "INFO",
           "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
           "file": "proxmox_mcp.log"
       }
   }
   ```

#### Using Environment Variables
Set the following environment variables:
```bash
# Required
PROXMOX_HOST=your-host
PROXMOX_USER=username@pve
PROXMOX_TOKEN_NAME=your-token-name
PROXMOX_TOKEN_VALUE=your-token-value

# Optional
PROXMOX_PORT=8006                  # Default: 8006
PROXMOX_VERIFY_SSL=true           # Default: true
PROXMOX_SERVICE=PVE               # Default: PVE
LOG_LEVEL=INFO                    # Default: INFO
LOG_FORMAT=%(asctime)s...         # Default: standard format
LOG_FILE=proxmox_mcp.log         # Default: None (stdout)
```

## Available Tools

The server provides the following MCP tools for interacting with Proxmox:

### get_nodes
Lists all nodes in the Proxmox cluster.

- Parameters: None
- Example Response:
  ```json
  [
    {
      "node": "pve1",
      "status": "online"
    },
    {
      "node": "pve2",
      "status": "online"
    }
  ]
  ```

### get_node_status
Get detailed status of a specific node.

- Parameters:
  - `node` (string, required): Name of the node
- Example Response:
  ```json
  {
    "status": "running",
    "uptime": 1234567,
    "cpu": 0.12,
    "memory": {
      "total": 16777216,
      "used": 8388608,
      "free": 8388608
    }
  }
  ```

### get_vms
List all VMs across the cluster.

- Parameters: None
- Example Response:
  ```json
  [
    {
      "vmid": "100",
      "name": "web-server",
      "status": "running",
      "node": "pve1"
    },
    {
      "vmid": "101",
      "name": "database",
      "status": "stopped",
      "node": "pve2"
    }
  ]
  ```

### get_containers
List all LXC containers.

- Parameters: None
- Example Response:
  ```json
  [
    {
      "vmid": "200",
      "name": "docker-host",
      "status": "running",
      "node": "pve1"
    },
    {
      "vmid": "201",
      "name": "nginx-proxy",
      "status": "running",
      "node": "pve1"
    }
  ]
  ```

### get_storage
List available storage.

- Parameters: None
- Example Response:
  ```json
  [
    {
      "storage": "local",
      "type": "dir"
    },
    {
      "storage": "ceph-pool",
      "type": "rbd"
    }
  ]
  ```

### get_cluster_status
Get overall cluster status.

- Parameters: None
- Example Response:
  ```json
  {
    "quorate": true,
    "nodes": 2,
    "version": "7.4-15",
    "cluster_name": "proxmox-cluster"
  }
  ```

### execute_vm_command
Execute a command in a VM's console using QEMU Guest Agent.

- Parameters:
  - `node` (string, required): Name of the node where VM is running
  - `vmid` (string, required): ID of the VM
  - `command` (string, required): Command to execute
- Example Response:
  ```json
  {
    "success": true,
    "output": "command output here",
    "error": "",
    "exit_code": 0
  }
  ```
- Requirements:
  - VM must be running
  - QEMU Guest Agent must be installed and running in the VM
  - Command execution permissions must be enabled in the Guest Agent
- Error Handling:
  - Returns error if VM is not running
  - Returns error if VM is not found
  - Returns error if command execution fails
  - Includes command output even if command returns non-zero exit code

## Running the Server

### Development Mode
For testing and development, use the MCP development server:
```bash
mcp dev proxmox_mcp/server.py
```

### Claude Desktop Integration
To install the server in Claude Desktop:
```bash
# Basic installation
mcp install proxmox_mcp/server.py

# Installation with custom name and environment variables
mcp install proxmox_mcp/server.py \
  --name "Proxmox Manager" \
  -v PROXMOX_HOST=your-host \
  -v PROXMOX_USER=username@pve \
  -v PROXMOX_TOKEN_NAME=your-token \
  -v PROXMOX_TOKEN_VALUE=your-secret
```

### Direct Execution
Run the server directly:
```bash
python -m proxmox_mcp.server
```

## Error Handling

The server implements comprehensive error handling:

- Authentication Errors: When token authentication fails
- Connection Errors: When unable to connect to Proxmox
- Validation Errors: When tool parameters are invalid
- API Errors: When Proxmox API calls fail

All errors are properly logged and returned with descriptive messages.

## Logging

Logging can be configured through the config file or environment variables:

- Log Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Output: File or stdout
- Format: Customizable format string

Example log output:
```
2025-02-18 19:15:23,456 - proxmox-mcp - INFO - Server started
2025-02-18 19:15:24,789 - proxmox-mcp - INFO - Connected to Proxmox host
2025-02-18 19:15:25,123 - proxmox-mcp - DEBUG - Tool called: get_nodes
```

## Development

- Run tests: `pytest`
- Format code: `black .`
- Type checking: `mypy .`
- Lint: `ruff .`

## Project Structure

```
proxmox-mcp/
├── src/
│   └── proxmox_mcp/
│       ├── server.py          # Main MCP server implementation
│       ├── tools/             # Tool implementations
│       │   └── vm_console.py  # VM console operations
│       └── utils/             # Utilities (auth, logging)
├── tests/                     # Test suite
├── config/
│   └── config.example.json    # Configuration template
├── pyproject.toml            # Project metadata and dependencies
├── requirements.in           # Core dependencies
├── requirements-dev.in       # Development dependencies
└── LICENSE                   # MIT License
```

## License

MIT License
