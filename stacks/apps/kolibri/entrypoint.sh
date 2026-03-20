#!/bin/sh
set -e

kolibri plugin enable kolibri_oidc_client_plugin

exec kolibri start --foreground
