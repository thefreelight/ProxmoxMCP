#!/bin/bash
# Database Cluster Installation Script
# VM 106 - 192.168.0.106

set -e

echo "🔧 Installing Database Cluster (PostgreSQL + Redis)..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install -y docker-compose

# Create database directory
mkdir -p ~/database
cd ~/database

# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  # PostgreSQL Database
  postgresql:
    image: postgres:15-alpine
    container_name: postgresql
    restart: unless-stopped
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: postgres
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: PostgresPass123!
    volumes:
      - postgresql_data:/var/lib/postgresql/data
      - ./init-databases.sql:/docker-entrypoint-initdb.d/init-databases.sql
    command: >
      postgres
      -c max_connections=200
      -c shared_buffers=256MB
      -c effective_cache_size=1GB
      -c maintenance_work_mem=64MB
      -c checkpoint_completion_target=0.9
      -c wal_buffers=16MB
      -c default_statistics_target=100

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    command: redis-server --requirepass RedisPass123! --maxmemory 2gb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data

  # pgAdmin for database management
  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: pgadmin
    restart: unless-stopped
    ports:
      - "8080:80"
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@company.local
      PGADMIN_DEFAULT_PASSWORD: PgAdminPass123!
    volumes:
      - pgadmin_data:/var/lib/pgadmin
    depends_on:
      - postgresql

volumes:
  postgresql_data:
  redis_data:
  pgadmin_data:
EOF

# Create database initialization script
cat > init-databases.sql << 'EOF'
-- Create databases for different services
CREATE DATABASE freeipa;
CREATE DATABASE jumpserver;
CREATE DATABASE gitlab;
CREATE DATABASE monitoring;

-- Create users for different services
CREATE USER freeipa WITH PASSWORD 'FreeIpaDB123!';
CREATE USER jumpserver WITH PASSWORD 'JumpServerDB123!';
CREATE USER gitlab WITH PASSWORD 'GitLabDB123!';
CREATE USER monitoring WITH PASSWORD 'MonitoringDB123!';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE freeipa TO freeipa;
GRANT ALL PRIVILEGES ON DATABASE jumpserver TO jumpserver;
GRANT ALL PRIVILEGES ON DATABASE gitlab TO gitlab;
GRANT ALL PRIVILEGES ON DATABASE monitoring TO monitoring;

-- Create extensions
\c gitlab;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gist;

\c monitoring;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
EOF

# Start database services
sudo docker-compose up -d

# Configure firewall
sudo ufw allow 5432/tcp
sudo ufw allow 6379/tcp
sudo ufw allow 8080/tcp

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 30

# Test database connections
echo "🧪 Testing database connections..."
sudo docker exec postgresql psql -U postgres -c "SELECT version();"
sudo docker exec redis redis-cli -a RedisPass123! ping

echo "✅ Database cluster installation completed!"
echo "🐘 PostgreSQL: 192.168.0.106:5432"
echo "🔴 Redis: 192.168.0.106:6379"
echo "🌐 pgAdmin: http://192.168.0.106:8080"
echo "👤 pgAdmin login: admin@company.local / PgAdminPass123!"
echo ""
echo "📋 Database credentials:"
echo "  - postgres: PostgresPass123!"
echo "  - freeipa: FreeIpaDB123!"
echo "  - jumpserver: JumpServerDB123!"
echo "  - gitlab: GitLabDB123!"
echo "  - monitoring: MonitoringDB123!"
echo "  - redis: RedisPass123!"
