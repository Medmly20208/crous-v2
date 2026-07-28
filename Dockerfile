FROM python:3.11-slim

WORKDIR /app

# System deps needed by apt during playwright's browser install step
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# This runs as root inside the Docker build, so --with-deps can
# actually install the system libraries Chromium needs (unlike on
# Render's native build environment, which doesn't grant root access).
RUN playwright install --with-deps chromium

COPY . .

CMD ["python", "logement.py"]
