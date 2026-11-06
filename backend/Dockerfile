FROM python:3.12-slim
ARG INSTALL_AI=false
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r requirements.txt && if [ "$INSTALL_AI" = "true" ]; then pip install --no-cache-dir -r requirements-ai.txt; fi
RUN useradd --create-home --uid 10001 app && mkdir -p /models/cache /models/custom && chown -R app:app /app /models
COPY --chown=app:app app ./app
USER app
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--ws-max-size","65536","--limit-concurrency","100"]
