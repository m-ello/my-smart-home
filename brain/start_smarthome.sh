#!/bin/bash
# start_smarthome.sh

# cleanup() {
#     echo "[*] Stopping hotspot..."
#     nmcli connection down "PEPS1"
# }
# trap cleanup EXIT

# echo "[*] Starting the Hotspot..."
# nmcli con up "Hotspot"
# sleep 3

echo "[*] Starting Flask..."
cd "$HOME/Desktop/my-smart-home/brain"
source venv/bin/activate
python main.py