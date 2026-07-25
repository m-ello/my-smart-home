#!/bin/bash

LOG=monitor.log

echo "[*] Starting connection: $(date)" | tee -a "$LOG"
echo "[*] Waiting for brain at 10.42.0.1..." | tee -a "$LOG"
until ping -c1 -W2 10.42.0.1 &>/dev/null; do
    sleep 2
done

echo "[*] Brain reached. Starting eyes_n_ears: $(date)" | tee -a "$LOG"

python3 main.py

echo "[*] Stopped: $(date)"