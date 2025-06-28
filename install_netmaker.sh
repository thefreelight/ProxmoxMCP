#!/bin/bash

# Netmaker Installation Script for VM 102 (infra-netmaker)
# This script installs Netmaker on Ubuntu 24.04

set -e

echo "🚀 Starting Netmaker Installation..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required packages
echo "🔧 Installing required packages..."
sudo apt install -y curl wget git unzip software-properties-common apt-transport-https ca-certificates gnupg lsb-release

# Install Docker
echo "🐳 Installing Docker..."
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose (standalone)
echo "🔧 Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Start and enable Docker
echo "▶️ Starting Docker service..."
sudo systemctl start docker
sudo systemctl enable docker

# Verify Docker installation
echo "✅ Verifying Docker installation..."
sudo docker --version
sudo docker-compose --version

# Create netmaker directory
echo "📁 Creating Netmaker directory..."
mkdir -p ~/netmaker
cd ~/netmaker

# Download Netmaker quick install script
echo "⬇️ Downloading Netmaker installation script..."
wget -O netmaker-install.sh https://raw.githubusercontent.com/gravitl/netmaker/master/scripts/nm-quick.sh
chmod +x netmaker-install.sh

echo "🎉 Prerequisites installed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Reboot the system to apply Docker group changes"
echo "2. Run the Netmaker installation script with your domain"
echo "3. Configure DNS and firewall settings"
echo ""
echo "💡 Example installation command:"
echo "   ./netmaker-install.sh -d your-domain.com -e your-email@domain.com"
echo ""
echo "🔗 For more information, visit: https://docs.netmaker.io/"
