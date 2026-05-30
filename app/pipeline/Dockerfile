FROM ghcr.io/astral-sh/uv:python3.14-trixie

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY src/ ./src/

ENV PATH="/app/.venv/bin:$PATH"
