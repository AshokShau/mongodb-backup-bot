FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    gnupg && \
    wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | apt-key add - && \
    echo "deb http://repo.mongodb.org/apt/debian bullseye/mongodb-org/6.0 main" | tee /etc/apt/sources.list.d/mongodb-org-6.0.list && \
    apt-get update && \
    apt-get install -y mongodb-database-tools && \
    apt-get remove -y wget gnupg && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.7.2

COPY . /app/

RUN uv pip install -e . --system

CMD ["start"]
