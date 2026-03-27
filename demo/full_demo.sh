#!/bin/bash
# MeshBroker Full Demo Runner
# Runs bounty race then regenerates heartbeat page
set -e
cd "$(dirname "$0")/.."

echo ""
echo "======================================================"
echo " MESHBROKER FULL DEMO — X LAYER TESTNET"
echo "======================================================"
echo ""

echo ">>> STEP 1: Generating Heartbeat page (pre-race state)..."
python3 scripts/generate_heartbeat.py

echo ""
echo ">>> STEP 2: Running Bounty Race (multi-agent competition)..."
python3 demo/bounty_race.py

echo ""
echo ">>> STEP 3: Regenerating Heartbeat page (post-race state)..."
python3 scripts/generate_heartbeat.py

echo ""
echo ">>> STEP 4: Opening Heartbeat page in browser..."
open heartbeat.html 2>/dev/null || xdg-open heartbeat.html 2>/dev/null || echo "Open heartbeat.html manually in your browser."

echo ""
echo "======================================================"
echo " DEMO COMPLETE. Copy TX hashes above into README."
echo "======================================================"
