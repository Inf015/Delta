COMPOSE = docker compose
SERVER  = root@100.80.115.53
SSH     = ssh -i ~/.ssh/franky
APP_DIR = /opt/delta

# ─── Desarrollo (Mac) ────────────────────────────────────────────────────────

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f

logs-api:
	$(COMPOSE) logs -f api

logs-worker:
	$(COMPOSE) logs -f worker

shell-api:
	$(COMPOSE) exec api bash

shell-db:
	$(COMPOSE) exec db psql -U $${POSTGRES_USER:-simtelemetry} -d $${POSTGRES_DB:-simtelemetry}

restart:
	$(COMPOSE) restart

# ─── Base de datos ────────────────────────────────────────────────────────────

migrate:
	$(COMPOSE) exec api alembic upgrade head

migration:
	$(COMPOSE) exec api alembic revision --autogenerate -m "$(msg)"

# ─── Tests ───────────────────────────────────────────────────────────────────

test:
	$(COMPOSE) exec api pytest tests/ -v

# ─── Deploy en franky ────────────────────────────────────────────────────────

deploy:
	git push
	$(SSH) $(SERVER) "cd $(APP_DIR) && git pull && docker compose up -d --build"

deploy-logs:
	$(SSH) $(SERVER) "cd $(APP_DIR) && docker compose logs -f"

server-shell:
	$(SSH) $(SERVER)

server-setup:
	$(SSH) $(SERVER) "git clone https://github.com/Inf015/Delta.git $(APP_DIR) || (cd $(APP_DIR) && git pull)"
	$(SSH) $(SERVER) "cd $(APP_DIR) && cp .env.example .env && echo 'Edita $(APP_DIR)/.env con tus valores reales'"

.PHONY: up down build logs logs-api logs-worker shell-api shell-db restart migrate migration test deploy deploy-logs server-shell server-setup
