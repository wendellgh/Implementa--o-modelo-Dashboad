FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

COPY Python/requirements.txt ./Python/requirements.txt
# RUN pip install --no-cache-dir -r Python/requirements.txt

COPY Python ./Python

EXPOSE 8501

CMD ["streamlit", "run", "Python/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
