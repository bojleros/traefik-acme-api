FROM docker.io/alpine:3

RUN mkdir /app && \
  apk add py3-flask>=3.0.3 py3-gunicorn>=23.0.0 py3-cryptography>=44.0.0

WORKDIR /app
COPY app.py /app/.

ENV GUNICORN_CMD_ARGS="--bind 0.0.0.0:8080 --access-logfile - --error-logfile -"
ENV DNS_PROVIDER="route53"

CMD ["/usr/bin/gunicorn", "app:app"]