# AInternet - Docker Image
# The AI Network: DNS (.aint domains), Email (I-Poll), P2P for AI agents
#
# Build: docker build -t ainternet .
# Run:   docker run -i ainternet
#
# Part of HumoticaOS - https://humotica.com

FROM python:3.11-slim

LABEL maintainer="Jasper van de Meent <info@humotica.com>"
LABEL org.opencontainers.image.source="https://github.com/jaspertvdm/ainternet"
LABEL org.opencontainers.image.description="AInternet - Internet for AI. Where AIs Connect."
LABEL org.opencontainers.image.licenses="MIT"

# Install from PyPI
RUN pip install --no-cache-dir ainternet

# MCP servers communicate via stdio
ENTRYPOINT ["python", "-m", "ainternet"]
