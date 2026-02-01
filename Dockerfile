# Imagen con Python + dependencias del sistema para Playwright (sin navegadores)
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# 1. Instalar dependencias Python (incluye el paquete playwright)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Instalar el navegador Chromium (explícito al desplegar)
RUN playwright install chromium

# Código de la aplicación
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
