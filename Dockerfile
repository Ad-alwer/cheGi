FROM python:3.12-slim AS builder

ARG VERSION

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -e . \
    && python -c "import shutil; shutil.which('chegi') or print('WARN: chegi not found in PATH')"

FROM debian:stable-slim
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/chegi /usr/local/bin/chegi
RUN ln -s /usr/local/bin/chegi /usr/local/bin/cheGi
ENTRYPOINT ["chegi"]
