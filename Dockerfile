# Pull the base image
FROM python:3.11

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PLAYWRIGHT_BROWSERS_PATH /ms-playwright

# Install necessary system dependencies including FFmpeg
RUN apt-get update -y && \
    apt-get install -y openjdk-17-jdk poppler-utils tesseract-ocr \
    wget gnupg2 -y && \
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' && \
    apt-get update && apt-get install -y google-chrome-stable ffmpeg

# Install Node.js for Playwright
RUN curl -sL https://deb.nodesource.com/setup_21.x | bash - && \
    apt-get install -y nodejs

# Clean up APT when done
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /code

# Copy project
COPY . /code/

# Install Python dependencies
# RUN pip install -r requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and browsers
RUN npm i -D playwright && npx playwright install

# Give execute permissions to the entrypoint script
RUN chmod +x /code/entrypoint.sh

# Set the entrypoint script to be executed
ENTRYPOINT ["/code/entrypoint.sh"]

# Run the application
# CMD daphne koda.asgi:application --port $PORT --bind 0.0.0.0
CMD ["daphne", "koda.asgi:application", "--port", "$PORT", "--bind", "0.0.0.0"]
