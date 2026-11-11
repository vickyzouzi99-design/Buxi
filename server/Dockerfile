FROM python:3.12-slim
WORKDIR /app
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server /app/server
COPY Buxi_Tarot_Knowledge_v01 /app/Buxi_Tarot_Knowledge_v01
RUN useradd --uid 10001 --create-home buxi && mkdir /data && chown buxi /data
USER buxi
ENV BUXI_DATA_DIR=/data PYTHONUNBUFFERED=1
CMD ["uvicorn","server.app.main:app","--host","0.0.0.0","--port","8000"]
