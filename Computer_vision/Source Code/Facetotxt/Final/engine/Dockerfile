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
RUN pip install --no-cache-dir --no-deps --ignore-installed numpy>=1.21.0 && \
    pip install --no-cache-dir --no-deps --ignore-installed opencv-python-headless==4.8.1.78 && \
    pip install --no-cache-dir --no-deps --ignore-installed keras==2.13.1 && \
    pip install --no-cache-dir --no-deps --ignore-installed tensorflow==2.13.0 && \
    pip install --no-cache-dir --no-deps --ignore-installed mediapipe==0.10.5 && \
    pip install --no-cache-dir --no-deps --ignore-installed pika==1.3.1 && \
    pip install --no-cache-dir --no-deps --ignore-installed python-multipart>=0.0.5 && \
    pip install --no-cache-dir --no-deps --ignore-installed pydantic>=1.8.0 && \
    pip install --no-cache-dir --no-deps --ignore-installed python-jose>=3.3.0 && \
    pip install --no-cache-dir --no-deps --ignore-installed python-dotenv>=0.19.0

# Copy current directory contents into container

# Set the line endings to LF
RUN find . -type f -name "*.py" -exec sed -i 's/\r$//' {} +