FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .  # This copies everything into /app, including shared_files/

CMD ["uvicorn", "semantic_query:app", "--host", "0.0.0.0", "--port", "8080"]
