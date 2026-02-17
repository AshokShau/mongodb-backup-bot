FROM python:3.11-slim-bullseye

WORKDIR /app

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        wget \
        gnupg; \
    \
    wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | apt-key add -; \
    \
    echo "deb http://repo.mongodb.org/apt/debian bullseye/mongodb-org/6.0 main" \
        > /etc/apt/sources.list.d/mongodb-org-6.0.list; \
    \
    apt-get update; \
    apt-get install -y --no-install-recommends mongodb-database-tools; \
    \
    rm -rf /var/lib/apt/lists/* /tmp/*; \
    mongorestore --version

RUN pip install --no-cache-dir uv

COPY . .

RUN uv pip install -e . --system

CMD ["start"]
