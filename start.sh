#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

mkdir -p /run/mysqld data
if [ -d /var/lib/mysql ] && command -v mysqld >/dev/null 2>&1; then
  chown mysql:mysql /run/mysqld 2>/dev/null || true
  if ! mysqladmin --socket=/run/mysqld/mysqld.sock ping >/dev/null 2>&1; then
    mysqld --user=mysql --datadir=/var/lib/mysql \
      --socket=/run/mysqld/mysqld.sock \
      --pid-file=/run/mysqld/mysqld.pid \
      --bind-address=127.0.0.1 --port=3306 >/tmp/mysqld.log 2>&1 &
    for i in $(seq 1 20); do
      mysqladmin --socket=/run/mysqld/mysqld.sock ping >/dev/null 2>&1 && break
      sleep 0.5
    done
  fi
fi

export PORT="${PORT:-8080}"
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi
exec python3 app.py
