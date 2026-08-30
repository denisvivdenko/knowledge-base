.PHONY: test

test:
	@if [ -f .env ]; then \
		uv run --env-file .env pytest; \
	else \
		uv run pytest; \
	fi
