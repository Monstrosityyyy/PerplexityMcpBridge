ARG BUILD_FROM=ghcr.io/hassio-addons/base-python:15.0.7
FROM ${BUILD_FROM}

WORKDIR /app

RUN apk add --no-cache cloudflared

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src /app/src
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
