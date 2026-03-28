import os, sys, time
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from web3 import Web3
from dotenv import load_dotenv
load_dotenv()

RPC_URL              = os.getenv("RPC_URL")
MESHBROKER_ADDRESS   = Web3.to_checksum_address(os.getenv("MESHBROKER_ADDRESS"))
USDT_ADDRESS         = Web3.to_checksum_address(os.getenv("USDT_ADDRESS"))
WORKER_PRIVATE_KEY   = os.getenv("WORKER_PRIVATE_KEY")
VERIFIER_PRIVATE_KEY = os.getenv("VERIFIER_PRIVATE_KEY")

w3 = Web3(Web3.HTTPProvider(RPC_URL))

USDT_ABI = [{"name":"balanceOf","type":"function","stateMutability":"view",
             "inputs":[{"name":"account","type":"address"}],
             "outputs":[{"name":"","type":"uint256"}]}]
TREASURY_ABI = [{"name":"protocolTreasury","type":"function","stateMutability":"view",
                 "inputs":[{"name":"","type":"address"}],
                 "outputs":[{"name":"","type":"uint256"}]}]

usdt      = w3.eth.contract(address=USDT_ADDRESS,    abi=USDT_ABI)
meshbroker = w3.eth.contract(address=MESHBROKER_ADDRESS, abi=TREASURY_ABI)

worker_addr   = w3.eth.account.from_key(WORKER_PRIVATE_KEY).address
verifier_addr = w3.eth.account.from_key(VERIFIER_PRIVATE_KEY).address

try:
    block        = w3.eth.block_number
    escrow       = usdt.functions.balanceOf(MESHBROKER_ADDRESS).call() / 1_000_000
    treasury     = meshbroker.functions.protocolTreasury(USDT_ADDRESS).call() / 1_000_000
    buyer_bal    = usdt.functions.balanceOf(verifier_addr).call() / 1_000_000
    worker_bal   = usdt.functions.balanceOf(worker_addr).call() / 1_000_000
    connected    = True
except Exception as e:
    block = escrow = treasury = buyer_bal = worker_bal = 0
    connected = False

updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

agents = [
    {"name":"MeshVerifier-Prime","address":verifier_addr,"specialty":"SECURITY",
     "score":84,"tier":"GOLD","tier_color":"#ffb700","completed":5,"slashed":0,
     "stake":10.0,"balance":buyer_bal,
     "tx":"d9235160a3cf517c6d39d33a2ad01baedf3f6a3dc87618c3cdb00e5d54da190b"},
    {"name":"MeshWorker-Alpha","address":worker_addr,"specialty":"MARKET DATA",
     "score":30,"tier":"BRONZE","tier_color":"#cd7f32","completed":0,"slashed":0,
     "stake":10.0,"balance":worker_bal,
     "tx":"2436d4facb021c9f2166c89784a723751ff9e19840afaa66f3cc33542912d77b"},
]

txs = [
    ("Bounty 1 Post",       "32dc7734084f1ef96ba03bb77a847ca0765d46433906e51c1301cd393e3d5240"),
    ("Alpha Accept + Proof","46c6634f8c9890267fc836966e73c18ed224604a01a30287192d25fbcc6f0254"),
    ("Alpha Settlement",    "7d0c2e04f842b038d23e8418a2e0a6d950f262c4de0aa99315a45a1301f69488"),
    ("Bounty 2 Post",       "30914746a9e87e6ece84feea9aea3377cbf0df8e4600103a183968aab9e1cd54"),
    ("Beta Accept + Proof", "004dd4757e967c12ba070c54354a9c1adb0c260bdb3e060822b2788e70e8c6b9"),
    ("Buyer USDT Approve",  "167854dba736462df860fa592b19014834f8104e17c8311da04e7f619b4a6845"),
    ("createSLA — lock",    "f01c67f3b5e386982dba314a3ec1e3603c4c0d79dde39182b3ea4a6d6f0314d3"),
    ("Worker USDT Approve", "ab8fc55ec84e3b984abcfb5143edb4b395b84af253dd797bc35a79e4ab240020"),
    ("acceptSLA",           "962cfaa5ca1de4cb36926e49911180e02c5a512418cea07ec1ba331ff6526ad6"),
    ("submitProof",         "fe78dd2afa1d28e5b702b2dd608ba2ef75cecff136261944158690d63d13942e"),
    ("verifyAndRelease",    "d9235160a3cf517c6d39d33a2ad01baedf3f6a3dc87618c3cdb00e5d54da190b"),
    ("Agent Registration",  "2436d4facb021c9f2166c89784a723751ff9e19840afaa66f3cc33542912d77b"),
]

def agent_card(a):
    bar_color = a["tier_color"]
    return f"""
<div class="agent-card" style="border-color:{bar_color}22;">
  <div class="agent-top">
    <div class="agent-left">
      <span class="tier-badge" style="background:{bar_color}22;color:{bar_color};border-color:{bar_color}44;">{a["tier"]}</span>
      <span class="agent-name">{a["name"]}</span>
      <span class="active-dot">ACTIVE</span>
    </div>
  </div>
  <div class="agent-addr">{a["address"][:6]}...{a["address"][-6:]}&nbsp;&nbsp;{a["specialty"]}</div>
  <div class="rep-label">REPUTATION SCORE <span style="color:{bar_color};float:right;font-weight:700;">{a["score"]}.0/100</span></div>
  <div class="rep-bar-bg"><div class="rep-bar-fill" style="width:{a['score']}%;background:{bar_color};box-shadow:0 0 8px {bar_color}66;"></div></div>
  <div class="agent-stats">
    <div class="stat-box"><div class="stat-val">{a["completed"]}</div><div class="stat-lbl">COMPLETED</div></div>
    <div class="stat-box"><div class="stat-val" style="color:#ff4444;">{a["slashed"]}</div><div class="stat-lbl">SLASHED</div></div>
    <div class="stat-box"><div class="stat-val" style="color:#00d4ff;">{a["stake"]}</div><div class="stat-lbl">STAKE USDT</div></div>
    <div class="stat-box"><div class="stat-val" style="color:#e0e0e0;">{a["balance"]:.1f}</div><div class="stat-lbl">BALANCE</div></div>
  </div>
  <div class="reg-tx">Registry TX &nbsp; {a["tx"][:18]}...</div>
</div>"""

cards_html = "\n".join(agent_card(a) for a in agents)

tx_rows = "\n".join(
    f'<div class="tx-row"><span class="tx-label">{label}</span>'
    f'<span class="tx-dot"></span>'
    f'<a class="tx-hash" href="https://www.okx.com/explorer/xlayer-test/tx/0x{h}" target="_blank">{h[:8]}...{h[-8:]}</a></div>'
    for label, h in txs
)

conn_color = "#00ff9d" if connected else "#ff4444"
conn_text  = "CONNECTED" if connected else "OFFLINE"

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<meta http-equiv="refresh" content="30"/>
<title>MeshBroker · Agent Heartbeat</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' fill='%23000'/%3E%3Ccircle cx='16' cy='16' r='3' fill='%2300d4ff'/%3E%3Ccircle cx='9' cy='9' r='2.5' fill='%23fff' fill-opacity='.3'/%3E%3Ccircle cx='23' cy='9' r='2.5' fill='%2300d4ff'/%3E%3Ccircle cx='9' cy='23' r='2.5' fill='%2300d4ff'/%3E%3Ccircle cx='23' cy='23' r='2.5' fill='%23fff' fill-opacity='.3'/%3E%3C/svg%3E"/>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&family=Space+Grotesk:wght@400;500;600;700&family=Outfit:wght@700;800;900&display=swap" rel="stylesheet"/>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#050810;--bg2:#080d14;--bg3:#0c1219;
  --b1:#0e1a26;--b2:#162436;
  --cyan:#00d4ff;--green:#00ff9d;--amber:#ffb700;--red:#ff4444;
  --text:#a8c0d0;--dim:#3a5a6a;
  --mono:'JetBrains Mono',monospace;
  --sans:'Outfit','Space Grotesk',sans-serif;
}}
html,body{{min-height:100vh;background:var(--bg);color:var(--text);font-family:var(--mono)}}
body{{background-image:linear-gradient(rgba(0,212,255,.02) 1px,transparent 1px),linear-gradient(90deg,rgba(0,212,255,.02) 1px,transparent 1px);background-size:52px 52px;}}
.page{{max-width:1280px;margin:0 auto;padding:32px 36px 48px}}

.hdr{{display:flex;align-items:center;justify-content:space-between;margin-bottom:32px;padding-bottom:22px;border-bottom:1px solid var(--b1);flex-wrap:wrap;gap:16px;}}
.logo{{display:flex;align-items:center;gap:14px}}
.logo-box{{width:44px;height:44px;border:2px solid var(--cyan);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:22px;color:var(--cyan);box-shadow:0 0 20px rgba(0,212,255,.25);}}
.logo-name{{font-family:var(--sans);font-size:22px;font-weight:800;color:#fff;letter-spacing:-.5px}}
.logo-name b{{color:var(--cyan)}}
.logo-sub{{font-size:9px;letter-spacing:.22em;color:var(--dim);text-transform:uppercase;margin-top:3px}}
.hdr-right{{display:flex;align-items:center;gap:20px;flex-wrap:wrap}}
.conn-badge{{display:flex;align-items:center;gap:9px;padding:8px 16px;border:1px solid var(--b2);border-radius:8px;background:var(--bg2);}}
.dot-pulse{{width:9px;height:9px;border-radius:50%;background:{conn_color};box-shadow:0 0 10px {conn_color};animation:pulse 1.8s ease-in-out infinite;}}
@keyframes pulse{{0%,100%{{opacity:1;transform:scale(1)}}50%{{opacity:.6;transform:scale(.85)}}}}
.conn-text{{font-size:11px;letter-spacing:.12em;color:{conn_color};font-weight:600;}}
.updated{{font-size:10px;color:var(--dim);text-align:right;line-height:1.6}}

.stats-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:16px;margin-bottom:32px}}
@media(max-width:900px){{.stats-grid{{grid-template-columns:repeat(2,1fr)}}}}
.stat-card{{background:var(--bg2);border:1px solid var(--b2);border-radius:12px;padding:20px 18px;}}
.stat-card-label{{font-size:9px;letter-spacing:.18em;color:var(--dim);text-transform:uppercase;margin-bottom:10px}}
.stat-card-val{{font-family:var(--sans);font-size:26px;font-weight:800;line-height:1}}

.section-hdr{{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}}
.section-title{{font-size:9px;letter-spacing:.2em;color:var(--dim);text-transform:uppercase;display:flex;align-items:center;gap:10px}}
.section-title::before{{content:'';display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--cyan);box-shadow:0 0 8px var(--cyan);}}
.section-count{{font-size:10px;color:var(--dim);letter-spacing:.1em}}

.agents-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px;margin-bottom:32px}}
.agent-card{{background:var(--bg2);border:1px solid;border-radius:14px;padding:20px;}}
.agent-top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}}
.agent-left{{display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
.tier-badge{{font-size:9px;font-weight:700;letter-spacing:.12em;padding:3px 8px;border-radius:4px;border:1px solid;}}
.agent-name{{font-family:var(--sans);font-size:16px;font-weight:700;color:#fff}}
.active-dot{{font-size:9px;letter-spacing:.12em;color:var(--green);padding:2px 8px;border:1px solid #00ff9d33;border-radius:4px;background:#00ff9d0a;}}
.agent-addr{{font-size:10px;color:var(--dim);margin-bottom:14px;letter-spacing:.04em}}
.rep-label{{font-size:9px;letter-spacing:.14em;color:var(--dim);text-transform:uppercase;margin-bottom:6px}}
.rep-bar-bg{{height:4px;background:var(--b2);border-radius:2px;margin-bottom:14px}}
.rep-bar-fill{{height:100%;border-radius:2px;transition:width .3s}}
.agent-stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:12px}}
.stat-box{{background:var(--bg3);border-radius:6px;padding:8px;text-align:center}}
.stat-val{{font-family:var(--sans);font-size:17px;font-weight:700;color:#e0e0e0}}
.stat-lbl{{font-size:8px;letter-spacing:.12em;color:var(--dim);text-transform:uppercase;margin-top:2px}}
.reg-tx{{font-size:9px;color:var(--dim);letter-spacing:.04em;padding-top:10px;border-top:1px solid var(--b1)}}

.tx-feed{{background:var(--bg2);border:1px solid var(--b2);border-radius:14px;padding:20px;margin-bottom:32px}}
.tx-row{{display:flex;align-items:center;gap:12px;padding:9px 0;border-bottom:1px solid var(--b1);font-size:11px;}}
.tx-row:last-child{{border-bottom:none}}
.tx-label{{color:var(--text);flex:1;min-width:160px}}
.tx-dot{{width:6px;height:6px;border-radius:50%;background:var(--green);box-shadow:0 0 6px var(--green);flex-shrink:0}}
.tx-hash{{color:var(--cyan);text-decoration:none;font-family:var(--mono);letter-spacing:.04em}}
.tx-hash:hover{{text-decoration:underline}}

.footer{{text-align:center;padding-top:24px;border-top:1px solid var(--b1);font-size:10px;color:var(--dim);letter-spacing:.1em;line-height:2}}
.footer a{{color:var(--cyan);text-decoration:none}}
</style>
</head>
<body>
<div class="page">

<div class="hdr">
  <div class="logo">
    <div class="logo-box">&#9672;</div>
    <div>
      <div class="logo-name">Mesh<b>Broker</b></div>
      <div class="logo-sub">Agent Trust Heartbeat</div>
    </div>
  </div>
  <div class="hdr-right">
    <div class="conn-badge">
      <div class="dot-pulse"></div>
      <span class="conn-text">{conn_text}</span>
    </div>
    <div class="updated">Updated: {updated}<br/>Auto-refresh every 30s</div>
  </div>
</div>

<div class="section-hdr"><div class="section-title">Protocol Statistics &nbsp;·&nbsp; X Layer Testnet (zkEVM)</div></div>
<div class="stats-grid">
  <div class="stat-card"><div class="stat-card-label">Latest Block</div><div class="stat-card-val" style="color:var(--cyan)">#{block:,}</div></div>
  <div class="stat-card"><div class="stat-card-label">Escrow Balance</div><div class="stat-card-val" style="color:var(--cyan)">{escrow:.2f} <span style="font-size:14px;color:var(--dim)">USDT</span></div></div>
  <div class="stat-card"><div class="stat-card-label">Protocol Treasury</div><div class="stat-card-val" style="color:var(--amber)">{treasury:.2f} <span style="font-size:14px;color:var(--dim)">USDT</span></div></div>
  <div class="stat-card"><div class="stat-card-label">Buyer Balance</div><div class="stat-card-val">{buyer_bal:.2f} <span style="font-size:14px;color:var(--dim)">USDT</span></div></div>
  <div class="stat-card"><div class="stat-card-label">Worker Balance</div><div class="stat-card-val">{worker_bal:.2f} <span style="font-size:14px;color:var(--dim)">USDT</span></div></div>
</div>

<div class="section-hdr">
  <div class="section-title">Registered Agents</div>
  <div class="section-count">{len(agents)} active</div>
</div>
<div class="agents-grid">{cards_html}</div>

<div class="section-hdr">
  <div class="section-title">Confirmed On-Chain Transactions</div>
  <div class="section-count">{len(txs)} total</div>
</div>
<div class="tx-feed">{tx_rows}</div>

<div class="footer">
  MeshBroker &nbsp;·&nbsp; Trustless SLA Enforcement for the Agentic Economy<br/>
  Built on X Layer (zkEVM) &nbsp;·&nbsp; OKX Onchain OS AI Hackathon 2026<br/>
  <a href="https://github.com/Vinaystwt/meshbroker-agents" target="_blank">GitHub</a>
  &nbsp;&nbsp;·&nbsp;&nbsp;
  <a href="https://meshbroker.netlify.app" target="_blank">meshbroker.netlify.app</a>
  &nbsp;&nbsp;·&nbsp;&nbsp;
  <a href="https://twitter.com/vinaystwt" target="_blank">@vinaystwt</a>
</div>

</div>
</body>
</html>"""

out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "heartbeat.html")
with open(out, "w") as f:
    f.write(html)

print(f"Heartbeat generated: {out}")
print(f"Block: #{block:,} | Escrow: {escrow:.2f} USDT | Treasury: {treasury:.4f} USDT")
