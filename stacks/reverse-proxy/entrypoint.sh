#!/bin/sh
set -e

# Set the required permissions on the acme.json file
chmod 600 /letsencrypt/acme.json

# Run the main Traefik process
exec traefik
