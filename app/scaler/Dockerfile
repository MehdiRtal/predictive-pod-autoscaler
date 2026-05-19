FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY src/ ./src/

RUN groupadd -g 1000 appgroup && \
    useradd -m -u 1000 -g appgroup appuser && \
    chown -R appuser:appgroup /app

USER 1000

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "-m", "src.main"]
