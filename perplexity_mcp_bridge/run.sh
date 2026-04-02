#!/usr/bin/with-contenv bashio
set -euo pipefail

export PYTHONUNBUFFERED=1
cd /app

uvicorn src.main:app --host 0.0.0.0 --port 8099
