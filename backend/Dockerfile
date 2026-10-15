FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# build-essential supports scientific Python wheels that may need compilation.
# WeasyPrint requires Pango/Harfbuzz/JPEG/OpenJPEG at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b \
    libjpeg62-turbo libopenjp2-7 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY README.md ./
RUN pip install --upgrade pip && pip install .

COPY . .

RUN mkdir -p /app/artifacts/reports && chown -R 10001:10001 /app
USER 10001

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
