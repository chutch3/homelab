FROM python:3.12-alpine

# iperf3 is intentionally unpinned to track the base image's current version.
# hadolint ignore=DL3018
RUN apk add --no-cache iperf3 && \
    adduser -D -u 10001 exporter && \
    iperf3 --version

COPY --chown=exporter:exporter iperf3_exporter/ /app/iperf3_exporter/

USER exporter

WORKDIR /app
EXPOSE 9579

ENTRYPOINT ["python3", "-m", "iperf3_exporter"]
