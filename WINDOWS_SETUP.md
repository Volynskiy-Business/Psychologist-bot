# 🪟 Windows Setup Guide

## Шаг 1: Установка необходимых программ

### 1.1 Установи Python
1. Скачай: https://python.org/downloads
2. При установке поставь галочку **"Add Python to PATH"**
3. Проверь: `python --version`

### 1.2 Установи Docker Desktop
1. Скачай: https://www.docker.com/products/docker-desktop
2. Установи и перезагрузи компьютер
3. Проверь: `docker --version`

### 1.3 Установи Git
1. Скачай: https://git-scm.com/download/win
2. Установи с настройками по умолчанию
3. Проверь: `git --version`

## Шаг 2: Скачай проект

```powershell
# Создай папку
mkdir C:\Projects
cd C:\Projects

# Клонируй репозиторий
git clone https://github.com/Volynskiy-Business/Psychologist-bot.git
cd Psychologist-bot
```

## Шаг 3: Настройка

```powershell
# Создай .env файл (через Notepad)
notepad .env
```

Вставь в файл:
```env
BOT_TOKEN=your_telegram_bot_token_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
DATABASE_URL=sqlite:///./data/psybot.db
REDIS_URL=redis://localhost:6379/0
STORE_CONVERSATIONS=false
```

## Шаг 4: Запуск (2 варианта)

### Вариант A: Через Docker (проще)

```powershell
# Запусти Docker Desktop (должен быть запущен!)

# В PowerShell:
docker compose up -d
```

### Вариант B: Локально (без Docker)

```powershell
# Создай виртуальное окружение
python -m venv venv

# Активируй
.\venv\Scripts\activate

# Установи зависимости
pip install -r requirements.txt

# Запусти
python -m app.main
```

## Шаг 5: Проверка

Открой Telegram и напиши своему боту `/start`

## Проблемы?

### "docker не найден"
→ Перезагрузи компьютер после установки Docker

### "pip не найден"
→ Переустанови Python с галочкой "Add to PATH"

### "Module not found"
→ Убедись, что активировал venv: `.\venv\Scripts\activate`
