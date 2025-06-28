#!/bin/bash

# Quick Netmaker Installation for VM 102
# Run this script on the VM directly

echo "🚀 Netmaker Quick Installation Starting..."

# Update and install Docker
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Create netmaker directory
mkdir -p ~/netmaker
cd ~/netmaker

# Download and run Netmaker quick install
wget -O nm-quick.sh https://raw.githubusercontent.com/gravitl/netmaker/master/scripts/nm-quick.sh
chmod +x nm-quick.sh

echo "✅ Docker installed. Ready for Netmaker installation."
echo "💡 Next: Run './nm-quick.sh -d <your-domain>' to install Netmaker"
