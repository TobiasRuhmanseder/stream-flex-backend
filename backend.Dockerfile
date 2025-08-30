# backend.Dockerfile
FROM python:3.12-alpine

LABEL maintainer="you@example.com"
LABEL version="1.0"
LABEL description="Django + Gunicorn on Alpine"

# Empfehlenswerte Runtime-Env
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System-Pakete:
# - runtime: ffmpeg, postgresql-client, libpq (für psycopg)
# - build-deps: build-base, python3-dev, postgresql-dev, libffi-dev, openssl-dev (für Wheels, cryptography, psycopg etc.)
RUN apk update && \
    apk add --no-cache bash ffmpeg postgresql-client libpq && \
    apk add --no-cache --virtual .build-deps \
        build-base python3-dev postgresql-dev libffi-dev openssl-dev && \
    pip install --upgrade pip && \
    true

# Code & requirements rein
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    apk del .build-deps

COPY . .

# entrypoint ausführbar machen
RUN chmod +x backend.entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["./backend.entrypoint.sh"]
