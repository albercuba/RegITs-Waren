#!/bin/sh
set -e

mkdir -p /app/data /app/uploads
chown -R regits:regits /app/data /app/uploads

exec gosu regits "$@"
