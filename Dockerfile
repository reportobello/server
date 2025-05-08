# syntax=docker.io/docker/dockerfile:1.7-labs

FROM alpine:3.21 AS docs

RUN apk add --no-cache mdbook

COPY docs /docs

RUN cd /docs && mdbook build


FROM node:24-alpine3.21 AS npm

WORKDIR /app
COPY www/package.json www/package-lock.json /app/

RUN npm i


FROM python:3.12.10-alpine3.21

RUN apk update \
	&& apk upgrade \
	&& apk add --no-cache \
		typst \
		docker-cli \
		font-noto \
		font-noto-cjk \
		font-jis-misc \
		font-jetbrains-mono \
		font-dejavu \
		font-liberation \
		font-ibm-type1 \
		font-roboto \
		uv \
	&& fc-cache \
	&& adduser -D -u 1000 reportobello \
	&& addgroup -g 971 docker \
	&& addgroup reportobello docker \
	&& rm -rf /var/cache/apk/*

USER reportobello

WORKDIR /app
VOLUME /app/data
VOLUME /app/logs

RUN mkdir -p /app/data/artifacts/files /app/data/artifacts/pdfs /app/logs

COPY --chown=reportobello:reportobello pyproject.toml uv.lock ./
RUN uv sync --no-cache

COPY --chown=reportobello:reportobello --parents main.py reportobello scripts www ./
COPY --chown=reportobello:reportobello --from=docs /docs/book /app/www/docs

# TODO: actually add an NPM build/bundle step here
COPY --chown=reportobello:reportobello --from=npm /app/node_modules/monaco-editor/min/vs /app/www/node_modules/monaco-editor/min/vs
COPY --chown=reportobello:reportobello --from=npm /app/node_modules/reportobello/dist /app/www/node_modules/reportobello/dist
COPY --chown=reportobello:reportobello --from=npm /app/node_modules/htmx.org/dist/htmx.min.js /app/www/node_modules/htmx.org/dist/
COPY --chown=reportobello:reportobello --from=npm /app/node_modules/typer-dot-js/typer.js /app/www/node_modules/typer-dot-js/

COPY typst /home/reportobello/.local/share/typst/

ENTRYPOINT [ "python3", "-m", "reportobello" ]

ENV REPORTOBELLO_ARTIFACT_DIR=/app/data/artifacts \
	REPORTOBELLO_DB=/app/data/db.db3 \
	REPORTOBELLO_DOMAIN=localhost:8000 \
	TYPST_FONT_PATHS=/usr/share/fonts \
	PATH="/app/reportobello/scripts:$PATH"

LABEL org.opencontainers.image.source=https://github.com/reportobello/server
