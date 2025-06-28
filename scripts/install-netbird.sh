#!/bin/bash
# NetBird VPN Controller Installation Script
# VM 102 - 192.168.0.102

set -e

echo "🔧 Installing NetBird VPN Controller..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install -y docker-compose

# Create NetBird directory
mkdir -p ~/netbird
cd ~/netbird

# Create docker-compose.yml for NetBird
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  # NetBird Management Service
  netbird-management:
    image: netbirdio/management:latest
    restart: unless-stopped
    ports:
      - "443:443"
      - "33073:33073"
    environment:
      - NETBIRD_MGMT_API_PORT=443
      - NETBIRD_MGMT_GRPC_PORT=33073
      - NETBIRD_MGMT_DATADIR=/var/lib/netbird
      - NETBIRD_MGMT_DNS_DOMAIN=company.local
      - NETBIRD_MGMT_SINGLE_ACCOUNT_MODE_DOMAIN=company.local
      - NETBIRD_MGMT_DISABLE_ANONYMOUS_METRICS=true
    volumes:
      - netbird_mgmt:/var/lib/netbird
      - ./management.json:/etc/netbird/management.json
    command: ["--log-level", "info"]

  # NetBird Signal Server
  netbird-signal:
    image: netbirdio/signal:latest
    restart: unless-stopped
    ports:
      - "10000:10000"
    volumes:
      - netbird_signal:/var/lib/netbird-signal

  # Coturn STUN/TURN Server
  coturn:
    image: coturn/coturn:latest
    restart: unless-stopped
    ports:
      - "3478:3478/udp"
      - "49152-65535:49152-65535/udp"
    environment:
      - TURN_USERNAME=netbird
      - TURN_PASSWORD=netbird123
    command: [
      "-n",
      "--log-file=stdout",
      "--external-ip=192.168.0.102",
      "--listening-port=3478",
      "--fingerprint",
      "--lt-cred-mech",
      "--user=netbird:netbird123",
      "--realm=company.local"
    ]

volumes:
  netbird_mgmt:
  netbird_signal:
EOF

# Create management configuration
cat > management.json << 'EOF'
{
  "Stuns": [
    {
      "Proto": "udp",
      "URI": "stun:192.168.0.102:3478"
    }
  ],
  "TURNConfig": {
    "Turns": [
      {
        "Proto": "udp",
        "URI": "turn:192.168.0.102:3478",
        "Username": "netbird",
        "Password": "netbird123"
      }
    ]
  },
  "Signal": {
    "Proto": "http",
    "URI": "192.168.0.102:10000"
  }
}
EOF

# Start NetBird services
sudo docker-compose up -d

# Configure firewall
sudo ufw allow 443/tcp
sudo ufw allow 33073/tcp
sudo ufw allow 10000/tcp
sudo ufw allow 3478/udp
sudo ufw allow 49152:65535/udp

echo "✅ NetBird installation completed!"
echo "🌐 Management UI: https://192.168.0.102"
echo "📡 Signal Server: 192.168.0.102:10000"
echo "🔄 STUN/TURN: 192.168.0.102:3478"
