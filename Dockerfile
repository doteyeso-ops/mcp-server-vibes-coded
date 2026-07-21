FROM python:3.11-slim

WORKDIR /app

# Optional curl for HTTP-mode probes (Smithery / self-host). Glama generates its own image.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --upgrade pip \
  && python -m pip install --no-cache-dir -r requirements.txt

COPY mcp_server.py pyproject.toml README.md LICENSE ./

# Official MCP Registry ownership marker for OCI packages
LABEL io.modelcontextprotocol.server.name="io.github.doteyeso-ops/mcp-server-vibes-coded"
LABEL org.opencontainers.image.source="https://github.com/doteyeso-ops/mcp-server-vibes-coded"
LABEL org.opencontainers.image.description="Vibes-Coded x402 agent tools MCP server"

ENV VIBES_ORIGIN=https://vibes-coded-production.up.railway.app
# Default: stdio (MCP Registry OCI + Glama mcp-proxy). For HTTP inspectors set:
#   MCP_TRANSPORT=streamable-http PORT=3000
ENV HOST=0.0.0.0
EXPOSE 3000

# Stdio by default — do not force MCP_TRANSPORT/PORT here (breaks Glama verify).
ENTRYPOINT ["python", "mcp_server.py"]
