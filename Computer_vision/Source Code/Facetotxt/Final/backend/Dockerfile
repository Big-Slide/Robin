# Use Python 3.9 as base image
FROM python:3.9-slim

ENV LANG=C.UTF-8
ARG PIP_TIMEOUT=500

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip first
RUN python -m pip install --upgrade pip

# Copy requirements first for better caching
COPY ./requirements.txt /srv/

# Install Python dependencies
RUN pip install --no-cache-dir --timeout $PIP_TIMEOUT -r /srv/requirements.txt

# Set working directory
WORKDIR /approot/Final