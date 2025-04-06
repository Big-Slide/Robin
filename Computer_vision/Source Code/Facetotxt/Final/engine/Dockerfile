FROM python:3.9-slim

ENV LANG=C.UTF-8
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ARG PIP_TIMEOUT=500

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip first
RUN python -m pip install --upgrade pip


# Copy requirements file

# Install Python dependencies one by one with --no-deps to avoid hash verification
RUN pip install --no-cache-dir numpy==1.26.4 && \
    pip install --no-cache-dir opencv-python-headless==4.10.0.84 && \
    pip install --no-cache-dir keras==3.7.0 && \
    pip install --no-cache-dir mediapipe==0.10.20 && \
    pip install --no-cache-dir pika==1.3.1 && \
    pip install --no-cache-dir python-multipart==0.0.20 && \
    pip install --no-cache-dir pydantic==2.10.5 && \
    pip install --no-cache-dir python-jose==3.3.0 && \
    pip install --no-cache-dir python-dotenv==1.0.1 &&\
    pip install --no-cache-dir tensorflow==2.18.0

# Install tensorflow in a separate step with --no-deps
ADD ./requirements.txt /srv/
RUN python -m pip install --timeout $PIP_TIMEOUT -r /srv/requirements.txt

WORKDIR /approot/src


# Set the line endings to LF
RUN find . -type f -name "*.py" -exec sed -i 's/\r$//' {} +