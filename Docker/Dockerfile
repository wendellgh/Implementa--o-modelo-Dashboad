FROM python:3.11-slim-bookworm

ARG ORACLE_INSTANT_CLIENT_URL=https://download.oracle.com/otn_software/linux/instantclient/2121000/instantclient-basic-linux.x64-21.21.0.0.0dbru.zip

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    ORACLE_CLIENT_LIB_DIR=/opt/oracle/instantclient \
    LD_LIBRARY_PATH=/opt/oracle/instantclient

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        libaio1 \
        libnsl2 \
        unzip \
        wget \
    && mkdir -p /opt/oracle \
    && wget -q -O /tmp/instantclient-basic.zip "${ORACLE_INSTANT_CLIENT_URL}" \
    && unzip -q /tmp/instantclient-basic.zip -d /opt/oracle \
    && ln -s /opt/oracle/instantclient_21_21 /opt/oracle/instantclient \
    && echo /opt/oracle/instantclient > /etc/ld.so.conf.d/oracle-instantclient.conf \
    && ldconfig \
    && rm -rf /var/lib/apt/lists/* /tmp/instantclient-basic.zip

COPY Python/requirements.txt ./Python/requirements.txt
RUN pip install --no-cache-dir -r Python/requirements.txt

COPY Python ./Python

EXPOSE 8501

CMD ["streamlit", "run", "Python/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
