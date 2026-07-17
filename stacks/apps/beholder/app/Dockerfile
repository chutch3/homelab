FROM node:22-alpine

ENV NODE_ENV=production

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund

COPY src ./src

# state volume mounts at /state; node user must own what it writes
RUN mkdir -p /state && chown node:node /state

USER node

CMD ["node", "src/index.js"]
