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


BUILD_VERSION := $(shell date +'%Y.%-m.%-d')

deploy:
	docker compose build
	docker tag ghcr.io/reportobello/server:latest "ghcr.io/reportobello/server:$(BUILD_VERSION)"
	@echo
	@echo -n "Are you sure you want to deploy? NO [CTRL+C]  YES [Enter] "
	@read
	@echo
	docker push ghcr.io/reportobello/server:latest
	docker push "ghcr.io/reportobello/server:$(BUILD_VERSION)"
