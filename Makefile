.PHONY: ruff test

all: ruff mypy test

test:
	uv run pytest

ruff:
	uv run ruff check reportobello test

mypy:
	uv run mypy reportobello test

fmt:
	uv run ruff check reportobello test --fix
