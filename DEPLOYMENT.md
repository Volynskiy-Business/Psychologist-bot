# 🚀 Free Cloud Deployment Guide

Deploy PsySupport AI Bot for **free** in the cloud. No need to keep your computer running 24/7.

## Recommended Free Options

### 1. 🥇 Oracle Cloud (Always Free) — BEST
**Resources:** 2 AMD instances + 4 ARM cores + 24GB RAM + 200GB storage

```bash
# 1. Sign up: https://www.oracle.com/cloud/free/
# 2. Create VM: Ubuntu 22.04, 1 OCPU, 1GB RAM
# 3. Connect via SSH
# 4. Install Docker
sudo apt update && sudo apt install -y docker.io docker-compose

# 5. Clone and run
git clone https://github.com/Volynskiy-Business/Psychologist-bot.git
cd Psychologist-bot
cp .env.example .env
# Edit .env with your keys
sudo docker-compose up -d
```

**Pros:**
- ✅ Truly free forever
- ✅ Powerful (up to 4 ARM cores)
- ✅ No credit card needed
- ✅ Custom domain support

**Cons:**
- ⚠️ Requires verification
- ⚠️ Account may be reviewed

---

### 2. 🥈 Render (Free Tier)
**Resources:** Web service + PostgreSQL

```bash
# 1. Sign up: https://render.com
# 2. Create Web Service
# 3. Connect GitHub repo
# 4. Set environment variables
# 5. Deploy
```

**Pros:**
- ✅ Simplest setup
- ✅ Auto-deploy from GitHub
- ✅ Free PostgreSQL
- ✅ HTTPS included

**Cons:**
- ⚠️ Sleeps after 15 min inactivity
- ⚠️ Limited resources

---

### 3. 🥉 Railway
**Resources:** $5/month free credit

```bash
# 1. Sign up: https://railway.app
# 2. New Project → Deploy from GitHub
# 3. Add PostgreSQL + Redis
# 4. Set env variables
# 5. Deploy
```

**Pros:**
- ✅ Easy to use
- ✅ Good for testing
- ✅ Auto-scaling

**Cons:**
- ⚠️ $5/month limit (may need paid)
- ⚠️ Sleep mode possible

---

### 4. Fly.io (Free Tier)
**Resources:** 3 shared-cpu-1x VMs

```bash
# 1. Install flyctl
curl -L https://fly.io/install.sh | sh

# 2. Sign up: fly auth signup
# 3. Launch: fly launch
# 4. Set secrets: fly secrets set BOT_TOKEN=xxx OPENROUTER_API_KEY=xxx
# 5. Deploy: fly deploy
```

**Pros:**
- ✅ Generous free tier
- ✅ Global CDN
- ✅ Easy CLI

**Cons:**
- ⚠️ Requires credit card (not charged)
- ⚠️ Limited resources

---

### 5. Google Cloud Run (Free Tier)
**Resources:** 2 million requests/month

```bash
# 1. Sign up: https://cloud.google.com/free
# 2. Enable Cloud Run API
# 3. Deploy container
gcloud run deploy psy-support-bot \
  --source . \
  --set-env-vars BOT_TOKEN=xxx,OPENROUTER_API_KEY=xxx
```

**Pros:**
- ✅ Serverless (pay per use)
- ✅ Auto-scaling
- ✅ Generous free tier

**Cons:**
- ⚠️ Complex setup
- ⚠️ Requires GCP knowledge

---

## Comparison Table

| Platform | Free Tier | Always On | Ease | Best For |
|----------|-----------|-----------|------|----------|
| Oracle Cloud | ✅ Forever | ✅ Yes | Medium | Production |
| Render | ✅ Limited | ❌ Sleeps | Easy | Testing |
| Railway | ✅ $5/mo | ⚠️ Maybe | Easy | Small projects |
| Fly.io | ✅ 3 VMs | ✅ Yes | Easy | Global deploy |
| GCP Run | ✅ 2M req | ✅ Yes | Hard | Serverless |

## Quick Start (Recommended)

**For beginners:** Render or Railway
**For production:** Oracle Cloud
**For global reach:** Fly.io

## Monitoring

All platforms support:
- Logs viewing
- Health checks
- Auto-restart
- Alerts

## Need Help?

Open an issue: https://github.com/Volynskiy-Business/Psychologist-bot/issues

---

*Deploy for free, help people for free! 🌍*
