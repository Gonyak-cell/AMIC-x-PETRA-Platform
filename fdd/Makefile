.PHONY: up down logs test migrate seed prod-up prod-down prod-logs prod-status prod-backup e2e-assets

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

# Backend
test:
	cd backend && python -m pytest -v

migrate:
	cd backend && alembic upgrade head

migrate-gen:
	cd backend && alembic revision --autogenerate -m "$(msg)"

# Frontend
dev-frontend:
	cd frontend && npm run dev

# PPTX Service
dev-pptx:
	cd pptx-service && npm run dev

# ── Production ─────────────────────────────────
prod-up:
	bash scripts/deploy.sh up

prod-down:
	bash scripts/deploy.sh down

prod-logs:
	bash scripts/deploy.sh logs

prod-status:
	bash scripts/deploy.sh status

prod-backup:
	bash scripts/deploy.sh backup

# ── E2E ────────────────────────────────────────
e2e-assets:
	python scripts/generate_e2e_assets.py
