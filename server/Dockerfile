FROM python:3.12-slim
WORKDIR /app

RUN pip install uv --no-cache-dir

COPY pyproject.toml .
RUN uv sync --no-dev

COPY app/ app/

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
