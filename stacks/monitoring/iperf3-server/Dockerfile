FROM python:3.12-alpine

# iperf3 is intentionally unpinned to track the base image's current version.
# hadolint ignore=DL3018
RUN apk add --no-cache iperf3 && \
    iperf3 --version && \
    adduser -D -u 10001 iperf3user
USER iperf3user

EXPOSE 5201

CMD ["iperf3", "-s"]
