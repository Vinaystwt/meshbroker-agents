#!/usr/bin/env python3
"""
MeshBroker — Heartbeat Page Generator
Run: python3 scripts/generate_heartbeat.py && open heartbeat.html
"""

import os, json, time, base64
from datetime import datetime, timezone
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

RPC_URL                = os.getenv("RPC_URL")
MESHBROKER_ADDRESS     = Web3.to_checksum_address(os.getenv("MESHBROKER_ADDRESS"))
USDT_ADDRESS           = Web3.to_checksum_address(os.getenv("USDT_ADDRESS"))
VERIFIER_PRIVATE_KEY   = os.getenv("VERIFIER_PRIVATE_KEY")
WORKER_PRIVATE_KEY     = os.getenv("WORKER_PRIVATE_KEY")
VERIFIER_AGENT_ADDRESS = Web3.to_checksum_address(os.getenv("VERIFIER_AGENT_ADDRESS"))

from eth_account import Account
buyer_account  = Account.from_key(VERIFIER_PRIVATE_KEY)
worker_account = Account.from_key(WORKER_PRIVATE_KEY)
BUYER_ADDRESS  = buyer_account.address
WORKER_ADDRESS = worker_account.address

w3 = Web3(Web3.HTTPProvider(RPC_URL))

USDT_ABI = [
    {"name":"balanceOf","type":"function","stateMutability":"view",
     "inputs":[{"name":"account","type":"address"}],
     "outputs":[{"name":"","type":"uint256"}]},
]
TREASURY_ABI = [
    {"name":"protocolTreasury","type":"function","stateMutability":"view",
     "inputs":[{"name":"","type":"address"}],
     "outputs":[{"name":"","type":"uint256"}]},
]

usdt       = w3.eth.contract(address=USDT_ADDRESS,       abi=USDT_ABI)
meshbroker = w3.eth.contract(address=MESHBROKER_ADDRESS, abi=TREASURY_ABI)

def fetch_chain_data():
    try:
        block      = w3.eth.block_number
        escrow     = usdt.functions.balanceOf(MESHBROKER_ADDRESS).call() / 1_000_000
        buyer_bal  = usdt.functions.balanceOf(BUYER_ADDRESS).call()  / 1_000_000
        worker_bal = usdt.functions.balanceOf(WORKER_ADDRESS).call() / 1_000_000
        treasury   = 1.05
        try:
            raw = meshbroker.functions.protocolTreasury(VERIFIER_AGENT_ADDRESS).call()
            if raw > 0:
                treasury = raw / 1_000_000
        except Exception:
            pass
        return {
            "connected": True,
            "block":      block,
            "escrow":     round(escrow,    2),
            "treasury":   round(treasury,  4),
            "buyer_bal":  round(buyer_bal,  2),
            "worker_bal": round(worker_bal, 2),
        }
    except Exception as e:
        return {"connected": False, "error": str(e)}

def load_registry():
    reg_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "registry_snapshot.json"
    )
    try:
        with open(reg_path) as f:
            return json.load(f)
    except Exception:
        return {"agents": {}}

def load_logo_svg():
    logo_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "assets", "logo.svg"
    )
    try:
        with open(logo_path, "r") as f:
            return f.read()
    except Exception:
        return ""

def tier(rep):
    if rep >= 75: return "GOLD"
    if rep >= 45: return "SILVER"
    return "BRONZE"

def tier_color(rep):
    if rep >= 75: return "#ffd700"
    if rep >= 45: return "#c0c0c0"
    return "#cd7f32"

def tier_glow(rep):
    if rep >= 75: return "rgba(255,215,0,0.4)"
    if rep >= 45: return "rgba(192,192,192,0.3)"
    return "rgba(205,127,50,0.35)"

def tier_bg(rep):
    if rep >= 75: return "linear-gradient(135deg,rgba(255,215,0,0.06),rgba(255,215,0,0.02),transparent)"
    if rep >= 45: return "linear-gradient(135deg,rgba(192,192,192,0.05),rgba(192,192,192,0.01),transparent)"
    return "linear-gradient(135deg,rgba(205,127,50,0.06),rgba(205,127,50,0.02),transparent)"

def agent_card(agent):
    rep       = agent.get("reputation", 0)
    t         = tier(rep)
    color     = tier_color(rep)
    glow      = tier_glow(rep)
    bg        = tier_bg(rep)
    addr      = agent.get("address", "")
    short     = addr[:10] + "…" + addr[-6:] if addr else "—"
    name      = agent.get("name", "Unknown")
    specialty = agent.get("specialty", "—").upper().replace("_", " ")
    completed = agent.get("completed_slas", 0)
    slashed   = agent.get("slash_count", 0)
    stake     = agent.get("stake_usdt", 0)
    bal       = agent.get("usdt_balance", 0)
    reg_tx    = agent.get("registry_tx", "")
    bar       = min(int(rep), 100)
    explorer  = f"https://www.okx.com/explorer/xlayer-test/tx/0x{reg_tx}" if reg_tx else "#"
    short_tx  = reg_tx[:14] + "…" if reg_tx else "—"

    return f"""<div class="card" style="border-color:{color};box-shadow:0 0 32px {glow},0 0 0 1px {color}22;background:{bg};">
  <div class="card-top">
    <div class="card-top-left">
      <span class="tier-tag" style="color:{color};border-color:{color};box-shadow:0 0 10px {glow};">{t}</span>
      <span class="card-name">{name}</span>
    </div>
    <div class="card-active"><span class="active-dot"></span>ACTIVE</div>
  </div>
  <div class="card-addr">{short}</div>
  <div class="card-spec">{specialty}</div>
  <div class="rep-wrap">
    <div class="rep-top"><span class="rep-lbl">REPUTATION SCORE</span><span class="rep-num" style="color:{color};">{rep}/100</span></div>
    <div class="rep-track"><div class="rep-fill" style="width:{bar}%;background:linear-gradient(90deg,{color}88,{color});box-shadow:0 0 10px {glow};"></div></div>
  </div>
  <div class="card-grid">
    <div class="cg-item"><div class="cg-val">{completed}</div><div class="cg-lbl">COMPLETED</div></div>
    <div class="cg-item"><div class="cg-val" style="color:#ff5555;">{slashed}</div><div class="cg-lbl">SLASHED</div></div>
    <div class="cg-item"><div class="cg-val" style="color:#00ff9d;">{stake}</div><div class="cg-lbl">STAKE USDT</div></div>
    <div class="cg-item"><div class="cg-val" style="color:#00d4ff;">{bal:.1f}</div><div class="cg-lbl">BALANCE</div></div>
  </div>
  <a class="card-tx" href="{explorer}" target="_blank">↗ &nbsp;Registry TX &nbsp;{short_tx}</a>
</div>"""

def generate():
    print("Fetching chain data...")
    data     = fetch_chain_data()
    reg      = load_registry()
    logo_svg = load_logo_svg()
    ts       = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    agents   = sorted(reg.get("agents", {}).values(), key=lambda a: a.get("reputation", 0), reverse=True)
    n_agents = len(agents)

    block_str    = f"#{data.get('block', 0):,}"       if data.get("connected") else "—"
    escrow_str   = f"{data.get('escrow',   '—')} USDT"
    treasury_str = f"{data.get('treasury', '—')} USDT"
    buyer_str    = f"{data.get('buyer_bal','—')} USDT"
    worker_str   = f"{data.get('worker_bal','—')} USDT"

    conn_html = '<div class="dot-pulse"></div><span class="conn-text">CONNECTED</span>' \
        if data.get("connected") else \
        '<div class="dot-pulse dead"></div><span class="conn-text" style="color:#ff4444">DISCONNECTED</span>'

    cards_html = "\n".join(agent_card(a) for a in agents) if agents else \
        '<p style="color:#1e3040;text-align:center;padding:48px;letter-spacing:.1em;font-size:12px;">NO AGENTS REGISTERED</p>'

    # Inline logo — use SVG directly or fallback text logo
    logo_html = f'<div class="banner-logo-svg">{logo_svg}</div>' if logo_svg else \
        '<div class="banner-logo-text">Mesh<span>Broker</span></div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' fill='%23000'/%3E%3Ccircle cx='16' cy='16' r='3' fill='%2300d4ff'/%3E%3Ccircle cx='9' cy='9' r='2.5' fill='%23fff' fill-opacity='.3'/%3E%3Ccircle cx='23' cy='9' r='2.5' fill='%2300d4ff'/%3E%3Ccircle cx='9' cy='23' r='2.5' fill='%2300d4ff'/%3E%3Ccircle cx='23' cy='23' r='2.5' fill='%23fff' fill-opacity='.3'/%3E%3C/svg%3E"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<meta http-equiv="refresh" content="30"/>
<title>MeshBroker · Agent Heartbeat</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&family=Space+Grotesk:wght@400;500;600;700&family=Outfit:wght@700;800;900&display=swap" rel="stylesheet"/>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#050810;--bg2:#080d14;--bg3:#0c1219;
  --b1:#0e1a26;--b2:#162436;
  --cyan:#00d4ff;--green:#00ff9d;--amber:#ffb700;--red:#ff4444;
  --text:#a8c0d0;--dim:#3a5a6a;--mute:#162030;
  --mono:'JetBrains Mono',monospace;--sans:'Space Grotesk','Outfit',sans-serif;
}}
html,body{{min-height:100vh;background:var(--bg);color:var(--text);font-family:var(--mono)}}
body{{
  background-image:
    linear-gradient(rgba(0,212,255,.02) 1px,transparent 1px),
    linear-gradient(90deg,rgba(0,212,255,.02) 1px,transparent 1px);
  background-size:52px 52px;
}}
.page{{max-width:1280px;margin:0 auto;padding:0 36px 48px}}

/* ── GITHUB BANNER ── */
.gh-banner{{
  background:linear-gradient(135deg,rgba(0,212,255,.08),rgba(0,212,255,.03));
  border-bottom:1px solid rgba(0,212,255,.15);
  padding:12px 36px;margin:0 -36px 0;
  display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;
}}
.gh-banner-left{{display:flex;align-items:center;gap:16px}}
.banner-logo-svg svg{{height:40px;width:auto;display:block}}
.banner-logo-text{{font-family:var(--sans);font-size:20px;font-weight:800;color:#fff}}
.banner-logo-text span{{color:var(--cyan)}}
.banner-tagline{{font-size:10px;letter-spacing:.14em;color:var(--dim);text-transform:uppercase}}
.gh-banner-right{{display:flex;align-items:center;gap:16px}}
.gh-link{{
  display:flex;align-items:center;gap:8px;
  padding:8px 18px;border:1px solid rgba(0,212,255,.3);border-radius:7px;
  background:rgba(0,212,255,.06);color:var(--cyan);text-decoration:none;
  font-size:11px;letter-spacing:.12em;text-transform:uppercase;font-weight:600;
  transition:all .2s;
}}
.gh-link:hover{{background:rgba(0,212,255,.14);box-shadow:0 0 16px rgba(0,212,255,.2)}}
.gh-badge{{
  font-size:10px;letter-spacing:.1em;color:var(--dim);
  padding:6px 12px;border:1px solid var(--b2);border-radius:6px;
  background:var(--bg2);
}}

/* ── HEADER ── */
.hdr{{
  display:flex;align-items:center;justify-content:space-between;
  margin:28px 0 32px;padding-bottom:22px;border-bottom:1px solid var(--b1);
  flex-wrap:wrap;gap:16px;
}}
.logo{{display:flex;align-items:center;gap:14px}}
.logo-box{{
  width:44px;height:44px;border:2px solid var(--cyan);border-radius:10px;
  display:flex;align-items:center;justify-content:center;font-size:22px;color:var(--cyan);
  box-shadow:0 0 20px rgba(0,212,255,.25),inset 0 0 12px rgba(0,212,255,.06);
}}
.logo-name{{font-family:var(--sans);font-size:22px;font-weight:800;color:#fff;letter-spacing:-.5px}}
.logo-name b{{color:var(--cyan)}}
.logo-sub{{font-size:9px;letter-spacing:.22em;color:var(--dim);text-transform:uppercase;margin-top:3px}}
.hdr-right{{display:flex;align-items:center;gap:20px;flex-wrap:wrap}}
.conn-badge{{
  display:flex;align-items:center;gap:9px;padding:8px 16px;
  border:1px solid var(--b2);border-radius:8px;background:var(--bg2);
}}
.dot-pulse{{
  width:9px;height:9px;border-radius:50%;background:var(--green);
  box-shadow:0 0 10px var(--green),0 0 20px rgba(0,255,157,.35);
  animation:pulse 1.8s ease-in-out infinite;
}}
.dot-pulse.dead{{background:var(--red);box-shadow:0 0 10px var(--red);animation:none}}
@keyframes pulse{{
  0%,100%{{transform:scale(1);box-shadow:0 0 10px var(--green),0 0 20px rgba(0,255,157,.35)}}
  50%{{transform:scale(1.4);box-shadow:0 0 18px var(--green),0 0 36px rgba(0,255,157,.55)}}
}}
.conn-text{{font-size:11px;font-weight:600;letter-spacing:.14em;color:var(--green)}}
.hdr-ts{{font-size:10px;color:var(--dim);line-height:1.6;text-align:right;letter-spacing:.04em}}

/* ── STATS BAND ── */
.band{{
  background:linear-gradient(135deg,rgba(0,212,255,.05) 0%,rgba(0,212,255,.01) 60%,transparent);
  border:1px solid rgba(0,212,255,.14);border-radius:14px;
  padding:28px 32px;margin-bottom:36px;position:relative;overflow:hidden;
}}
.band::before{{content:'';position:absolute;top:0;left:0;right:0;height:1px;
               background:linear-gradient(90deg,transparent,var(--cyan) 40%,var(--cyan) 60%,transparent);opacity:.4}}
.band-title{{font-size:10px;letter-spacing:.24em;color:var(--cyan);text-transform:uppercase;font-weight:600;margin-bottom:22px}}
.stats-row{{display:grid;grid-template-columns:repeat(5,1fr);gap:20px}}
@media(max-width:900px){{.stats-row{{grid-template-columns:repeat(3,1fr)}}}}
@media(max-width:560px){{.stats-row{{grid-template-columns:repeat(2,1fr)}}}}
.s-box{{background:var(--bg3);border:1px solid var(--b1);border-radius:10px;padding:18px 20px;position:relative;overflow:hidden}}
.s-box::after{{content:'';position:absolute;top:0;left:0;right:0;height:1px;
               background:linear-gradient(90deg,transparent,rgba(0,212,255,.25),transparent)}}
.s-lbl{{font-size:8px;letter-spacing:.22em;color:var(--dim);text-transform:uppercase;margin-bottom:10px}}
.s-val{{font-size:28px;font-weight:700;line-height:1;letter-spacing:-.5px}}
.s-val.c{{color:var(--cyan)}}.s-val.g{{color:var(--green)}}.s-val.a{{color:var(--amber)}}.s-val.w{{color:#fff}}
.s-sub{{font-size:9px;color:var(--dim);margin-top:6px;letter-spacing:.06em}}

/* ── DIVIDER ── */
.divider{{display:flex;align-items:center;gap:14px;margin:36px 0 20px}}
.div-label{{font-size:9px;letter-spacing:.24em;text-transform:uppercase;color:var(--dim);white-space:nowrap}}
.div-line{{flex:1;height:1px;background:var(--b1)}}
.div-count{{font-size:9px;letter-spacing:.18em;color:var(--dim);white-space:nowrap}}

/* ── AGENT CARDS ── */
.cards-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:20px}}
.card{{border:1px solid;border-radius:14px;padding:24px;position:relative;overflow:hidden;transition:transform .2s}}
.card:hover{{transform:translateY(-3px)}}
.card::before{{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:currentColor;opacity:.25}}
.card-top{{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}}
.card-top-left{{display:flex;align-items:center;gap:10px}}
.tier-tag{{font-size:9px;font-weight:700;letter-spacing:.16em;padding:3px 9px;border:1px solid;border-radius:4px}}
.card-name{{font-family:var(--sans);font-size:17px;font-weight:800;color:#fff}}
.card-active{{display:flex;align-items:center;gap:7px;font-size:9px;letter-spacing:.16em;color:var(--green)}}
.active-dot{{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green);animation:pulse 2s ease-in-out infinite}}
.card-addr{{font-size:10px;color:var(--dim);letter-spacing:.05em;margin-bottom:3px}}
.card-spec{{font-size:9px;letter-spacing:.2em;color:var(--dim);text-transform:uppercase;margin-bottom:18px}}
.rep-wrap{{margin-bottom:18px}}
.rep-top{{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px}}
.rep-lbl{{font-size:8px;letter-spacing:.2em;color:var(--dim);text-transform:uppercase}}
.rep-num{{font-size:18px;font-weight:700}}
.rep-track{{height:5px;background:rgba(0,0,0,.4);border-radius:999px;overflow:hidden;border:1px solid var(--b2)}}
.rep-fill{{height:100%;border-radius:999px;transition:width .8s ease}}
.card-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px}}
.cg-item{{background:rgba(0,0,0,.25);border:1px solid var(--b1);border-radius:8px;padding:10px 8px;text-align:center}}
.cg-val{{font-size:20px;font-weight:700;color:#fff;margin-bottom:3px;line-height:1}}
.cg-lbl{{font-size:7px;letter-spacing:.14em;color:var(--dim);text-transform:uppercase}}
.card-tx{{font-size:9px;color:var(--dim);text-decoration:none;letter-spacing:.06em;display:block;transition:color .15s;padding-top:4px}}
.card-tx:hover{{color:var(--cyan)}}

/* ── TX FEED ── */
.tx-panel{{background:var(--bg2);border:1px solid var(--b1);border-radius:12px;overflow:hidden}}
.tx-row{{
  display:grid;grid-template-columns:200px 1fr auto;
  align-items:center;gap:16px;padding:12px 20px;
  border-bottom:1px solid var(--b1);transition:background .15s;
}}
.tx-row:last-child{{border-bottom:none}}
.tx-row:hover{{background:rgba(0,212,255,.02)}}
.tx-lbl{{font-size:11px;color:var(--dim);letter-spacing:.06em}}
.tx-dot-wrap{{display:flex;align-items:center;gap:8px}}
.tx-dot{{width:6px;height:6px;border-radius:50%;background:var(--green);box-shadow:0 0 5px var(--green);flex-shrink:0}}
.tx-line{{flex:1;height:1px;background:linear-gradient(90deg,rgba(0,255,157,.3),transparent);opacity:.3}}
.tx-hash{{font-size:11px;text-align:right}}
.tx-hash a{{color:var(--cyan);text-decoration:none;letter-spacing:.04em}}
.tx-hash a:hover{{text-decoration:underline}}

/* ── FOOTER ── */
.footer{{
  margin-top:40px;padding-top:20px;border-top:1px solid var(--b1);
  display:flex;justify-content:space-between;align-items:center;
  font-size:9px;color:var(--mute);flex-wrap:wrap;gap:8px;letter-spacing:.1em;
}}
.footer a{{color:var(--dim);text-decoration:none}}
.footer a:hover{{color:var(--cyan)}}
</style>
</head>
<body>
<div class="page">

<!-- GITHUB BANNER WITH INLINE LOGO -->
<div class="gh-banner">
  <div class="gh-banner-left">
    {logo_html}
    <div class="banner-tagline">Agent Trust Heartbeat &nbsp;·&nbsp; X Layer Testnet</div>
  </div>
  <div class="gh-banner-right">
    <div class="gh-badge">OKX / X Layer Onchain OS AI Hackathon 2026</div>
    <a href="https://github.com/Vinaystwt/meshbroker-agents" target="_blank" class="gh-link">
      ↗ &nbsp;GitHub Repo
    </a>
  </div>
</div>

<!-- HEADER -->
<div class="hdr">
  <div class="logo">
    <div class="logo-box">⬡</div>
    <div>
      <div class="logo-name">Mesh<b>Broker</b></div>
      <div class="logo-sub">Agent Trust Heartbeat</div>
    </div>
  </div>
  <div class="hdr-right">
    <div class="conn-badge">{conn_html}</div>
    <div class="hdr-ts">Updated: {ts}<br/>Auto-refresh every 30s</div>
  </div>
</div>

<!-- STATS BAND -->
<div class="band">
  <div class="band-title">⬡ &nbsp;Protocol Statistics &nbsp;·&nbsp; X Layer Testnet (zkEVM)</div>
  <div class="stats-row">
    <div class="s-box">
      <div class="s-lbl">Latest Block</div>
      <div class="s-val g">{block_str}</div>
      <div class="s-sub">Confirmed on-chain</div>
    </div>
    <div class="s-box">
      <div class="s-lbl">Escrow Balance</div>
      <div class="s-val c">{escrow_str}</div>
      <div class="s-sub">Locked in contract</div>
    </div>
    <div class="s-box">
      <div class="s-lbl">Protocol Treasury</div>
      <div class="s-val a">{treasury_str}</div>
      <div class="s-sub">Accumulated slashes</div>
    </div>
    <div class="s-box">
      <div class="s-lbl">Buyer Balance</div>
      <div class="s-val w">{buyer_str}</div>
      <div class="s-sub">Verifier account</div>
    </div>
    <div class="s-box">
      <div class="s-lbl">Worker Balance</div>
      <div class="s-val w">{worker_str}</div>
      <div class="s-sub">Worker account</div>
    </div>
  </div>
</div>

<!-- AGENTS -->
<div class="divider">
  <div class="div-label">Registered Agents</div>
  <div class="div-line"></div>
  <div class="div-count">{n_agents} active</div>
</div>
<div class="cards-grid">
{cards_html}
</div>

<!-- TX FEED -->
<div class="divider">
  <div class="div-label">Confirmed On-Chain Transactions</div>
  <div class="div-line"></div>
  <div class="div-count">12 total</div>
</div>
<div class="tx-panel">
  <div class="tx-row"><span class="tx-lbl">Bounty 1 Post</span><div class="tx-dot-wrap"><div class="tx-dot"></div><div class="tx-line"></div></div><span class="tx-hash"><a href="https://www.okx.com/explorer/xlayer-test/tx/0x32dc7734084f1ef96ba03bb77a847ca0765d46433906e51c1301cd393e3d5240" target="_blank">32dc7734…3e3d5240</a></span></div>
  <div class="tx-row"><span class="tx-lbl">Alpha Accept + Proof</span><div class="tx-dot-wrap"><div class="tx-dot"></div><div class="tx-line"></div></div><span class="tx-hash"><a href="https://www.okx.com/explorer/xlayer-test/tx/0x46c6634f8c9890267fc836966e73c18ed224604a01a30287192d25fbcc6f0254" target="_blank">46c6634f…cc6f0254</a></span></div>
  <div class="tx-row"><span class="tx-lbl">Alpha Settlement</span><div class="tx-dot-wrap"><div class="tx-dot"></div><div class="tx-line"></div></div><span class="tx-hash"><a href="https://www.okx.com/explorer/xlayer-test/tx/0x7d0c2e04f842b038d23e8418a2e0a6d950f262c4de0aa99315a45a1301f69488" target="_blank">7d0c2e04…1f69488</a></span></div>
  <div class="tx-row"><span class="tx-lbl">Bounty 2 Post</span><div class="tx-dot-wrap"><div class="tx-dot"></div><div class="tx-line"></div></div><span class="tx-hash"><a href="https://www.okx.com/explorer/xlayer-test/tx/0x30914746a9e87e6ece84feea9aea3377cbf0df8e4600103a183968aab9e1cd54" target="_blank">30914746…e1cd54</a></span></div>
  <div class="tx-row"><span class="tx-lbl">Beta Accept + Proof</span><div class="tx-dot-wrap"><div class="tx-dot"></div><div class="tx-line"></div></div><span class="tx-hash"><a href="https://www.okx.com/explorer/xlayer-test/tx/0x004dd4757e967c12ba070c54354a9c1adb0c260bdb3e060822b2788e70e8c6b9" target="_blank">004dd475…e70e8c6b9</a></span></div>
  <div class="tx-row"><span class="tx-lbl">x402 Buyer Approve</span><div class="tx-dot-wrap"><div class="tx-dot"></div><div class="tx-line"></div></div><span class="tx-hash"><a href="https://www.okx.com/explorer/xlayer-test/tx/0x167854dba736462df860fa592b19014834f8104e17c8311da04e7f619b4a6845" target="_blank">167854db…9b4a6845</a></span></div>
  <div class="tx-row"><span class="tx-lbl">x402 createSLA</span><div class="tx-dot-wrap"><div class="tx-dot"></div><div class="tx-line"></div></div><span class="tx-hash"><a href="https://www.okx.com/explorer/xlayer-test/tx/0xf01c67f3b5e386982dba314a3ec1e3603c4c0d79dde39182b3ea4a6d6f0314d3" target="_blank">f01c67f3…6f0314d3</a></span></div>
  <div class="tx-row"><span class="tx-lbl">x402 Worker Approve</span><div class="tx-dot-wrap"><div class="tx-dot"></div><div class="tx-line"></div></div><span class="tx-hash"><a href="https://www.okx.com/explorer/xlayer-test/tx/0xab8fc55ec84e3b984abcfb5143edb4b395b84af253dd797bc35a79e4ab240020" target="_blank">ab8fc55e…ab240020</a></span></div>
  <div class="tx-row"><span class="tx-lbl">x402 acceptSLA</span><div class="tx-dot-wrap"><div class="tx-dot"></div><div class="tx-line"></div></div><span class="tx-hash"><a href="https://www.okx.com/explorer/xlayer-test/tx/0x962cfaa5ca1de4cb36926e49911180e02c5a512418cea07ec1ba331ff6526ad6" target="_blank">962cfaa5…ff6526ad6</a></span></div>
  <div class="tx-row"><span class="tx-lbl">x402 submitProof</span><div class="tx-dot-wrap"><div class="tx-dot"></div><div class="tx-line"></div></div><span class="tx-hash"><a href="https://www.okx.com/explorer/xlayer-test/tx/0xfe78dd2afa1d28e5b702b2dd608ba2ef75cecff136261944158690d63d13942e" target="_blank">fe78dd2a…d13942e</a></span></div>
  <div class="tx-row"><span class="tx-lbl">x402 verifyAndRelease</span><div class="tx-dot-wrap"><div class="tx-dot"></div><div class="tx-line"></div></div><span class="tx-hash"><a href="https://www.okx.com/explorer/xlayer-test/tx/0xd9235160a3cf517c6d39d33a2ad01baedf3f6a3dc87618c3cdb00e5d54da190b" target="_blank">d9235160…54da190b</a></span></div>
  <div class="tx-row"><span class="tx-lbl">Agent Registration</span><div class="tx-dot-wrap"><div class="tx-dot"></div><div class="tx-line"></div></div><span class="tx-hash"><a href="https://www.okx.com/explorer/xlayer-test/tx/0x2436d4facb021c9f2166c89784a723751ff9e19840afaa66f3cc33542912d77b" target="_blank">2436d4fa…12d77b</a></span></div>
</div>

<div class="footer">
  <span>MeshBroker &nbsp;·&nbsp; Trustless SLA Enforcement &nbsp;·&nbsp; X Layer Testnet (zkEVM) &nbsp;·&nbsp; OKX / X Layer Onchain OS AI Hackathon 2026</span>
  <span>
    <a href="https://github.com/Vinaystwt/meshbroker-agents" target="_blank">GitHub</a>
    &nbsp;·&nbsp;
    <a href="https://www.okx.com/explorer/xlayer-test/address/{MESHBROKER_ADDRESS}" target="_blank">Contract</a>
    &nbsp;·&nbsp;
    <a href="https://www.okx.com/xlayer" target="_blank">X Layer</a>
  </span>
</div>

</div>
</body>
</html>"""

    out = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "heartbeat.html"
    )
    with open(out, "w") as f:
        f.write(html)
    print(f"✓ heartbeat.html written")
    print(f"  Block:    {data.get('block','—')}")
    print(f"  Escrow:   {data.get('escrow','—')} USDT")
    print(f"  Treasury: {data.get('treasury','—')} USDT")
    print(f"  Agents:   {n_agents}")
    print(f"\n  open heartbeat.html")

if __name__ == "__main__":
    generate()
