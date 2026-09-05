FROM python:3.12.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN addgroup --system par && adduser --system --ingroup par --home /nonexistent par
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip install --no-cache-dir '.[control-plane]'
USER par
CMD ["python", "-m", "provable_agent_reference.control_plane.health"]
