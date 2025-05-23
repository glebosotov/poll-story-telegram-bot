#!/bin/bash

# Ensure logs directory exists & correct perms
mkdir -p /app/logs
chmod -R 755 /app/logs

env > /etc/environment

echo "Saved" $(cat /etc/environment | wc -l) env variables

# Install cron entries into root's crontab
crontab /etc/cron.d/python-cron

# Optional: verify installation (for debugging)
echo "Installed cron entries:" && crontab -l

# Start cron in foreground, then tail its log
cron && tail -f /var/log/cron.log