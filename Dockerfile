FROM python:3.13-slim

# 1) Install cron
RUN apt-get update && \
    apt-get install -y cron && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2) Copy dependencies and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 3) Copy application code + entrypoint
COPY ./app /app
COPY entrypoint.sh /app/entrypoint.sh

# 4) Copy default crontab into cron.d
COPY python-cron /etc/cron.d/python-cron
RUN chmod 0644 /etc/cron.d/python-cron

# 5) Prepare cron-log and make entrypoint executable
RUN touch /var/log/cron.log
RUN chmod +x /app/entrypoint.sh

# 6) Launch entrypoint (starts cron & tails log)
ENTRYPOINT ["/app/entrypoint.sh"]