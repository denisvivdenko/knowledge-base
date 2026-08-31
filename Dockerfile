FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY server.py ./

RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:${PATH}"

CMD ["uv", "run", "server.py"]
