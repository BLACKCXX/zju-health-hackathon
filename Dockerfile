FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY report/ ./report/
COPY app.py README.md ./

RUN mkdir -p textbooks uploads data indexes outputs

EXPOSE 18000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "18000"]
