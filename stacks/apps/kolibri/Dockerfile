FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends sqlite3 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir kolibri==0.19.2 kolibri-oidc-client-plugin==0.3.2

ENV KOLIBRI_HOME=/kolibrihome
ENV KOLIBRI_HTTP_PORT=8080
ENV KOLIBRI_RUN_MODE=docker

WORKDIR /kolibrihome

EXPOSE 8080

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
