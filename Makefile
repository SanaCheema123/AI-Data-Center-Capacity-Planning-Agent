SHELL := /bin/bash

.PHONY: up down logs test backend-test frontend-test lint

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

backend-test:
	cd backend && pytest

frontend-test:
	cd frontend && npm test -- --run

test: backend-test frontend-test
