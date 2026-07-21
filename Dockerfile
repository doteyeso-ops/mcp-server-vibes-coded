FROM python:3.11-slim

WORKDIR /app

# curl for HEALTHCHECK (Glama / registry probes)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --upgrade pip \
  && python -m pip install --no-cache-dir -r requirements.txt

COPY mcp_server.py pyproject.toml README.md LICENSE ./

ENV VIBES_ORIGIN=https://vibes-coded-production.up.railway.app
# Hosted inspectors (Glama/Smithery) need streamable-HTTP, not stdio.
ENV MCP_TRANSPORT=streamable-http
ENV HOST=0.0.0.0
ENV PORT=3000
EXPOSE 3000

HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
  CMD curl -fsS http://127.0.0.1:3000/healthz || exit 1

ENTRYPOINT ["python", "mcp_server.py"]
