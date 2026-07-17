FROM oven/bun:1.3.9

WORKDIR /app

COPY package.json bun.lock ./
COPY sidecar/package.json ./sidecar/package.json
RUN bun install --frozen-lockfile --production --filter inventory-ai-sidecar

COPY sidecar ./sidecar

WORKDIR /app/sidecar
ENV NODE_ENV=production

CMD ["bun", "run", "start"]
