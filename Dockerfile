FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV VIBES_ORIGIN=https://vibes-coded-production.up.railway.app
EXPOSE 3000

ENTRYPOINT ["python", "mcp_server.py"]
