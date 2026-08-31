.PHONY: test run up down logs

test:
	$(MAKE) up-test-server &&  sleep 5 && \
	uv run --env-file .env pytest $(ARGS) && \
	$(MAKE) down-test-server

up-test-server:
	docker compose --env-file .env.test --profile test up --build -d;

down-test-server:
	docker compose --env-file .env.test --profile test up --build -d;

run:
	uv run --env-file .env server.py;

up:
	docker compose --profile dev up --build -d;

down:
	docker compose --profile dev down;

logs:
	docker compose --profile dev logs -f;
