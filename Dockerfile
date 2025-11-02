FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends wget gnupg ca-certificates && \
    wget -qO /usr/share/keyrings/mongodb-server-6.0.gpg https://www.mongodb.org/static/pgp/server-6.0.asc && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/mongodb-server-6.0.gpg] \
        http://repo.mongodb.org/apt/debian bullseye/mongodb-org/6.0 main" \
        | tee /etc/apt/sources.list.d/mongodb-org-6.0.list > /dev/null && \
    apt-get update && \
    apt-get install -y --no-install-recommends mongodb-database-tools && \
    apt-get purge -y --auto-remove wget gnupg && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN pip install --no-cache-dir uv

COPY . .
RUN uv pip install -e . --system

CMD ["start"]
