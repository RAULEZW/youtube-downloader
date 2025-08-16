#!/bin/bash

echo "Starting Flask and ngrok..."

cd ~/yt_downloader || exit
source venv/bin/activate
python3 main.py &  # start Flask
sleep 1
ngrok http 5000 &  # start ngrok
