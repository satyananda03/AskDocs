FROM python:3.12-slim

WORKDIR /app

# Install LibreOffice + dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    libreoffice-writer \
    libreoffice-impress \
    libreoffice-calc \
    fonts-liberation \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml .

RUN uv pip install --system -e .

COPY . .

EXPOSE 8000

CMD ["python", "run.py"]