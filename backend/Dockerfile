FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app ./app
COPY run.py ./run.py

RUN mkdir -p /app/data /app/uploads

EXPOSE 8001

# SQLite 与内置定时任务必须保持单进程，避免重复执行和并发写库。
CMD ["sh", "-c", "python run.py init-db && exec uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 1"]
