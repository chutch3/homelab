#!/bin/sh
set -eu

if [ -n "${DATABASE_PASSWORD_FILE:-}" ]; then
    DATABASE_PASSWORD=$(cat "$DATABASE_PASSWORD_FILE")
    export DATABASE_PASSWORD
fi
if [ -n "${SECRET_KEY_BASE_FILE:-}" ]; then
    SECRET_KEY_BASE=$(cat "$SECRET_KEY_BASE_FILE")
    export SECRET_KEY_BASE
fi
if [ -n "${password_auth_pepper_FILE:-}" ]; then
    password_auth_pepper=$(cat "$password_auth_pepper_FILE")
    export password_auth_pepper
fi

case "${1:-web}" in
    web|worker|poller|housekeeping)
        bundle exec ruby docker/wait-for-database.rb
        if [ "${1:-web}" = web ]; then
            bundle exec rake db:prepare
        else
            attempts=0
            until bundle exec rake db:abort_if_pending_migrations; do
                attempts=$((attempts + 1))
                if [ "$attempts" -ge 60 ]; then
                    echo "Database migrations did not finish within the startup window" >&2
                    exit 1
                fi
                sleep 2
            done
        fi
        ;;
esac

case "${1:-web}" in
    web) exec bundle exec puma -C config/puma.rb ;;
    worker) exec bundle exec rake jobs:work ;;
    poller) exec bundle exec rake projectmonitor:poller ;;
    housekeeping) exec bundle exec clockwork clockwork.rb ;;
    *) exec "$@" ;;
esac
