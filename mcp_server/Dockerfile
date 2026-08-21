FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install core GLOW library used by MCP handlers.
# Install shared core from a source archive so docker builds do not depend on
# PyPI — pinned to a commit SHA, never a moving branch: an unpinned main.zip is
# how the deployed image and the endpoints drifted apart (contract v0.1.1 split
# vs. an older container build). To upgrade: verify the new SHA locally, update
# it here, and redeploy.
RUN pip install --no-cache-dir https://github.com/Community-Access/quill-glow-core/archive/6fded95d2972e64154b6375d678f2ecd57da177a.zip
COPY desktop/pyproject.toml desktop/
COPY desktop/src/ desktop/src/
RUN pip install --no-cache-dir ./desktop

# Install MCP server runtime dependencies.
COPY mcp_server/requirements.txt mcp_server/
RUN pip install --no-cache-dir -r mcp_server/requirements.txt

# Copy MCP server source.
COPY mcp_server/ mcp_server/

EXPOSE 8000

CMD ["uvicorn", "mcp_server.main:app", "--host", "0.0.0.0", "--port", "8000"]
