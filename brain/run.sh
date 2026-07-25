#!/bin/bash

LOG=server.log

echo "[*] Starting Flask: $(date)" | tee -a "$LOG"

cd "$HOME/Desktop/my-smart-home/brain"
source venv/bin/activate
python main.py

echo "[*] Connection ended: $(date)" | tee -a "$LOG"