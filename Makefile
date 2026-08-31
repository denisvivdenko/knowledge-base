.PHONY: test

test:
	uv run --env-file .env pytest;
