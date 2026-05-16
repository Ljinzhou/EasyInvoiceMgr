ARG NUXT_PUBLIC_API_BASE=http://localhost:5000/api
ARG USE_CHINA_MIRROR=false

FROM node:20-slim AS build

WORKDIR /app

RUN corepack enable && corepack prepare pnpm@9 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./

ARG USE_CHINA_MIRROR
RUN if [ "$USE_CHINA_MIRROR" = "true" ]; then \
        pnpm config set registry https://registry.npmmirror.com; \
    fi \
    && pnpm install --frozen-lockfile

COPY . .

ARG NUXT_PUBLIC_API_BASE
ENV NUXT_PUBLIC_API_BASE=${NUXT_PUBLIC_API_BASE}

RUN NUXT_PUBLIC_API_BASE=${NUXT_PUBLIC_API_BASE} pnpm run build

FROM node:20-slim AS serve

WORKDIR /app

COPY --from=build /app/.output ./.output

EXPOSE 3000

ENV HOST=0.0.0.0
ENV PORT=3000

CMD ["node", ".output/server/index.mjs"]
