FROM docker.arvancloud.ir/python:3.10-slim-bookworm

ENV LANG C.UTF-8
ARG PIP_TIMEOUT=500

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y curl dnsutils libaio1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --upgrade pip

ADD ./requirements.txt /srv/
RUN python -m pip cache purge && python -m pip install --timeout $PIP_TIMEOUT --no-cache-dir -r /srv/requirements.txt

WORKDIR /approot/src