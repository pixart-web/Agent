FROM python:3.12-slim

ARG CODEX_CLI_VERSION=0.149.0
ARG PNPM_VERSION=11.9.0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates curl git \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install --no-install-recommends -y nodejs \
    && npm install --global "@openai/codex@${CODEX_CLI_VERSION}" "pnpm@${PNPM_VERSION}" \
    && rm -rf /var/lib/apt/lists/*



WORKDIR /app

COPY apps/api/pyproject.toml .
COPY apps/api/app ./app
COPY apps/api/alembic.ini .
COPY apps/api/alembic ./alembic
RUN pip install --no-cache-dir .

COPY apps/api/tests ./tests
COPY apps/api/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
