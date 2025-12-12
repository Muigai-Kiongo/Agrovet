#!/bin/sh
set -e

# Entrypoint: wait for Postgres, optionally load .env, run migrations & collectstatic, then exec CMD.
# This version is defensive: it won't exit if .env is missing and prints helpful debug info.

APP_DIR="/app"
ENV_FILE="${APP_DIR}/.env"

# Print basic context for debugging
echo "Entrypoint starting. PWD=$(pwd) APP_DIR=${APP_DIR}"
echo "Listing ${APP_DIR}:"
ls -la "${APP_DIR}" || true

# Load environment variables from .env if present (for local dev inside container)
if [ -f "${ENV_FILE}" ]; then
  echo "Sourcing ${ENV_FILE}"
  # set -o allexport / set +o allexport is not supported in /bin/sh on some minimal shells,
  # but POSIX sh supports 'set -a' / 'set +a' instead.
  set -a
  # Source the file safely, but don't let a single malformed line break the whole script
  # (use '|| true' so 'set -e' doesn't abort).
  . "${ENV_FILE}" || true
  set +a
else
  echo "No ${ENV_FILE} found, skipping environment load"
fi

# Wait for Postgres to be ready (simple loop using nc)
POSTGRES_HOST=${POSTGRES_HOST:-db}
POSTGRES_PORT=${POSTGRES_PORT:-5432}

echo "Waiting for Postgres to be ready at ${POSTGRES_HOST}:${POSTGRES_PORT}..."
# loop until nc succeeds; print a dot every second for feedback
count=0
while ! nc -z ${POSTGRES_HOST} ${POSTGRES_PORT}; do
  count=$((count+1))
  if [ $((count % 10)) -eq 0 ]; then
    echo "Still waiting for Postgres after ${count} attempts..."
    echo "Network info:"
    ip addr || true
  fi
  sleep 0.5
done
echo "Postgres is up - continuing"

# Run migrations and collectstatic (fail if these commands error)
echo "Running Django migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Finally exec the container CMD (gunicorn or any provided command)
echo "Starting command: $@"
exec "$@"