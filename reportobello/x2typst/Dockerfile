FROM python:3.12.7-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update \
	&& apt upgrade -y \
	&& apt install fontconfig -y \
	&& adduser --disabled-password -u 1000 x2typst \
	&& rm -rf /var/lib/apt/lists/* \
	&& fc-cache

USER x2typst

WORKDIR /app

COPY --chown=x2typst:x2typst requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=x2typst:x2typst . x2typst

ENTRYPOINT [ "python3", "-m", "x2typst" ]

# TODO: move to its own repo?
LABEL org.opencontainers.image.source=https://github.com/reportobello/server
