FROM python:3.11-slim

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Crear carpeta de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install gunicorn

# Copiar el resto del proyecto
COPY . .

# Exponer puerto que usará gunicorn (Cloud Run lo inyecta por $PORT)
EXPOSE 8080

# Comando final
CMD exec gunicorn tu_app.wsgi:application --bind 0.0.0.0:$PORT --workers 3
