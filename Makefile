.PHONY: test run up down logs

test:
	uv run --env-file .env pytest;

run:
	uv run --env-file .env server.py;

up:
	docker compose up --build -d;

down:
	docker compose down;

logs:
	docker compose logs -f;
