"""
MeshBroker Heartbeat Generator
Reads real on-chain events → generates heartbeat.html
Open the HTML file in any browser. Zero dependencies, zero hosting.
"""
import os, sys, time
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web3 import Web3
from dotenv import load_dotenv
from core.reputation import get_onchain_reputation

load_dotenv()

def generate():
    w3        = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
    mesh_addr = Web3.to_checksum_address(os.getenv("MESHBROKER_ADDRESS").strip("'\" "))
    usdt_addr = Web3.to_checksum_address(os.getenv("USDT_ADDRESS").strip("'\" "))

    worker_addr   = w3.eth.account.from_key(os.getenv("WORKER_PRIVATE_KEY")).address
    verifier_addr = w3.eth.account.from_key(os.getenv("VERIFIER_PRIVATE_KEY")).address

    agents = [
        {"label": "WorkerAgent",   "address": worker_addr},
        {"label": "VerifierAgent", "address": verifier_addr},
        {"label": "BuyerAgent",    "address": verifier_addr},
    ]

    # Get live USDT balances
    usdt_abi = [{"name":"balanceOf","type":"function","stateMutability":"view",
                 "inputs":[{"name":"account","type":"address"}],
                 "outputs":[{"name":"","type":"uint256"}]}]
    treasury_abi = [{"name":"protocolTreasury","type":"function","stateMutability":"view",
                     "inputs":[{"name":"","type":"address"}],
                     "outputs":[{"name":"","type":"uint256"}]}]
    usdt     = w3.eth.contract(address=usdt_addr, abi=usdt_abi)
    mesh     = w3.eth.contract(address=mesh_addr, abi=treasury_abi)

    try:
        treasury_bal = mesh.functions.protocolTreasury(usdt_addr).call() / 1e6
        contract_bal = usdt.functions.balanceOf(mesh_addr).call() / 1e6
        block_num    = w3.eth.block_number
        connected    = True
    except Exception as e:
        treasury_bal = contract_bal = 0.0
        block_num    = 0
        connected    = False

    # Build agent cards
    rows = ""
    for ag in agents:
        rep = get_onchain_reputation(ag["address"])
        score = rep["trust_score"]
        bar_width = score
        if score >= 80:
            tier_color = "#00ff88"
            tier_bg    = "#003322"
            status_dot = "🟢"
        elif score >= 50:
            tier_color = "#ffd700"
            tier_bg    = "#332200"
            status_dot = "🟡"
        else:
            tier_color = "#ff4444"
            tier_bg    = "#330000"
            status_dot = "🔴"

        try:
            bal = usdt.functions.balanceOf(ag["address"]).call() / 1e6
        except:
            bal = 0.0

        rows += f"""
        <div class="agent-card">
          <div class="agent-header">
            <span class="status-dot">{status_dot}</span>
            <span class="agent-name">{ag['label']}</span>
            <span class="tier-badge" style="background:{tier_bg};color:{tier_color}">{rep['tier']}</span>
          </div>
          <div class="agent-addr">{ag['address']}</div>
          <div class="stats-row">
            <div class="stat"><div class="stat-val">{score}</div><div class="stat-lbl">Trust Score</div></div>
            <div class="stat"><div class="stat-val">{rep['jobs_completed']}</div><div class="stat-lbl">Jobs Done</div></div>
            <div class="stat"><div class="stat-val">{rep['jobs_slashed']}</div><div class="stat-lbl">Slashes</div></div>
            <div class="stat"><div class="stat-val">{bal:.2f}</div><div class="stat-lbl">USDT Bal</div></div>
          </div>
          <div class="bar-container">
            <div class="bar-fill" style="width:{bar_width}%;background:{tier_color}"></div>
          </div>
          <div class="bar-labels"><span>0</span><span>Trust Score: {score}/100</span><span>100</span></div>
        </div>"""

    status_color = "#00ff88" if connected else "#ff4444"
    status_text  = f"CONNECTED — Block #{block_num}" if connected else "RPC OFFLINE"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MeshBroker Agent Heartbeat — X Layer</title>
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{background:#0a0a0f;color:#e0e0e0;font-family:'SF Mono',monospace;padding:24px}}
  .header{{border-bottom:1px solid #1a1a2e;padding-bottom:16px;margin-bottom:24px}}
  .title{{font-size:22px;font-weight:700;color:#fff;letter-spacing:1px}}
  .subtitle{{font-size:12px;color:#666;margin-top:4px}}
  .network-badge{{display:inline-flex;align-items:center;gap:6px;background:#0d1117;
    border:1px solid #30363d;border-radius:4px;padding:4px 10px;font-size:11px;
    color:{status_color};margin-top:8px}}
  .protocol-stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:24px}}
  .proto-card{{background:#0d1117;border:1px solid #1e3a5f;border-radius:8px;padding:16px;text-align:center}}
  .proto-val{{font-size:24px;font-weight:700;color:#4fc3f7}}
  .proto-lbl{{font-size:11px;color:#666;margin-top:4px;text-transform:uppercase;letter-spacing:1px}}
  .section-title{{font-size:13px;font-weight:600;color:#888;text-transform:uppercase;
    letter-spacing:2px;margin-bottom:12px}}
  .agent-card{{background:#0d1117;border:1px solid #1e3a5f;border-radius:8px;
    padding:16px;margin-bottom:12px}}
  .agent-header{{display:flex;align-items:center;gap:10px;margin-bottom:6px}}
  .status-dot{{font-size:14px}}
  .agent-name{{font-size:15px;font-weight:700;color:#fff;flex:1}}
  .tier-badge{{font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px}}
  .agent-addr{{font-size:10px;color:#444;margin-bottom:12px;font-family:monospace}}
  .stats-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:12px}}
  .stat{{text-align:center;background:#12121a;border-radius:4px;padding:8px}}
  .stat-val{{font-size:18px;font-weight:700;color:#e0e0e0}}
  .stat-lbl{{font-size:10px;color:#555;margin-top:2px;text-transform:uppercase}}
  .bar-container{{background:#1a1a2e;border-radius:4px;height:6px;overflow:hidden;margin-bottom:4px}}
  .bar-fill{{height:100%;border-radius:4px;transition:width 0.3s ease}}
  .bar-labels{{display:flex;justify-content:space-between;font-size:10px;color:#444}}
  .footer{{text-align:center;margin-top:24px;font-size:11px;color:#333;border-top:1px solid #1a1a2e;padding-top:16px}}
  .generated{{color:#444;font-size:10px;text-align:right;margin-top:4px}}
</style>
</head>
<body>
<div class="header">
  <div class="title">⚡ MESHBROKER AGENT HEARTBEAT</div>
  <div class="subtitle">Live trust scores · On-chain reputation · X Layer Testnet</div>
  <div class="network-badge">● {status_text} &nbsp;|&nbsp; Contract: {mesh_addr[:10]}...{mesh_addr[-6:]}</div>
</div>

<div class="protocol-stats">
  <div class="proto-card">
    <div class="proto-val">{contract_bal:.2f}</div>
    <div class="proto-lbl">Escrow Balance (USDT)</div>
  </div>
  <div class="proto-card">
    <div class="proto-val">{treasury_bal:.4f}</div>
    <div class="proto-lbl">Protocol Treasury (USDT)</div>
  </div>
  <div class="proto-card">
    <div class="proto-val">#{block_num:,}</div>
    <div class="proto-lbl">Current Block</div>
  </div>
</div>

<div class="section-title">Agent Reputation Ledger</div>
{rows}

<div class="footer">
  MeshBroker — Trustless SLA Enforcement for the Agentic Economy<br>
  Built on X Layer (zkEVM) · OKX Onchain OS Hackathon 2026
</div>
<div class="generated">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} UTC</div>
</body>
</html>"""

    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "heartbeat.html")
    with open(out, "w") as f:
        f.write(html)
    print(f"\n✅ Heartbeat page generated: {out}")
    print(f"   Open in browser: open heartbeat.html\n")

if __name__ == "__main__":
    generate()
