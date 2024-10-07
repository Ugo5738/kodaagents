# Use official Python image from the Docker Hub
FROM python:3.11

# Set environment variables to prevent Python from writing pyc files to disk
ENV PYTHONDONTWRITEBYTECODE 1
# Force stdout and stderr to be unbuffered
ENV PYTHONUNBUFFERED 1

# Install necessary system dependencies including FFmpeg and build tools
RUN apt-get update -y && \
    apt-get install -y \
    openjdk-17-jdk \
    poppler-utils \
    tesseract-ocr \
    wget \
    gnupg2 \
    netcat-openbsd \
    chromium \
    ffmpeg \
    build-essential \
    curl \
    pkg-config \
    libssl-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Rust using rustup
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
# Add Rust to PATH
ENV PATH="/root/.cargo/bin:${PATH}"

# Upgrade pip
RUN pip install --upgrade pip

# Set the working directory
WORKDIR /code

# Copy the project files to the working directory
COPY . /code/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Give execute permissions to the entrypoint script
RUN chmod +x /code/entrypoint.sh

# Set the entrypoint script to be executed
ENTRYPOINT ["/code/entrypoint.sh"]

# Run the application
CMD ["daphne", "koda.asgi:application", "--port", "$PORT", "--bind", "0.0.0.0"]


# For Multi-Stage build
# # Stage 1: Build stage
# FROM python:3.11 AS builder

# # Install system dependencies and Rust
# RUN apt-get update -y && \
#     apt-get install -y \
#         build-essential \
#         curl \
#         pkg-config \
#         libssl-dev \
#         && apt-get clean && rm -rf /var/lib/apt/lists/*

# RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
# ENV PATH="/root/.cargo/bin:${PATH}"

# # Upgrade pip
# RUN pip install --upgrade pip

# # Set the working directory
# WORKDIR /tmp

# # Copy only requirements.txt to leverage Docker layer caching
# COPY requirements.txt .

# # Install Python dependencies
# RUN pip install --user --no-cache-dir -r requirements.txt

# # Stage 2: Final image
# FROM python:3.11

# # Set environment variables
# ENV PYTHONDONTWRITEBYTECODE 1
# ENV PYTHONUNBUFFERED 1

# # Install runtime dependencies
# RUN apt-get update -y && \
#     apt-get install -y \
#         openjdk-17-jdk \
#         poppler-utils \
#         tesseract-ocr \
#         wget \
#         gnupg2 \
#         netcat-openbsd \
#         chromium \
#         ffmpeg \
#         && apt-get clean && rm -rf /var/lib/apt/lists/*

# # Set the working directory
# WORKDIR /code

# # Copy the application code
# COPY . /code/

# # Copy installed Python packages from the builder
# COPY --from=builder /root/.local /root/.local

# # Update PATH environment variable
# ENV PATH="/root/.local/bin:${PATH}"

# # Give execute permissions to the entrypoint script
# RUN chmod +x /code/entrypoint.sh

# # Set the entrypoint script to be executed
# ENTRYPOINT ["/code/entrypoint.sh"]

# # Run the application
# CMD ["daphne", "koda.asgi:application", "--port", "$PORT", "--bind", "0.0.0.0"]
