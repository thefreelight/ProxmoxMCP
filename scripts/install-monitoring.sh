#!/bin/bash
# Monitoring & Backup Installation Script
# VM 110 - 192.168.0.110

set -e

echo "🔧 Installing Monitoring & Backup System..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose and other tools
sudo apt install -y docker-compose rclone

# Create monitoring directory
mkdir -p ~/monitoring
cd ~/monitoring

# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-lifecycle'

  # Grafana
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=GrafanaPass123!
      - GF_DATABASE_TYPE=postgres
      - GF_DATABASE_HOST=192.168.0.106:5432
      - GF_DATABASE_NAME=monitoring
      - GF_DATABASE_USER=monitoring
      - GF_DATABASE_PASSWORD=MonitoringDB123!
      - GF_AUTH_LDAP_ENABLED=true
      - GF_AUTH_LDAP_CONFIG_FILE=/etc/grafana/ldap.toml
    volumes:
      - grafana_data:/var/lib/grafana
      - ./ldap.toml:/etc/grafana/ldap.toml
    depends_on:
      - prometheus

  # Node Exporter
  node-exporter:
    image: prom/node-exporter:latest
    container_name: node-exporter
    restart: unless-stopped
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'

  # AlertManager
  alertmanager:
    image: prom/alertmanager:latest
    container_name: alertmanager
    restart: unless-stopped
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml
      - alertmanager_data:/alertmanager

volumes:
  prometheus_data:
  grafana_data:
  alertmanager_data:
EOF

# Create Prometheus configuration
cat > prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node-exporter'
    static_configs:
      - targets: 
        - '192.168.0.101:9100'  # FreeIPA
        - '192.168.0.102:9100'  # NetBird
        - '192.168.0.103:9100'  # JumpServer
        - '192.168.0.104:9100'  # GitLab
        - '192.168.0.105:9100'  # RustDesk
        - '192.168.0.106:9100'  # Database
        - '192.168.0.107:9100'  # App Server 1
        - '192.168.0.108:9100'  # App Server 2
        - '192.168.0.109:9100'  # Nginx Gateway
        - '192.168.0.110:9100'  # Monitoring
        - '192.168.0.111:9100'  # Dev Environment
        - '192.168.0.112:9100'  # Container Registry

  - job_name: 'postgresql'
    static_configs:
      - targets: ['192.168.0.106:5432']

  - job_name: 'redis'
    static_configs:
      - targets: ['192.168.0.106:6379']
EOF

# Create Grafana LDAP configuration
cat > ldap.toml << 'EOF'
[[servers]]
host = "192.168.0.101"
port = 389
use_ssl = false
start_tls = false
ssl_skip_verify = true
bind_dn = "uid=admin,cn=users,cn=accounts,dc=company,dc=local"
bind_password = "AdminPassword123!"
search_filter = "(uid=%s)"
search_base_dns = ["cn=users,cn=accounts,dc=company,dc=local"]

[servers.attributes]
name = "cn"
surname = "sn"
username = "uid"
member_of = "memberOf"
email = "mail"

[[servers.group_mappings]]
group_dn = "cn=admins,cn=groups,cn=accounts,dc=company,dc=local"
org_role = "Admin"

[[servers.group_mappings]]
group_dn = "cn=users,cn=groups,cn=accounts,dc=company,dc=local"
org_role = "Viewer"
EOF

# Create AlertManager configuration
cat > alertmanager.yml << 'EOF'
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@company.local'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
- name: 'web.hook'
  webhook_configs:
  - url: 'http://127.0.0.1:5001/'
EOF

# Start monitoring services
sudo docker-compose up -d

# Configure firewall
sudo ufw allow 3000/tcp
sudo ufw allow 9090/tcp
sudo ufw allow 9093/tcp
sudo ufw allow 9100/tcp

echo "✅ Monitoring system installation completed!"
echo "📊 Grafana: http://192.168.0.110:3000 (admin/GrafanaPass123!)"
echo "🔍 Prometheus: http://192.168.0.110:9090"
echo "🚨 AlertManager: http://192.168.0.110:9093"
