#!/bin/sh
set -e

mkdir -p /app/storage/images /home/appuser/.insightface/models
chown -R appuser:appuser /app/storage/images /home/appuser/.insightface

su appuser -c "python -m alembic upgrade head"

exec su appuser -c "$*"
