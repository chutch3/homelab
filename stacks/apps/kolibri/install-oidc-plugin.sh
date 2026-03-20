#!/bin/bash
# Install and enable Kolibri OIDC plugin at startup
# pip install is idempotent — safe to run on every container start

set -e

echo "Installing Kolibri OIDC client plugin..."
pip install kolibri-oidc-client-plugin

echo "Enabling OIDC plugin..."
kolibri plugin enable kolibri_oidc_client_plugin || true

echo "OIDC plugin installed and enabled successfully!"
