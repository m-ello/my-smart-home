#!/bin/bash

echo "[*] Waiting for brain at 10.42.0.1..."
until ping -c1 -W2 10.42.0.1 &>/dev/null; do
    sleep 2
done

echo "[*] Brain reached. Starting eyes_n_ears..."
python3 main.py

trap 'echo "[*] Stopped."' EXIT
