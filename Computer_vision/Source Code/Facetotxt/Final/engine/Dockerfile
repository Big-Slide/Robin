FROM python:3.9-slim

WORKDIR /approot/final
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

# Copy requirements file
COPY requirements.txt /srv/requirements.txt

# Install Python dependencies one by one with --no-deps to avoid hash verification
RUN pip install --no-cache-dir --disable-pip-version-check --no-deps \
    pika==1.2.0 \
    python-multipart==0.0.5 \
    pydantic==1.8.0 \
    numpy==1.21.0 \
    opencv-python==4.5.0 \
    tensorflow==2.8.0 \
    keras==2.8.0 \
    mediapipe==0.8.9 \
    python-jose==3.3.0 \
    python-dotenv==0.19.0

# Copy current directory contents into container
COPY . .

# Set the line endings to LF
RUN find . -type f -name "*.py" -exec sed -i 's/\r$//' {} +