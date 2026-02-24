#!/bin/bash
# Генерация самоподписанного SSL для IP 193.42.127.176
# Запуск: из корня проекта — ./scripts/gen-selfsigned-cert.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CERTS_DIR="$PROJECT_ROOT/certs/selfsigned"
mkdir -p "$CERTS_DIR"
cd "$CERTS_DIR"

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout privkey.pem \
  -out fullchain.pem \
  -subj "/CN=193.42.127.176" \
  -addext "subjectAltName=IP:193.42.127.176"

echo "Сертификаты созданы: $CERTS_DIR"
echo "Дальше: docker compose up -d"
