#!/bin/bash
# FreeIPA Identity Server Installation Script
# VM 101 - 192.168.0.101

set -e

echo "🔧 Installing FreeIPA Identity Server..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install FreeIPA server
sudo apt install -y freeipa-server freeipa-server-dns

# Set hostname
sudo hostnamectl set-hostname freeipa.company.local

# Configure /etc/hosts
echo "192.168.0.101 freeipa.company.local freeipa" | sudo tee -a /etc/hosts

# Install FreeIPA server with DNS
sudo ipa-server-install \
    --realm=COMPANY.LOCAL \
    --domain=company.local \
    --ds-password=AdminPassword123! \
    --admin-password=AdminPassword123! \
    --hostname=freeipa.company.local \
    --ip-address=192.168.0.101 \
    --setup-dns \
    --forwarder=1.1.1.1 \
    --forwarder=1.0.0.1 \
    --reverse-zone=0.168.192.in-addr.arpa. \
    --unattended

# Enable and start services
sudo systemctl enable ipa
sudo systemctl start ipa

# Configure firewall
sudo ufw allow 53/tcp
sudo ufw allow 53/udp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 389/tcp
sudo ufw allow 636/tcp
sudo ufw allow 88/tcp
sudo ufw allow 88/udp
sudo ufw allow 464/tcp
sudo ufw allow 464/udp
sudo ufw allow 123/udp

echo "✅ FreeIPA installation completed!"
echo "🌐 Web UI: https://192.168.0.101"
echo "👤 Admin user: admin"
echo "🔑 Admin password: AdminPassword123!"
