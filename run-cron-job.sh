#!/bin/bash

echo "[$(date)] Starting Python script" >> /app/logs/app.log
cd /app
/usr/local/bin/python main.py >> /app/logs/app.log 2>&1
