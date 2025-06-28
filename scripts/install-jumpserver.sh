#!/bin/bash
# JumpServer Operations Installation Script
# VM 103 - 192.168.0.103

set -e

echo "🔧 Installing JumpServer Operations Platform..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install -y docker-compose

# Create JumpServer directory
mkdir -p ~/jumpserver
cd ~/jumpserver

# Generate secret key and bootstrap token
SECRET_KEY=$(openssl rand -base64 32)
BOOTSTRAP_TOKEN=$(openssl rand -base64 32)

# Create environment file
cat > .env << EOF
# JumpServer Configuration
SECRET_KEY=${SECRET_KEY}
BOOTSTRAP_TOKEN=${BOOTSTRAP_TOKEN}
DB_ENGINE=postgresql
DB_HOST=192.168.0.106
DB_PORT=5432
DB_USER=jumpserver
DB_PASSWORD=JumpServerDB123!
DB_NAME=jumpserver
REDIS_HOST=192.168.0.106
REDIS_PORT=6379
REDIS_PASSWORD=RedisPass123!

# Network Configuration
HTTP_BIND_HOST=0.0.0.0
HTTP_LISTEN_PORT=80
HTTPS_LISTEN_PORT=443
WS_LISTEN_PORT=2222

# LDAP Integration (FreeIPA)
AUTH_LDAP=true
AUTH_LDAP_SERVER_URI=ldap://192.168.0.101:389
AUTH_LDAP_BIND_DN=uid=admin,cn=users,cn=accounts,dc=company,dc=local
AUTH_LDAP_BIND_PASSWORD=AdminPassword123!
AUTH_LDAP_SEARCH_OU=cn=users,cn=accounts,dc=company,dc=local
AUTH_LDAP_SEARCH_FILTER=(uid=%(user)s)
AUTH_LDAP_USER_ATTR_MAP={"username": "uid", "name": "cn", "email": "mail"}

# Session Configuration
SESSION_COOKIE_AGE=86400
SESSION_EXPIRE_AT_BROWSER_CLOSE=true
EOF

# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  jumpserver:
    image: jumpserver/jms_all:latest
    container_name: jumpserver
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "2222:2222"
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - BOOTSTRAP_TOKEN=${BOOTSTRAP_TOKEN}
      - DB_ENGINE=${DB_ENGINE}
      - DB_HOST=${DB_HOST}
      - DB_PORT=${DB_PORT}
      - DB_USER=${DB_USER}
      - DB_PASSWORD=${DB_PASSWORD}
      - DB_NAME=${DB_NAME}
      - REDIS_HOST=${REDIS_HOST}
      - REDIS_PORT=${REDIS_PORT}
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    volumes:
      - jumpserver_data:/opt/jumpserver/data
      - jumpserver_logs:/opt/jumpserver/logs
    depends_on:
      - redis-local
    env_file:
      - .env

  # Local Redis for session storage
  redis-local:
    image: redis:7-alpine
    container_name: jumpserver-redis
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data

volumes:
  jumpserver_data:
  jumpserver_logs:
  redis_data:
EOF

# Start JumpServer
sudo docker-compose up -d

# Configure firewall
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 2222/tcp

echo "✅ JumpServer installation completed!"
echo "🌐 Web UI: https://192.168.0.103"
echo "👤 Default admin: admin"
echo "🔑 Bootstrap token: ${BOOTSTRAP_TOKEN}"
echo "📝 Please save the bootstrap token for initial setup!"
