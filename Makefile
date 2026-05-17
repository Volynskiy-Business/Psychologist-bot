.PHONY: restart-bot deploy-bot logs logs-talk shell test lint

# Code-only change: volume-mounted app — no rebuild needed
restart-bot:
	docker compose restart bot

# Dependency change (requirements.txt / Dockerfile): full rebuild + recreate
deploy-bot:
	docker compose build bot
	docker compose up -d --force-recreate --no-deps bot

# First-time full stack bring-up (or after OS reboot)
up:
	docker compose up -d

# Tear down all managed services (volumes preserved)
down:
	docker compose down

logs:
	docker compose logs -f --tail=200 bot

# Friendly/Talk mode log stream (filter to relevant stages)
logs-talk:
	docker compose logs -f bot 2>&1 | grep -E "stage=friendly|stage=talk|friendly_mode|talk_human|talk_repair"

shell:
	docker compose exec bot bash

test:
	wsl -d Ubuntu-24.04-Compacted -- bash -lc "cd /opt/projects/psysupport && .venv/bin/python3 -m pytest tests/ -x -q"

lint:
	wsl -d Ubuntu-24.04-Compacted -- bash -lc "cd /opt/projects/psysupport && .venv/bin/python3 -m ruff check app/ tests/"
