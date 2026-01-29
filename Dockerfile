# Usar imagen base de Python oficial
FROM python:3.10-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema (necesario para psycopg2-binary en algunos casos)
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Copiar archivos de dependencias
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del proyecto
COPY . .

# Exponer el puerto (aunque Render lo gestiona, es buena práctica)
EXPOSE 8000

# Comando de inicio usando la variable de entorno PORT que provee Render
CMD sh -c "uvicorn server.main:app --host 0.0.0.0 --port ${PORT:-8000}"
