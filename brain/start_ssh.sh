#!/bin/bash

HOST=rrr@10.42.0.245
LOG=monitor.log

echo "Started: $(date)" | tee -a "$LOG"

ssh "$HOST" | tee -a "$LOG"

echo "Connection lost: $(date)" | tee -a "$LOG"