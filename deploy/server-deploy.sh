#!/usr/bin/env bash
set -Eeuo pipefail

APP_ROOT=/opt/sln-wms
RELEASE_ARCHIVE=/tmp/sln-wms-release.tar.gz
APP_USER=slnwms
DB_NAME=sln_warehouse
DB_USER=slnwms

log() { printf '\n[%s] %s\n' "$(date '+%F %T')" "$*"; }

if [[ $EUID -ne 0 ]]; then
  echo "Run this script with sudo." >&2
  exit 1
fi

log "Installing system packages"
dnf install -y python3.12 python3.12-pip postgresql17-server nginx tar gzip libgomp

if ! id "$APP_USER" >/dev/null 2>&1; then
  useradd --system --home-dir "$APP_ROOT" --shell /sbin/nologin "$APP_USER"
fi

# A small swap file prevents dependency installation and report generation from
# being killed by the OOM killer on a 1 GiB EC2 instance.
if ! swapon --show=NAME --noheadings | grep -qx /swapfile; then
  log "Creating 2 GiB swap file"
  if [[ ! -f /swapfile ]]; then
    dd if=/dev/zero of=/swapfile bs=1M count=2048 status=none
    chmod 600 /swapfile
    mkswap /swapfile >/dev/null
  fi
  swapon /swapfile
  grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

if [[ ! -s /var/lib/pgsql/data/PG_VERSION ]]; then
  log "Initializing PostgreSQL"
  postgresql-setup --initdb
fi
systemctl enable --now postgresql

# Amazon Linux defaults loopback TCP connections to ident authentication,
# while the application uses a generated database password.
sed -Ei 's/^(host[[:space:]]+all[[:space:]]+all[[:space:]]+127\.0\.0\.1\/32[[:space:]]+)ident$/\1scram-sha-256/' /var/lib/pgsql/data/pg_hba.conf
sed -Ei 's/^(host[[:space:]]+all[[:space:]]+all[[:space:]]+::1\/128[[:space:]]+)ident$/\1scram-sha-256/' /var/lib/pgsql/data/pg_hba.conf
systemctl reload postgresql

install -d -o "$APP_USER" -g "$APP_USER" "$APP_ROOT" "$APP_ROOT/shared"

if [[ ! -f "$APP_ROOT/shared/backend.env" ]]; then
  log "Creating database and production secrets"
  DB_PASSWORD=$(python3.12 -c 'import secrets; print(secrets.token_urlsafe(32))')
  JWT_SECRET=$(python3.12 -c 'import secrets; print(secrets.token_urlsafe(64))')
  sudo -u postgres psql -v ON_ERROR_STOP=1 \
    --set=db_user="$DB_USER" --set=db_password="$DB_PASSWORD" --set=db_name="$DB_NAME" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'db_user', :'db_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'db_user') \gexec
SELECT format('CREATE DATABASE %I OWNER %I', :'db_name', :'db_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'db_name') \gexec
SQL
  umask 077
  cat > "$APP_ROOT/shared/backend.env" <<EOF
APP_NAME=SLN Warehouse Management System
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO
HOST=127.0.0.1
PORT=8000
DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@127.0.0.1:5432/${DB_NAME}
SYNC_DATABASE_URL=postgresql+psycopg2://${DB_USER}:${DB_PASSWORD}@127.0.0.1:5432/${DB_NAME}
JWT_SECRET_KEY=${JWT_SECRET}
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=["http://13.60.31.242","https://13.60.31.242"]
EOF
  chown "$APP_USER:$APP_USER" "$APP_ROOT/shared/backend.env"
  chmod 600 "$APP_ROOT/shared/backend.env"
fi

if [[ ! -f "$RELEASE_ARCHIVE" ]]; then
  echo "Release archive not found: $RELEASE_ARCHIVE" >&2
  exit 1
fi

log "Extracting application release"
rm -rf "$APP_ROOT/release.new"
install -d -o "$APP_USER" -g "$APP_USER" "$APP_ROOT/release.new"
tar -xzf "$RELEASE_ARCHIVE" -C "$APP_ROOT/release.new"
ln -s "$APP_ROOT/shared/backend.env" "$APP_ROOT/release.new/warehouse/.env"
chown -R "$APP_USER:$APP_USER" "$APP_ROOT/release.new"

log "Installing backend dependencies"
if [[ ! -x "$APP_ROOT/venv/bin/python" ]]; then
  sudo -u "$APP_USER" python3.12 -m venv "$APP_ROOT/venv"
fi
sudo -u "$APP_USER" "$APP_ROOT/venv/bin/python" -m pip install --no-cache-dir --upgrade pip
sudo -u "$APP_USER" "$APP_ROOT/venv/bin/python" -m pip install --no-cache-dir -r "$APP_ROOT/release.new/warehouse/requirements.txt"
# rapidocr declares the GUI OpenCV package even on servers. Keep the headless
# build last so cv2 does not require X11 libraries such as libxcb.
sudo -u "$APP_USER" "$APP_ROOT/venv/bin/python" -m pip uninstall -y opencv-python
sudo -u "$APP_USER" "$APP_ROOT/venv/bin/python" -m pip install --no-cache-dir --force-reinstall opencv-python-headless

log "Running database migrations"
sudo -u "$APP_USER" bash -c "cd '$APP_ROOT/release.new/warehouse' && '$APP_ROOT/venv/bin/python' -m alembic upgrade head"

if [[ -d "$APP_ROOT/release" ]]; then
  rm -rf "$APP_ROOT/release.previous"
  mv "$APP_ROOT/release" "$APP_ROOT/release.previous"
fi
mv "$APP_ROOT/release.new" "$APP_ROOT/release"

install -m 0644 "$APP_ROOT/release/deploy/sln-backend.service" /etc/systemd/system/sln-backend.service
install -m 0644 "$APP_ROOT/release/deploy/nginx.conf" /etc/nginx/conf.d/sln-wms.conf
rm -f /etc/nginx/conf.d/default.conf
systemctl daemon-reload
systemctl enable sln-backend nginx
systemctl restart sln-backend
nginx -t
systemctl restart nginx

log "Verifying services"
for attempt in {1..20}; do
  if curl --fail --silent http://127.0.0.1:8000/health >/dev/null; then
    break
  fi
  if [[ $attempt -eq 20 ]]; then
    journalctl -u sln-backend -n 100 --no-pager
    exit 1
  fi
  sleep 2
done
curl --fail --silent -H 'Host: 13.60.31.242' http://127.0.0.1/health
echo
log "Deployment complete"

