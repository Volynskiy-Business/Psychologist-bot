# 🤖 PsySupport AI Bot

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![OpenRouter](https://img.shields.io/badge/Powered%20by-OpenRouter-orange)](https://openrouter.ai)
[![CI/CD](https://github.com/Volynskiy-Business/Psychologist-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/Volynskiy-Business/Psychologist-bot/actions)
[![Coverage](https://codecov.io/gh/Volynskiy-Business/Psychologist-bot/branch/main/graph/badge.svg)](https://codecov.io/gh/Volynskiy-Business/Psychologist-bot)
[![Docker](https://img.shields.io/badge/Docker-ready-blue)](docker-compose.yml)
[![Languages](https://img.shields.io/badge/Languages-7-success)](i18n/)

[English](README.md) | **Русский** | [Deutsch](README.de.md) | [Français](README.fr.md) | [Português](README.pt.md) | [Norsk](README.no.md) | [Dansk](README.da.md)

AI-помощник для психологической самопомощи, психообразования и эмоциональной поддержки в Telegram.

## ⚠️ Важно

Этот бот **НЕ является**:
- Врачом или психиатром
- Психотерапевтом
- Кризисной службой
- Инструментом для диагностики

Бот предназначен только для **самопомощи** и **эмоциональной поддержки**.

## ✨ Возможности

- 🗣 **Безопасный диалог** с AI
- 🧠 **CBT/КПТ** упражнения
- 🧘 **Mindfulness** и grounding
- 📊 **Дневник настроения**
- 📋 **План безопасности**
- 🆘 **Кризисная маршрутизация**
- 🤖 **OpenRouter** — бесплатные LLM-модели
- 🌍 **Мультиязычность** — автоопределение языка

## 🚀 Быстрый старт

### 1. Получение API ключей

**Telegram Bot Token:**
1. Напишите [@BotFather](https://t.me/BotFather)
2. Отправьте `/newbot`
3. Скопируйте токен

**OpenRouter API Key:**
1. Зарегистрируйтесь на [openrouter.ai/keys](https://openrouter.ai/keys)
2. Создайте ключ (бесплатно)

### 2. Установка

```bash
git clone https://github.com/vmn2014/Psychologist-bot.git
cd Psychologist-bot

# Создать виртуальное окружение (рекомендуется)
python3 -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt
```

### 3. Настройка

```bash
cp .env.example .env
# Отредактируйте .env, добавив свои ключи
```

### 4. Запуск

```bash
# Локально (с активированным venv)
python -m app.main

# Или через Docker (venv не нужен)
docker-compose up --build
```

## 📁 Структура проекта

```
psy-support-bot/
├── app/
│   ├── main.py              # Точка входа
│   ├── config.py            # Pydantic Settings
│   ├── ai/
│   │   ├── openrouter_client.py
│   │   └── prompts/
│   │       ├── system_prompt.py
│   │       └── safety_classifier_prompt.py
│   ├── bot/handlers/
│   │   ├── start.py         # Согласие + меню
│   │   ├── chat.py          # Безопасный диалог
│   │   ├── mood.py          # Дневник
│   │   └── i18n.py          # Переводы
│   ├── safety/
│   │   ├── crisis_detector.py
│   │   ├── safety_classifier.py
│   │   └── safety_protocols.py
│   ├── db/
│   │   ├── models.py
│   │   └── session.py
│   └── psychology/
├── i18n/                    # Переводы
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

## 🌍 Языки

Бот автоматически определяет язык пользователя из настроек Telegram:

| Язык | Код | Статус |
|------|-----|--------|
| English | `en` | ✅ Полный |
| Русский | `ru` | ✅ Полный |
| Deutsch | `de` | ✅ Полный |
| Français | `fr` | ✅ Полный |
| Español | `es` | 🚧 В планах |
| Português | `pt` | ✅ Полный |
| Norsk | `no` | ✅ Полный |
| Dansk | `da` | ✅ Полный |

## 🛡️ Безопасность

- 5 уровней детекции кризиса
- Автоматическая маршрутизация к живой помощи
- Защита от prompt injection
- Валидация ответов AI
- Не ставит диагнозы
- Не даёт медицинских советов

## 🔒 Приватность

- Явное согласие при `/start`
- Команда `/delete_my_data`
- Минимизация данных
- Шифрование секретов через env

## 📚 Доказательная база

Бот использует подходы, рекомендованные:
- [ВОЗ](https://www.who.int)
- [NICE](https://www.nice.org.uk)
- [SAMHSA](https://www.samhsa.gov)

## 📝 Команды

| Команда | Описание |
|---------|----------|
| `/start` | Начало работы |
| `/mood` | Дневник настроения |
| `/chat` | Свободный разговор |
| `/delete_my_data` | Удалить данные |
| `/privacy` | Политика приватности |

## ⚠️ Ограничения

- Бесплатные модели OpenRouter имеют rate limits
- Бот не заменяет профессиональную помощь
- При кризисе обращайтесь к специалистам

## 🤝 Участие

Приветствуются pull requests! См. [CONTRIBUTING.md](CONTRIBUTING.md).

## 💝 Поддержка

Проект бесплатный, но серверы нет. [Поддержите нас](DONATIONS.md), чтобы бот продолжал работать!

## 🚀 Бесплатный деплой

Разверните в облаке бесплатно — не нужно держать компьютер включённым:
[Руководство по бесплатному деплою](DEPLOYMENT.md)

## 📄 Лицензия

[MIT License](LICENSE) © 2026
