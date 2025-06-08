FROM --platform=linux/amd64 python:3.10-slim-bookworm

ENV LANG C.UTF-8
ARG PIP_TIMEOUT=500

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y curl dnsutils libaio1 ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --upgrade pip

RUN python -m pip install torch==2.7.0+cpu torchaudio==2.7.0+cpu --index-url https://download.pytorch.org/whl/cpu --timeout $PIP_TIMEOUT

RUN python -m pip install speechbrain==1.0.3  --timeout $PIP_TIMEOUT

ADD ./requirements.txt /srv/
RUN python -m pip cache purge && python -m pip install --timeout $PIP_TIMEOUT --no-cache-dir -r /srv/requirements.txt

WORKDIR /approot/src