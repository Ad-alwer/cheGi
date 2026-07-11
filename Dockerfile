FROM debian:stable-slim AS builder

ARG VERSION
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

ADD https://github.com/Ad-alwer/cheGi/releases/download/v${VERSION}/chegi_${VERSION}_linux_amd64.tar.gz /tmp/
RUN tar xzf /tmp/chegi_*.tar.gz -C /tmp/

FROM debian:stable-slim
COPY --from=builder /tmp/chegi /usr/local/bin/cheGi
ENTRYPOINT ["cheGi"]
