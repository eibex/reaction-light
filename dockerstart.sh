#!/bin/bash

# Required enviormental variable
if [ -z "$TOKEN" ]; then
   echo "TOKEN environment variable not set."
   exit 1
fi

cd /bot

echo "[server]
token = $TOKEN
name = $NAME
system_channel = $SYSTEM_CHANNEL
logo = $LOGO
colour = $COLOUR
language = $LANGUAGE" > config.ini

python3 ./bot.py