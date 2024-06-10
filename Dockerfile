# Use official Python image from the Docker Hub
FROM python:3.11

# Set environment variables to prevent Python from writing pyc files to disk
ENV PYTHONDONTWRITEBYTECODE 1
# Force stdout and stderr to be unbuffered
ENV PYTHONUNBUFFERED 1
# Define the path for Playwright browsers
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Install necessary system dependencies including FFmpeg
RUN apt-get update -y && \
    apt-get install -y openjdk-17-jdk poppler-utils tesseract-ocr wget gnupg2 netcat-openbsd && \
    apt-get install -y chromium ffmpeg && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Node.js for Playwright
RUN curl -sL https://deb.nodesource.com/setup_21.x | bash - && \
    apt-get install -y nodejs

# Clean up APT when done
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /code

# Copy the project files to the working directory
COPY . /code/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Verify installation
RUN pip list
RUN which daphne

# Install Playwright and browsers
RUN npm i -D playwright && npx playwright install

# Give execute permissions to the entrypoint script
RUN chmod +x /code/entrypoint.sh

# Set the entrypoint script to be executed
ENTRYPOINT ["/code/entrypoint.sh"]

# Run the application
CMD ["daphne", "koda.asgi:application", "--port", "$PORT", "--bind", "0.0.0.0"]
