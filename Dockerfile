FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /data

ENV QALACH_DATA_DIR=/data
ENV PORT=8550
EXPOSE 8550

CMD ["python", "app_qalach_darak.py"]
