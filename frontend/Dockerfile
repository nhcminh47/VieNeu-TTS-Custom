FROM node:24-slim AS deps

WORKDIR /app
RUN corepack enable

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

FROM node:24-slim AS builder

WORKDIR /app
RUN corepack enable

ARG NEXT_PUBLIC_VIENEU_API_BASE=/api/vieneu
ENV NEXT_TELEMETRY_DISABLED=1 \
    NEXT_PUBLIC_VIENEU_API_BASE=$NEXT_PUBLIC_VIENEU_API_BASE

COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN pnpm build

FROM node:24-slim AS runner

WORKDIR /app
RUN corepack enable

ARG NEXT_PUBLIC_VIENEU_API_BASE=/api/vieneu
ARG VIENEU_INTERNAL_API_BASE=http://127.0.0.1:8000
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000 \
    NEXT_PUBLIC_VIENEU_API_BASE=$NEXT_PUBLIC_VIENEU_API_BASE \
    VIENEU_INTERNAL_API_BASE=$VIENEU_INTERNAL_API_BASE

COPY --from=builder /app ./

EXPOSE 3000

CMD ["pnpm", "start"]
