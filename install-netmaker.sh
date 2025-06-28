#!/bin/bash
# Professional Netmaker Installation Script
# VM: infra-netmaker-01 (102)
# Purpose: Network Management and WireGuard VPN Service

set -e

# Configuration
NETMAKER_VERSION="v0.21.2"
DOMAIN="netmaker.home.local"
SERVER_IP="192.168.0.102"
INSTALL_LOG="/var/log/netmaker-install.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a $INSTALL_LOG
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a $INSTALL_LOG
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a $INSTALL_LOG
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a $INSTALL_LOG
}

# Start installation
log "=========================================="
log "Starting Netmaker Installation"
log "Version: $NETMAKER_VERSION"
log "Domain: $DOMAIN"
log "Server IP: $SERVER_IP"
log "=========================================="

# Update system
log "Updating system packages..."
apt-get update -y >> $INSTALL_LOG 2>&1
apt-get upgrade -y >> $INSTALL_LOG 2>&1

# Install prerequisites
log "Installing prerequisites..."
apt-get install -y \
    curl \
    wget \
    git \
    docker.io \
    docker-compose \
    ufw \
    net-tools \
    dnsutils \
    wireguard \
    wireguard-tools >> $INSTALL_LOG 2>&1

# Start and enable Docker
log "Configuring Docker..."
systemctl enable docker >> $INSTALL_LOG 2>&1
systemctl start docker >> $INSTALL_LOG 2>&1
usermod -aG docker ubuntu >> $INSTALL_LOG 2>&1

# Configure firewall
log "Configuring firewall..."
ufw --force enable >> $INSTALL_LOG 2>&1
ufw allow ssh >> $INSTALL_LOG 2>&1
ufw allow 80/tcp >> $INSTALL_LOG 2>&1
ufw allow 443/tcp >> $INSTALL_LOG 2>&1
ufw allow 8080/tcp >> $INSTALL_LOG 2>&1
ufw allow 51821:51830/udp >> $INSTALL_LOG 2>&1  # WireGuard ports

# Create netmaker directory
log "Creating Netmaker directory structure..."
mkdir -p /opt/netmaker
cd /opt/netmaker

# Download Netmaker
log "Downloading Netmaker $NETMAKER_VERSION..."
wget -O docker-compose.yml https://raw.githubusercontent.com/gravitl/netmaker/$NETMAKER_VERSION/compose/docker-compose.yml >> $INSTALL_LOG 2>&1

# Configure environment
log "Configuring Netmaker environment..."
cat > .env << EOF
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
MASTER_KEY=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 30)
JWT_SECRET=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 30)

# MQTT
MQTT_HOST=$SERVER_IP
MQTT_PORT=1883

# Ports
API_PORT=8080
GRPC_PORT=50051
EOF

# Start Netmaker
log "Starting Netmaker services..."
docker-compose up -d >> $INSTALL_LOG 2>&1

# Wait for services to start
log "Waiting for services to initialize..."
sleep 30

# Check service status
log "Checking service status..."
docker-compose ps >> $INSTALL_LOG 2>&1

# Create admin user
log "Creating admin user..."
docker-compose exec -T netmaker netmaker user create admin admin@$DOMAIN --admin >> $INSTALL_LOG 2>&1 || warning "Admin user creation failed - may already exist"

# Configure systemd service
log "Creating systemd service..."
cat > /etc/systemd/system/netmaker.service << EOF
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

systemctl daemon-reload >> $INSTALL_LOG 2>&1
systemctl enable netmaker >> $INSTALL_LOG 2>&1

# Configure DNS
log "Configuring DNS settings..."
echo "nameserver 127.0.0.1" > /etc/resolv.conf.netmaker
echo "nameserver 8.8.8.8" >> /etc/resolv.conf.netmaker

# Create management scripts
log "Creating management scripts..."
cat > /opt/netmaker/manage.sh << 'EOF'
#!/bin/bash
# Netmaker Management Script

case "$1" in
    start)
        echo "Starting Netmaker..."
        cd /opt/netmaker && docker-compose up -d
        ;;
    stop)
        echo "Stopping Netmaker..."
        cd /opt/netmaker && docker-compose down
        ;;
    restart)
        echo "Restarting Netmaker..."
        cd /opt/netmaker && docker-compose restart
        ;;
    status)
        echo "Netmaker Status:"
        cd /opt/netmaker && docker-compose ps
        ;;
    logs)
        echo "Netmaker Logs:"
        cd /opt/netmaker && docker-compose logs -f
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
EOF

chmod +x /opt/netmaker/manage.sh

# Create status check script
cat > /opt/netmaker/health-check.sh << 'EOF'
#!/bin/bash
# Netmaker Health Check

echo "=== Netmaker Health Check ==="
echo "Date: $(date)"
echo ""

echo "Docker Services:"
cd /opt/netmaker && docker-compose ps

echo ""
echo "API Health:"
curl -s http://localhost:8080/api/server/health || echo "API not responding"

echo ""
echo "Network Interfaces:"
ip addr show | grep -E "(wg|nm-)"

echo ""
echo "WireGuard Status:"
wg show

echo ""
echo "Firewall Status:"
ufw status
EOF

chmod +x /opt/netmaker/health-check.sh

# Final status check
log "Performing final health check..."
sleep 10
/opt/netmaker/health-check.sh >> $INSTALL_LOG 2>&1

log "=========================================="
log "Netmaker Installation Complete!"
log "=========================================="
log "Access Information:"
log "- Web UI: http://$SERVER_IP:8080"
log "- API: http://$SERVER_IP:8080/api"
log "- Domain: $DOMAIN"
log ""
log "Management Commands:"
log "- Start: /opt/netmaker/manage.sh start"
log "- Stop: /opt/netmaker/manage.sh stop"
log "- Status: /opt/netmaker/manage.sh status"
log "- Health: /opt/netmaker/health-check.sh"
log ""
log "Log file: $INSTALL_LOG"
log "=========================================="

info "Installation completed successfully!"
info "Please configure your DNS to point $DOMAIN to $SERVER_IP"
info "Default admin credentials will be displayed in the logs"
