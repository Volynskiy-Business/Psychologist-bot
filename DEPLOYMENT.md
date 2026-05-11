# 🚀 Free Cloud Deployment Guide

Deploy PsySupport AI Bot for **free** in the cloud. No need to keep your computer running 24/7.

## 🥇 Recommended: Oracle Cloud Always Free

**Best for**: Production, 24/7 operation, full control

### What You Get (Free Forever)
- 2 AMD-based Compute VMs (1/8 OCPU, 1 GB RAM each)
- 4 ARM-based Compute VMs (up to 24 GB RAM total)
- 200 GB block storage
- No credit card required

### Setup Instructions

#### Step 1: Create Oracle Cloud Account
1. Go to https://www.oracle.com/cloud/free/
2. Sign up (requires phone verification)
3. Wait for account activation (usually instant)

#### Step 2: Create VM Instance
1. Go to Compute → Instances → Create Instance
2. Name: `psy-support-bot`
3. Image: Ubuntu 22.04
4. Shape: VM.Standard.A1.Flex (ARM)
   - OCPUs: 1
   - Memory: 6 GB (recommended) or 4 GB (minimum)
5. Add SSH key (generate new or upload existing)
6. Create

#### Step 3: Connect and Setup
```bash
# Connect via SSH
ssh ubuntu@YOUR_VM_IP

# Download and run setup script
curl -fsSL https://raw.githubusercontent.com/Volynskiy-Business/Psychologist-bot/main/oracle-cloud-setup.sh | bash

# Edit environment variables
nano ~/psy-support-bot/.env
# Add your real API keys:
# BOT_TOKEN=your_telegram_token
# OPENROUTER_API_KEY=your_openrouter_key

# Start the bot
cd ~/psy-support-bot
docker compose -f docker-compose.oracle.yml up -d

# Check logs
docker compose -f docker-compose.oracle.yml logs -f bot
```

#### Step 4: Enable Monitoring (Optional)
```bash
# Start with Prometheus + Grafana
docker compose -f docker-compose.oracle.yml --profile monitoring up -d

# Access Grafana
# URL: http://YOUR_VM_IP:3000
# Login: admin / admin
```

#### Step 5: Configure Firewall
1. Go to Networking → Virtual Cloud Networks
2. Click your VCN → Security Lists
3. Add Ingress Rules:
   - Port 22 (SSH): 0.0.0.0/0
   - Port 3000 (Grafana): Your IP only
   - Port 9090 (Prometheus): Your IP only
   - Port 8000 (Metrics): Your IP only

### Maintenance
```bash
# Update bot
cd ~/psy-support-bot
git pull
docker compose -f docker-compose.oracle.yml up -d --build

# View logs
docker compose -f docker-compose.oracle.yml logs -f bot

# Backup database
docker compose -f docker-compose.oracle.yml exec postgres pg_dump -U postgres psybot > backup.sql

# Check resources
docker stats
```

---

## 🥈 Alternative: Render (Free Tier)

**Best for**: Quick testing, simple setup

**Limitations**: Sleeps after 15 min inactivity

```bash
# 1. Sign up: https://render.com
# 2. New Web Service → Connect GitHub repo
# 3. Set environment variables in dashboard
# 4. Deploy
```

---

## 🥉 Alternative: Railway

**Best for**: Small projects, easy scaling

**Limitations**: $5/month free credit (may need paid for 24/7)

```bash
# 1. Sign up: https://railway.app
# 2. New Project → Deploy from GitHub
# 3. Add PostgreSQL + Redis plugins
# 4. Set env variables
# 5. Deploy
```

---

## Comparison Table

| Platform | Free Tier | Always On | Resources | Ease | Best For |
|----------|-----------|-----------|-----------|------|----------|
| **Oracle Cloud** | ✅ Forever | ✅ Yes | 4 ARM cores + 24GB | Medium | **Production** |
| Render | ✅ Limited | ❌ Sleeps | 512MB RAM | Easy | Testing |
| Railway | ✅ $5/mo | ⚠️ Maybe | Flexible | Easy | Small projects |
| Fly.io | ✅ 3 VMs | ✅ Yes | Shared CPU | Medium | Global deploy |

---

## Troubleshooting

### Bot not responding
```bash
# Check if container is running
docker ps

# Check logs
docker compose logs bot

# Restart
docker compose restart bot
```

### Database connection error
```bash
# Check PostgreSQL
docker compose logs postgres

# Reset database (WARNING: data loss)
docker compose down -v
docker compose up -d
```

### Out of memory
```bash
# Check memory usage
free -h

# Reduce memory limits in docker-compose.oracle.yml
# Or upgrade to paid tier
```

---

## Need Help?

- Open an issue: https://github.com/Volynskiy-Business/Psychologist-bot/issues
- Telegram: @psy_support_bot

---

*Deploy for free, help people for free! 🌍*
