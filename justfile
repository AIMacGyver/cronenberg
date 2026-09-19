set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

default: check

sync:
    uv sync

lint:
    uv run ruff check .

format:
    uv run ruff format .

test:
    uv run pytest

check: lint test
