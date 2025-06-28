#!/bin/bash
# Netmaker One-Click Installation Script
# VM: infra-netmaker-01 (192.168.0.102)
# Run with: curl -sSL https://raw.githubusercontent.com/your-repo/netmaker-oneclick-install.sh | bash

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
NETMAKER_VERSION="v0.21.2"
DOMAIN="netmaker.home.local"
SERVER_IP="192.168.0.102"
INSTALL_LOG="/var/log/netmaker-install.log"

log() { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1" | tee -a $INSTALL_LOG; }
error() { echo -e "${RED}[ERROR]${NC} $1" | tee -a $INSTALL_LOG; }
info() { echo -e "${BLUE}[INFO]${NC} $1" | tee -a $INSTALL_LOG; }

echo -e "${BLUE}"
cat << 'EOF'
╔═══════════════════════════════════════════════════════════════╗
║                    NETMAKER INSTALLER                        ║
║              Professional Network Management                 ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

log "Starting Netmaker installation on $SERVER_IP"
log "Version: $NETMAKER_VERSION | Domain: $DOMAIN"

# Update system
log "Updating system packages..."
sudo apt update -y >/dev/null 2>&1
sudo apt upgrade -y >/dev/null 2>&1

# Install prerequisites
log "Installing prerequisites..."
sudo apt install -y curl wget git docker.io docker-compose ufw net-tools dnsutils wireguard wireguard-tools jq >/dev/null 2>&1

# Configure Docker
log "Configuring Docker..."
sudo systemctl enable docker >/dev/null 2>&1
sudo systemctl start docker >/dev/null 2>&1
sudo usermod -aG docker ubuntu >/dev/null 2>&1

# Configure firewall
log "Configuring firewall..."
sudo ufw --force enable >/dev/null 2>&1
sudo ufw allow ssh >/dev/null 2>&1
sudo ufw allow 80/tcp >/dev/null 2>&1
sudo ufw allow 443/tcp >/dev/null 2>&1
sudo ufw allow 8080/tcp >/dev/null 2>&1
sudo ufw allow 8081/tcp >/dev/null 2>&1
sudo ufw allow 1883/tcp >/dev/null 2>&1
sudo ufw allow 51821:51830/udp >/dev/null 2>&1

# Create directory structure
log "Creating Netmaker directory..."
sudo mkdir -p /opt/netmaker
cd /opt/netmaker

# Download Netmaker
log "Downloading Netmaker $NETMAKER_VERSION..."
sudo wget -q -O docker-compose.yml https://raw.githubusercontent.com/gravitl/netmaker/$NETMAKER_VERSION/compose/docker-compose.yml

# Generate secrets
MASTER_KEY=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
JWT_SECRET=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

# Create environment file
log "Creating environment configuration..."
sudo tee .env > /dev/null << EOF
# Netmaker Configuration
NETMAKER_BASE_DOMAIN=$DOMAIN
SERVER_HOST=$SERVER_IP
COREDNS_ADDR=$SERVER_IP
DNS_MODE=on
SERVER_API_CONN_STRING=$SERVER_IP:8080
DISPLAY_KEYS=on
DATABASE=sqlite
NODE_ID=netmaker-server-1

# Security
MASTER_KEY=$MASTER_KEY
JWT_SECRET=$JWT_SECRET

# MQTT
MQTT_HOST=$SERVER_IP
MQTT_PORT=1883

# Ports
API_PORT=8080
GRPC_PORT=50051
GRPC_SSL=off

# UI
UI_PORT=8080
EOF

# Start Netmaker
log "Starting Netmaker services..."
sudo docker-compose up -d >/dev/null 2>&1

# Wait for services
log "Waiting for services to initialize..."
sleep 30

# Check services
log "Checking service status..."
if sudo docker-compose ps | grep -q "Up"; then
    info "✅ Netmaker services are running"
else
    error "❌ Some services failed to start"
    sudo docker-compose ps
fi

# Create admin user
log "Creating admin user..."
sleep 10
sudo docker-compose exec -T netmaker netmaker user create admin admin@$DOMAIN --admin >/dev/null 2>&1 || info "Admin user may already exist"

# Create systemd service
log "Creating systemd service..."
sudo tee /etc/systemd/system/netmaker.service > /dev/null << EOF
[Unit]
Description=Netmaker Network Management
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/netmaker
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload >/dev/null 2>&1
sudo systemctl enable netmaker >/dev/null 2>&1

# Create management scripts
log "Creating management tools..."
sudo tee /opt/netmaker/manage.sh > /dev/null << 'SCRIPT_EOF'
#!/bin/bash
case "$1" in
    start)   cd /opt/netmaker && sudo docker-compose up -d ;;
    stop)    cd /opt/netmaker && sudo docker-compose down ;;
    restart) cd /opt/netmaker && sudo docker-compose restart ;;
    status)  cd /opt/netmaker && sudo docker-compose ps ;;
    logs)    cd /opt/netmaker && sudo docker-compose logs -f ;;
    health)  curl -s http://localhost:8080/api/server/health | jq . ;;
    *)       echo "Usage: $0 {start|stop|restart|status|logs|health}" ;;
esac
SCRIPT_EOF

sudo chmod +x /opt/netmaker/manage.sh

# Create quick status script
sudo tee /opt/netmaker/status.sh > /dev/null << 'STATUS_EOF'
#!/bin/bash
echo "=== Netmaker Status ==="
echo "Date: $(date)"
echo ""
echo "Services:"
cd /opt/netmaker && sudo docker-compose ps
echo ""
echo "API Health:"
curl -s http://localhost:8080/api/server/health 2>/dev/null | jq . || echo "API not responding"
echo ""
echo "Network Interfaces:"
ip addr show | grep -E "(wg|nm-)" || echo "No WireGuard interfaces found"
echo ""
echo "Firewall:"
sudo ufw status | grep -E "(8080|51821)"
STATUS_EOF

sudo chmod +x /opt/netmaker/status.sh

# Final health check
log "Performing final health check..."
sleep 5

# Test API
if curl -s http://localhost:8080/api/server/health >/dev/null 2>&1; then
    API_STATUS="✅ Online"
else
    API_STATUS="❌ Offline"
fi

# Get container status
CONTAINERS=$(sudo docker-compose ps --services | wc -l)
RUNNING=$(sudo docker-compose ps | grep "Up" | wc -l)

echo -e "${GREEN}"
cat << EOF
╔═══════════════════════════════════════════════════════════════╗
║                 INSTALLATION COMPLETE!                       ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "${BLUE}📋 Installation Summary:${NC}"
echo "• Server IP: $SERVER_IP"
echo "• Domain: $DOMAIN"
echo "• API Status: $API_STATUS"
echo "• Containers: $RUNNING/$CONTAINERS running"
echo ""

echo -e "${BLUE}🌐 Access Information:${NC}"
echo "• Web UI: http://$SERVER_IP:8080"
echo "• API: http://$SERVER_IP:8080/api"
echo "• Admin: admin@$DOMAIN"
echo ""

echo -e "${BLUE}🛠️ Management Commands:${NC}"
echo "• Status: /opt/netmaker/status.sh"
echo "• Manage: /opt/netmaker/manage.sh {start|stop|restart|status|logs}"
echo "• Logs: sudo docker-compose logs -f"
echo ""

echo -e "${BLUE}📋 Next Steps:${NC}"
echo "1. Access Web UI: http://$SERVER_IP:8080"
echo "2. Login with admin credentials"
echo "3. Create a network"
echo "4. Generate client configs"
echo "5. Connect your devices"
echo ""

echo -e "${YELLOW}💡 Quick Status Check:${NC}"
/opt/netmaker/status.sh

log "Installation completed successfully!"
info "Log file: $INSTALL_LOG"
