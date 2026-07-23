FROM python:3.11-slim

WORKDIR /app/doctflow

# Instala dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python do backend
COPY doctflow/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código do backend
COPY doctflow/ .

# Porta exposta
EXPOSE 8000

# Comando de start
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
