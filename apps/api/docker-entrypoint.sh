#!/bin/sh
set -eu

echo "Applying database migrations..."
alembic upgrade head

echo "Seeding initial agents..."
python -m app.scripts.seed_agents

echo "Starting Agent API..."
exec "$@"
