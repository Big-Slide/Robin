FROM python:3.10-bullseye

ENV LANG C.UTF-8
ARG PIP_TIMEOUT=60

RUN apt update && apt install curl espeak-ng
RUN python3 -m pip install --upgrade pip

ADD ./requirements.txt /srv/
RUN python3 -m pip install -r /srv/requirements.txt --timeout $PIP_TIMEOUT

WORKDIR /approot/src