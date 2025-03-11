# Use Python 3.9 as base image
FROM python:3.9-slim

WORKDIR /approot/Final
ENV LANG=C.UTF-8
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

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

# Install Python dependencies one by one to better handle errors
RUN pip install --no-cache-dir numpy==1.21.0 && \
    pip install --no-cache-dir opencv-python-headless==4.8.1.78 && \
    pip install --no-cache-dir keras==2.13.1 && \
    pip install --no-cache-dir tensorflow==2.13.0 && \
    pip install --no-cache-dir mediapipe==0.10.5 && \
    pip install --no-cache-dir pika==1.3.1

# Copy current directory contents into container

# Set the line endings to LF
RUN find . -type f -name "*.py" -exec sed -i 's/\r$//' {} +