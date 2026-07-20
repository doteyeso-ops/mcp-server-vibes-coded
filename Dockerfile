FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV VIBES_ORIGIN=https://vibes-coded-production.up.railway.app
# Serve over streamable-HTTP so hosted MCP inspectors (Glama/Smithery) can
# connect and enumerate tools. stdio is for local clients only.
ENV MCP_TRANSPORT=streamable-http
ENV HOST=0.0.0.0
ENV PORT=3000
EXPOSE 3000

ENTRYPOINT ["python", "mcp_server.py"]
