#!/bin/bash
# GitLab Platform Installation Script
# VM 104 - 192.168.0.104

set -e

echo "🔧 Installing GitLab Platform..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y curl openssh-server ca-certificates tzdata perl

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install -y docker-compose

# Create GitLab directory
mkdir -p ~/gitlab
cd ~/gitlab

# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  gitlab:
    image: gitlab/gitlab-ee:latest
    container_name: gitlab
    restart: unless-stopped
    hostname: 'gitlab.company.local'
    ports:
      - '80:80'
      - '443:443'
      - '22:22'
    volumes:
      - gitlab_config:/etc/gitlab
      - gitlab_logs:/var/log/gitlab
      - gitlab_data:/var/opt/gitlab
    environment:
      GITLAB_OMNIBUS_CONFIG: |
        external_url 'https://gitlab.company.local'
        
        # Database configuration (external PostgreSQL)
        postgresql['enable'] = false
        gitlab_rails['db_adapter'] = 'postgresql'
        gitlab_rails['db_encoding'] = 'unicode'
        gitlab_rails['db_host'] = '192.168.0.106'
        gitlab_rails['db_port'] = 5432
        gitlab_rails['db_database'] = 'gitlab'
        gitlab_rails['db_username'] = 'gitlab'
        gitlab_rails['db_password'] = 'GitLabDB123!'
        
        # Redis configuration (external)
        redis['enable'] = false
        gitlab_rails['redis_host'] = '192.168.0.106'
        gitlab_rails['redis_port'] = 6379
        gitlab_rails['redis_password'] = 'RedisPass123!'
        
        # LDAP configuration (FreeIPA)
        gitlab_rails['ldap_enabled'] = true
        gitlab_rails['ldap_servers'] = YAML.load <<-'EOS'
          main:
            label: 'FreeIPA'
            host: '192.168.0.101'
            port: 389
            uid: 'uid'
            bind_dn: 'uid=admin,cn=users,cn=accounts,dc=company,dc=local'
            password: 'AdminPassword123!'
            encryption: 'plain'
            verify_certificates: false
            active_directory: false
            allow_username_or_email_login: true
            lowercase_usernames: false
            block_auto_created_users: false
            base: 'cn=users,cn=accounts,dc=company,dc=local'
            user_filter: ''
            attributes:
              username: ['uid', 'userid', 'sAMAccountName']
              email: ['mail', 'email', 'userPrincipalName']
              name: 'cn'
              first_name: 'givenName'
              last_name: 'sn'
        EOS
        
        # Container Registry
        registry_external_url 'https://registry.company.local'
        gitlab_rails['registry_enabled'] = true
        
        # CI/CD Configuration
        gitlab_ci['gitlab_ci_all_broken_builds'] = true
        gitlab_ci['gitlab_ci_add_pusher'] = true
        
        # Backup configuration
        gitlab_rails['backup_keep_time'] = 604800
        gitlab_rails['backup_path'] = "/var/opt/gitlab/backups"
        
        # Performance tuning
        unicorn['worker_processes'] = 4
        sidekiq['max_concurrency'] = 25

volumes:
  gitlab_config:
  gitlab_logs:
  gitlab_data:
EOF

# Start GitLab
sudo docker-compose up -d

# Configure firewall
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp

echo "✅ GitLab installation started!"
echo "🌐 Web UI: https://192.168.0.104"
echo "📦 Registry: https://registry.company.local"
echo "⏳ GitLab is starting up, this may take 5-10 minutes..."
echo "🔑 Get initial root password with: sudo docker exec -it gitlab grep 'Password:' /etc/gitlab/initial_root_password"
