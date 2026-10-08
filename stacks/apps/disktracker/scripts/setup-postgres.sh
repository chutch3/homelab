#!/usr/bin/env bash
# Set up PostgreSQL 16 locally for DiskTracker on Ubuntu/Debian.
# Run as your normal user; sudo is used only to install missing packages.
set -euo pipefail
umask 077

if (( EUID == 0 )); then
    echo "Run this script as your normal user, without sudo." >&2
    exit 1
fi

app_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
local_dir="$app_dir/.local"
# .local/ lives on the workspace filesystem, which multiple containers (each with
# its own PID and network namespace) can mount at once, so credentials there are
# keyed by hostname. The data directory stays off it entirely: the workspace is a
# cluster filesystem on shared iSCSI storage, where a single write can stall for
# many seconds, so it lives on this container's own disk.
host_id="$(hostname)"
pg_data="${XDG_STATE_HOME:-$HOME/.local/state}/disktracker/postgres"
pg_bin=/usr/lib/postgresql/16/bin
credentials="$local_dir/env-$host_id.sh"

if [[ ! -x "$pg_bin/initdb" ]] || ! command -v python3 >/dev/null; then
    sudo apt-get update
    sudo apt-get install -y postgresql-16 postgresql-client-16 python3
fi

mkdir -p "$local_dir" "$(dirname -- "$pg_data")"

if [[ -f "$pg_data/PG_VERSION" ]]; then
    if [[ ! -f "$credentials" ]]; then
        echo "Existing cluster has no $credentials. Restore its credentials before continuing." >&2
        exit 1
    fi
else
    if [[ -e "$pg_data" ]]; then
        echo "Found an incomplete cluster in $pg_data; inspect it before continuing." >&2
        exit 1
    fi

    if [[ -f "$credentials" ]]; then
        # A rebuilt container keeps its credentials on the workspace but starts with
        # an empty disk; start a fresh cluster under the same password.
        # shellcheck source=/dev/null
        db_password="$(source "$credentials" && python3 -c 'import os, urllib.parse; print(urllib.parse.urlsplit(os.environ["DISKTRACKER_TEST_ADMIN_URL"]).password)')"
    else
        db_password="$(python3 -c 'import secrets; print(secrets.token_hex(24))')"
        printf "export DISKTRACKER_DATABASE_URL='postgresql+psycopg://disktracker:%s@127.0.0.1:55432/disktracker'\nexport DISKTRACKER_TEST_ADMIN_URL='postgresql://disktracker:%s@127.0.0.1:55432/postgres'\n" \
            "$db_password" "$db_password" > "$credentials"
    fi

    "$pg_bin/initdb" \
        -D "$pg_data" \
        --username=disktracker \
        --auth=scram-sha-256 \
        --pwfile=<(printf '%s\n' "$db_password")
    unset db_password

    # PostgreSQL configuration escapes single quotes by doubling them.
    socket_dir="${pg_data//\'/\'\'}"
    cat >> "$pg_data/postgresql.conf" <<EOF
listen_addresses = '127.0.0.1'
port = 55432
unix_socket_directories = '$socket_dir'
timezone = 'UTC'
log_timezone = 'UTC'
EOF
fi

chmod 600 "$credentials"
# shellcheck source=/dev/null
source "$credentials"
: "${DISKTRACKER_TEST_ADMIN_URL:?Missing test/admin database URL in env.sh}"

if ! "$pg_bin/pg_ctl" -D "$pg_data" status >/dev/null 2>&1; then
    # The data directory is on this container's own disk, so a PID file here can
    # only be this container's own crashed process.
    if [[ -f "$pg_data/postmaster.pid" ]]; then
        echo "A PostgreSQL PID file exists for this host's cluster, but its server is not running." >&2
        echo "If nothing else on this host is using it, remove $pg_data/postmaster.pid and rerun this script." >&2
        exit 1
    fi
    "$pg_bin/pg_ctl" -D "$pg_data" -l "$pg_data/server.log" -w start
fi

# Pass the URL explicitly; PGDATABASE does not expand a connection URI.
# Disable local psql startup files and stop on SQL errors.
actual_data_dir="$("$pg_bin/psql" --dbname="$DISKTRACKER_TEST_ADMIN_URL" -X -v ON_ERROR_STOP=1 -Atc 'SHOW data_directory')"
if [[ "$(realpath "$actual_data_dir")" != "$(realpath "$pg_data")" ]]; then
    echo "env.sh points to a different PostgreSQL cluster; refusing to create a database." >&2
    exit 1
fi

exists="$("$pg_bin/psql" --dbname="$DISKTRACKER_TEST_ADMIN_URL" -X -v ON_ERROR_STOP=1 -Atc "SELECT 1 FROM pg_database WHERE datname = 'disktracker'")"
if [[ "$exists" != 1 ]]; then
    "$pg_bin/psql" --dbname="$DISKTRACKER_TEST_ADMIN_URL" -X -v ON_ERROR_STOP=1 -c 'CREATE DATABASE disktracker'
fi

printf '\nPostgreSQL is ready. Credentials: %s\n' "$credentials"
echo 'From the repository root, run: task dev -- disktracker'
echo 'That command applies database migrations and starts the app.'
