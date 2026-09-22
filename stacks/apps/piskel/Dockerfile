# Piskel ships no Docker image, so build the static web app from source and
# serve it with nginx. Everything runs in the browser (sprites are saved to the
# browser's local storage), so the runtime image is just static files.

FROM node:22-slim AS build

# Upstream has no recent release tags; pin a commit for reproducible builds.
ARG PISKEL_REF=bef52beb312e771bf0cbb915d873e8d638842d7a

WORKDIR /src
ADD https://github.com/piskelapp/piskel/archive/${PISKEL_REF}.tar.gz /tmp/piskel.tar.gz
RUN tar -xzf /tmp/piskel.tar.gz --strip-components=1 && rm /tmp/piskel.tar.gz

# --ignore-scripts skips husky's git-hook install (no .git in a tarball) and
# puppeteer's Chromium download, which only the test suite needs.
ENV PUPPETEER_SKIP_DOWNLOAD=1
RUN npm ci --ignore-scripts --no-audit --no-fund \
    && npm run build \
    && rm -rf dest/prod/piskelapp-partials

FROM nginxinc/nginx-unprivileged:1.29-alpine

COPY --from=build /src/dest/prod /usr/share/nginx/html

EXPOSE 8080
