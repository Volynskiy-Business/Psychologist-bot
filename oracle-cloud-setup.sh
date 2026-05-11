#!/bin/bash
# Oracle Cloud Setup Script for PsySupport AI Bot
# Run this on your Oracle Cloud VPS

set -e

echo "🚀 Setting up PsySupport AI Bot on Oracle Cloud..."

# Update system
echo "📦 Updating system..."
sudo apt update && sudo apt upgrade -y

# Install Docker
echo "🐳 Installing Docker..."
sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Create app directory
mkdir -p ~/psy-support-bot
cd ~/psy-support-bot

# Clone repository
echo "📥 Cloning repository..."
git clone https://github.com/Volynskiy-Business/Psychologist-bot.git .

# Create environment file
echo "⚙️ Creating environment file..."
cat > .env << 'EOF'
# Telegram
BOT_TOKEN=your_telegram_bot_token_here
BOT_DISPLAY_NAME=PsySupport AI

# OpenRouter
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
DEFAULT_MODEL=openrouter/free

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/psybot
REDIS_URL=redis://redis:6379/0

# Admin
ADMIN_TELEGRAM_IDS=

# Privacy
STORE_CONVERSATIONS=false
MESSAGE_RETENTION_DAYS=30
SAFETY_EVENT_RETENTION_DAYS=180

# App
APP_ENV=production
LOG_LEVEL=INFO
EOF

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Edit .env file with your real API keys:"
echo "   nano ~/psy-support-bot/.env"
echo ""
echo "2. Start the bot:"
echo "   cd ~/psy-support-bot"
echo "   docker compose up -d"
echo ""
echo "3. Check logs:"
echo "   docker compose logs -f bot"
echo ""
echo "4. View metrics:"
echo "   http://your-server-ip:9090 (Prometheus)"
echo "   http://your-server-ip:3000 (Grafana, admin/admin)"
echo ""
