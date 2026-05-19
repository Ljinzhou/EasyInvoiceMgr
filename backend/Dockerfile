FROM python:3.11-slim

ARG USE_CHINA_MIRROR=false

RUN if [ "$USE_CHINA_MIRROR" = "true" ]; then \
        sed -i "s/deb.debian.org/mirrors.aliyun.com/g" /etc/apt/sources.list.d/debian.sources; \
    fi \
    && apt-get update && apt-get install -y --no-install-recommends \
    mupdf-tools \
    postgresql-client \
    gzip \
    git \
    ca-certificates \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI (for triggering host docker compose during update)
# 根据是否使用中国镜像选择不同的 Docker 源
RUN set -ex \
    && install -m 0755 -d /etc/apt/keyrings \
    && if [ "$USE_CHINA_MIRROR" = "true" ]; then \
        curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/debian/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
        && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://mirrors.aliyun.com/docker-ce/linux/debian bookworm stable" \
        > /etc/apt/sources.list.d/docker.list; \
    else \
        curl -fsSL https://download.docker.com/linux/debian/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
        && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian bookworm stable" \
        > /etc/apt/sources.list.d/docker.list; \
    fi \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
ARG USE_CHINA_MIRROR
RUN if [ "$USE_CHINA_MIRROR" = "true" ]; then \
        pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi

COPY . .

RUN mkdir -p uploads exports

EXPOSE 5000

CMD ["python", "app.py"]
