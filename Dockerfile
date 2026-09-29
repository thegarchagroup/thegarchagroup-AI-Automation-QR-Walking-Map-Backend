FROM python:3.12-slim

WORKDIR /app

# System deps for bcrypt/cryptography wheels are usually unnecessary on
# slim + manylinux wheels, but build-essential covers the rare case a
# wheel isn't available for this platform.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The SQLite file lives in /app/data — mount a volume here (see
# docker-compose.yml) so data survives container rebuilds/redeploys.
# Set DATABASE_URL=sqlite:///./data/walkguide.db in production so it
# actually writes into this mounted folder.
RUN mkdir -p /app/data /app/uploads
VOLUME ["/app/data", "/app/uploads"]

EXPOSE 8000

# No --reload in production, and bind to 0.0.0.0 so it's reachable from
# outside the container (not just localhost inside it).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]