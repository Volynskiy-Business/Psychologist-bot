# 🤖 PsySupport AI Bot

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![OpenRouter](https://img.shields.io/badge/Powered%20by-OpenRouter-orange)](https://openrouter.ai)
[![CI/CD](https://github.com/Volynskiy-Business/Psychologist-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/Volynskiy-Business/Psychologist-bot/actions)
[![Coverage](https://codecov.io/gh/Volynskiy-Business/Psychologist-bot/branch/main/graph/badge.svg)](https://codecov.io/gh/Volynskiy-Business/Psychologist-bot)
[![Docker](https://img.shields.io/badge/Docker-ready-blue)](docker-compose.yml)
[![Languages](https://img.shields.io/badge/Languages-7-success)](i18n/)

**English** | [Русский](README.ru.md) | [Deutsch](README.de.md) | [Français](README.fr.md) | [Português](README.pt.md) | [Norsk](README.no.md) | [Dansk](README.da.md)

AI assistant for psychological self-help, psychoeducation and emotional support in Telegram.

## ⚠️ Important

This bot **is NOT**:
- A doctor or psychiatrist
- A psychotherapist
- A crisis service
- A diagnostic tool

The bot is designed for **self-help** and **emotional support** only.

## ✨ Features

- 🗣 **Safe dialogue** with AI
- 🧠 **CBT** exercises
- 🧘 **Mindfulness** and grounding
- 📊 **Mood diary**
- 📋 **Safety plan**
- 🆘 **Crisis routing**
- 🤖 **OpenRouter** — free LLM models
- 🌍 **Multilingual** — auto language detection

## 🚀 Quick Start

### 1. Get API Keys

**Telegram Bot Token:**
1. Message [@BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Copy the token

**OpenRouter API Key:**
1. Sign up at [openrouter.ai/keys](https://openrouter.ai/keys)
2. Create a key (free)

### 2. Installation

```bash
git clone https://github.com/vmn2014/Psychologist-bot.git
cd Psychologist-bot

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

```bash
cp .env.example .env
# Edit .env, add your keys
```

### 4. Run

```bash
# Local (with activated venv)
python -m app.main

# Or with Docker (no venv needed)
docker-compose up --build
```

## 📁 Project Structure

```
psy-support-bot/
├── app/
│   ├── main.py              # Entry point
│   ├── config.py            # Pydantic Settings
│   ├── ai/
│   │   ├── openrouter_client.py
│   │   └── prompts/
│   │       ├── system_prompt.py
│   │       └── safety_classifier_prompt.py
│   ├── bot/handlers/
│   │   ├── start.py         # Consent + menu
│   │   ├── chat.py          # Safe dialogue
│   │   ├── mood.py          # Mood diary
│   │   └── i18n.py          # Translations
│   ├── safety/
│   │   ├── crisis_detector.py
│   │   ├── safety_classifier.py
│   │   └── safety_protocols.py
│   ├── db/
│   │   ├── models.py
│   │   └── session.py
│   └── psychology/
├── i18n/                    # Translations
│   ├── en.json
│   ├── ru.json
│   ├── de.json
│   └── fr.json
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

## 🌍 Languages

The bot automatically detects the user's language from Telegram settings:

| Language | Code | Status |
|----------|------|--------|
| English | `en` | ✅ Full |
| Русский | `ru` | ✅ Full |
| Deutsch | `de` | ✅ Full |
| Français | `fr` | ✅ Full |
| Español | `es` | 🚧 Planned |
| Português | `pt` | ✅ Full |
| Norsk | `no` | ✅ Full |
| Dansk | `da` | ✅ Full |

## 🛡️ Safety

- 5-level crisis detection
- Automatic routing to live help
- Prompt injection protection
- AI response validation
- No diagnoses
- No medical advice

## 🔒 Privacy

- Explicit consent at `/start`
- `/delete_my_data` command
- Data minimization
- Encrypted secrets via env

## 📚 Evidence Base

The bot uses approaches recommended by:
- [WHO](https://www.who.int)
- [NICE](https://www.nice.org.uk)
- [SAMHSA](https://www.samhsa.gov)

## 📝 Commands

| Command | Description |
|---------|-------------|
| `/start` | Start |
| `/mood` | Mood diary |
| `/chat` | Free chat |
| `/delete_my_data` | Delete data |
| `/privacy` | Privacy policy |

## ⚠️ Limitations

- Free OpenRouter models have rate limits
- Bot does not replace professional help
- In crisis, contact specialists

## 🤝 Contributing

Pull requests welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## 💝 Support

This project is free, but servers aren't. [Support us](DONATIONS.md) to keep the bot running!

## 🚀 Deploy for Free

Deploy in the cloud for free — no need to keep your PC running:
[Free Deployment Guide](DEPLOYMENT.md)

## 📄 License

[MIT License](LICENSE) © 2026
