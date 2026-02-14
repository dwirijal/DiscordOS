FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (needed for compilation of some libs)
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Install Common Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Source Code
COPY . .

# Run Bot
CMD ["python", "main.py"]
