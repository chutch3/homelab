FROM ruby:3.4.11-slim-bookworm AS base

ENV RAILS_ENV=production \
    BUNDLE_PATH=/usr/local/bundle \
    BUNDLE_FROZEN=true \
    RAILS_SERVE_STATIC_FILES=true
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates libmariadb3 libyaml-0-2 nodejs tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 projectmonitor \
    && useradd --uid 1000 --gid 1000 --create-home projectmonitor

FROM base AS build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git libmariadb-dev libssl-dev libyaml-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*
COPY Gemfile Gemfile.lock ./
RUN bundle config set without 'development test' && bundle install --jobs 4
COPY . .
# Build assets without a running database or a real deployment secret.
RUN SECRET_KEY_BASE=asset-compilation-placeholder-not-a-runtime-secret \
    bundle exec rake assets:precompile

FROM build AS test
ENV RAILS_ENV=test BUNDLE_WITHOUT="" CHROME_BIN=/usr/bin/chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium chromium-driver npm \
    && rm -rf /var/lib/apt/lists/* \
    && bundle config unset without && bundle install --jobs 4
RUN npm ci && chown -R projectmonitor:projectmonitor /app
USER 1000:1000
CMD ["bash", "script/test-all.sh"]

FROM base AS production
COPY --from=build /usr/local/bundle /usr/local/bundle
COPY --from=build --chown=projectmonitor:projectmonitor /app /app
USER 1000:1000
EXPOSE 3000
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["web"]
