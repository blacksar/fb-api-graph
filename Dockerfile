# Imagen con Python + dependencias del sistema para Playwright (Chromium)
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# 1. Dependencias Python (incluye playwright)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Navegador Chromium
RUN playwright install chromium

COPY . .

EXPOSE 8000

# Si Chromium falla al lanzar, ejecutar con: docker run -p 8000:8000 --ipc=host --init api-facebook
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
