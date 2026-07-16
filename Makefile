# Iran Carbon Black — common developer commands (PowerShell-friendly via make if installed)

.PHONY: env up down build logs ps health seed

env:
	@if not exist .env copy .env.example .env

up: env
	docker compose up -d --build

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f --tail=100

ps:
	docker compose ps

health:
	curl -s http://localhost:8080/health
	curl -s http://localhost:8001/health
	curl -s http://localhost:8003/health

seed:
	python scripts/seed_synthetic.py --base-url http://localhost:8080
