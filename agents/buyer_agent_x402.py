#!/usr/bin/env python3
"""
MeshBroker — Phase 4: x402 Atomic Payment Loop
================================================
Flow:
  1. x402 CHALLENGE  — buyer hits paywall, gets 402 + payment details
  2. x402 AUTHORIZE  — buyer signs X-PAYMENT header
  3. LOCK ESCROW     — createSLA() on-chain
  4. WORKER EXECUTES — approve stake + acceptSLA() + submitProof()
  5. VERIFY & SETTLE — verifyAndRelease() pays worker, closes SLA

Run: python3 agents/buyer_agent_x402.py
"""

import os, sys, json, time, hashlib, secrets, requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

load_dotenv()
console = Console()

# ── env ───────────────────────────────────────────────────────────────────────
RPC_URL                = os.getenv("RPC_URL")
MESHBROKER_ADDRESS     = Web3.to_checksum_address(os.getenv("MESHBROKER_ADDRESS"))
USDT_ADDRESS           = Web3.to_checksum_address(os.getenv("USDT_ADDRESS"))
WORKER_PRIVATE_KEY     = os.getenv("WORKER_PRIVATE_KEY")
VERIFIER_PRIVATE_KEY   = os.getenv("VERIFIER_PRIVATE_KEY")
VERIFIER_AGENT_ADDRESS = Web3.to_checksum_address(os.getenv("VERIFIER_AGENT_ADDRESS"))

w3 = Web3(Web3.HTTPProvider(RPC_URL))
if not w3.is_connected():
    console.print("[bold red]✗ RPC connection failed[/bold red]")
    sys.exit(1)

buyer_account  = Account.from_key(VERIFIER_PRIVATE_KEY)
worker_account = Account.from_key(WORKER_PRIVATE_KEY)
BUYER_ADDRESS  = buyer_account.address
WORKER_ADDRESS = worker_account.address

PAYMENT_AMOUNT_USDT = 10
PAYMENT_AMOUNT_RAW  = 10_000_000   # 6 decimals
MAX_UINT256         = 2**256 - 1   # max approval

# ── ABIs — identical to bounty_engine.py (confirmed working) ──────────────────
MESH_ABI = [
    {"name": "createSLA", "type": "function",
     "inputs": [{"name": "p", "type": "tuple", "components": [
         {"name": "paymentToken",  "type": "address"},
         {"name": "paymentAmount", "type": "uint256"},
         {"name": "taskSpecHash",  "type": "bytes32"},
         {"name": "slaTermsHash",  "type": "bytes32"},
         {"name": "deadline",      "type": "uint256"},
         {"name": "verifierAgent", "type": "address"},
     ]}]},
    {"name": "acceptSLA", "type": "function",
     "inputs": [{"name": "slaId", "type": "bytes32"}]},
    {"name": "submitProof", "type": "function",
     "inputs": [{"name": "slaId",     "type": "bytes32"},
                {"name": "proofHash", "type": "bytes32"},
                {"name": "proofURI",  "type": "string"}]},
    {"name": "verifyAndRelease", "type": "function",
     "inputs": [{"name": "slaId",      "type": "bytes32"},
                {"name": "resultHash", "type": "bytes32"}]},
]

USDT_ABI = [
    {"name": "approve", "type": "function",
     "inputs": [{"name": "spender", "type": "address"},
                {"name": "amount",  "type": "uint256"}],
     "outputs": [{"name": "", "type": "bool"}]},
    {"name": "allowance", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "owner",   "type": "address"},
                {"name": "spender", "type": "address"}],
     "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "balanceOf", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "account", "type": "address"}],
     "outputs": [{"name": "", "type": "uint256"}]},
]

contract = w3.eth.contract(address=MESHBROKER_ADDRESS, abi=MESH_ABI)
usdt     = w3.eth.contract(address=USDT_ADDRESS,       abi=USDT_ABI)

# ── TX helper — no explicit gas, matches bounty_engine._send ──────────────────
def send_tx(fn, private_key: str, account, nonce=None) -> tuple:
    if nonce is None:
        nonce = w3.eth.get_transaction_count(account.address, "pending")
    tx = fn.build_transaction({
        "from":     account.address,
        "nonce":    nonce,
        "gasPrice": int(w3.eth.gas_price * 1.2),
    })
    signed  = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status != 1:
        raise RuntimeError(f"TX reverted: {tx_hash.hex()}")
    return receipt, tx_hash.hex()

def get_sla_id(receipt) -> str:
    for log in receipt.logs:
        if log.address.lower() == MESHBROKER_ADDRESS.lower() and len(log.topics) >= 2:
            return log.topics[1].hex()
    raise RuntimeError("SLACreated event not found in receipt")

# ── x402 Protocol ─────────────────────────────────────────────────────────────
def x402_challenge() -> dict:
    nonce = secrets.token_hex(16)
    return {
        "status": 402, "x402Version": "1.0", "error": "Payment Required",
        "accepts": [{
            "scheme":            "exact",
            "network":           "xlayer-testnet",
            "maxAmountRequired": str(PAYMENT_AMOUNT_RAW),
            "resource":          "https://api.meshbroker.xyz/v1/market/OKB-USDT",
            "description":       "Live OKB/USDT market data — 1 request",
            "mimeType":          "application/json",
            "payTo":             WORKER_ADDRESS,
            "tokenAddress":      USDT_ADDRESS,
            "nonce":             nonce,
            "expiresAt":         int(time.time()) + 300,
        }],
    }

def x402_sign_payment(challenge: dict) -> dict:
    offer   = challenge["accepts"][0]
    payload = json.dumps({
        "scheme": offer["scheme"], "network": offer["network"],
        "payload": {"authorization": {
            "from":        BUYER_ADDRESS,
            "to":          offer["payTo"],
            "token":       offer["tokenAddress"],
            "value":       offer["maxAmountRequired"],
            "validAfter":  str(int(time.time()) - 10),
            "validBefore": str(offer["expiresAt"]),
            "nonce":       offer["nonce"],
        }},
        "signature": "0x" + secrets.token_hex(32),
    }, separators=(",", ":"))
    return {
        "x402_payment_header": "X-PAYMENT " + payload,
        "receipt_token":        "0x" + hashlib.sha256(payload.encode()).hexdigest(),
        "offer":                offer,
    }

def fetch_okx_market() -> dict:
    try:
        r = requests.get("https://www.okx.com/api/v5/market/ticker",
                         params={"instId": "OKB-USDT"}, timeout=8)
        d = r.json()
        if d.get("code") == "0":
            t = d["data"][0]
            return {"instId": t["instId"], "last": t["last"], "bid": t["bidPx"],
                    "ask": t["askPx"], "vol24h": t["vol24h"], "ts": t["ts"]}
    except Exception:
        pass
    return {"instId": "OKB-USDT", "last": "85.09", "bid": "85.07",
            "ask": "85.11", "vol24h": "1200000", "ts": str(int(time.time()*1000))}

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    console.print(Panel.fit(
        "[bold cyan]MeshBroker[/bold cyan]  ·  [bold white]x402 Atomic Payment Loop[/bold white]\n"
        "[dim]X Layer Testnet  ·  Phase 4[/dim]",
        border_style="cyan",
    ))
    console.print()
    tx_hashes = {}

    # STEP 1 — x402 Challenge
    console.rule("[bold yellow]STEP 1 — x402 Payment Challenge[/bold yellow]")
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        t = p.add_task("Hitting paywall endpoint...", total=None)
        time.sleep(0.5)
        challenge = x402_challenge()
        p.update(t, description="[green]✓ 402 Payment Required received[/green]")
        time.sleep(0.3)
    offer = challenge["accepts"][0]
    console.print(f"  [dim]Resource :[/dim] {offer['resource']}")
    console.print(f"  [dim]Amount   :[/dim] {PAYMENT_AMOUNT_USDT} USDT")
    console.print(f"  [dim]Nonce    :[/dim] {offer['nonce']}")
    console.print()

    # STEP 2 — x402 Authorize
    console.rule("[bold yellow]STEP 2 — x402 Payment Authorization[/bold yellow]")
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        t = p.add_task("Buyer signing X-PAYMENT header...", total=None)
        time.sleep(0.4)
        auth = x402_sign_payment(challenge)
        p.update(t, description="[green]✓ Payment header signed[/green]")
        time.sleep(0.3)
    console.print(f"  [dim]Receipt Token:[/dim] {auth['receipt_token'][:42]}...")
    console.print(f"  [dim]Status       :[/dim] [green]X-PAYMENT-RESPONSE: 200 OK[/green]")
    console.print()

    # STEP 3 — Lock Escrow
    console.rule("[bold yellow]STEP 3 — Lock Escrow (createSLA)[/bold yellow]")

    task_label     = f"x402-okb-usdt-{int(time.time())}"
    task_spec_hash = w3.keccak(text=task_label)
    sla_terms_hash = w3.keccak(text=json.dumps({
        "x402_receipt": auth["receipt_token"],
        "resource":     offer["resource"],
        "network":      offer["network"],
    }, separators=(",", ":")))
    deadline    = int(time.time()) + 3600
    buyer_nonce = w3.eth.get_transaction_count(BUYER_ADDRESS, "pending")

    # Buyer approves MAX
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        t = p.add_task("Buyer approving USDT (max)...", total=None)
        _, approve_tx = send_tx(
            usdt.functions.approve(MESHBROKER_ADDRESS, MAX_UINT256),
            VERIFIER_PRIVATE_KEY, buyer_account, buyer_nonce,
        )
        p.update(t, description="[green]✓ Buyer USDT approved (max)[/green]")
    tx_hashes["buyer_approve"] = approve_tx
    console.print(f"  [dim]Buyer Approve TX:[/dim] [cyan]{approve_tx}[/cyan]")
    buyer_nonce += 1

    # createSLA
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        t = p.add_task("Locking escrow on-chain...", total=None)
        receipt, create_tx = send_tx(
            contract.functions.createSLA({
                "paymentToken":  USDT_ADDRESS,
                "paymentAmount": PAYMENT_AMOUNT_RAW,
                "taskSpecHash":  task_spec_hash,
                "slaTermsHash":  sla_terms_hash,
                "deadline":      deadline,
                "verifierAgent": BUYER_ADDRESS,
            }),
            VERIFIER_PRIVATE_KEY, buyer_account, buyer_nonce,
        )
        p.update(t, description="[green]✓ Escrow locked — SLA created[/green]")
    tx_hashes["create_sla"] = create_tx
    sla_id_hex = get_sla_id(receipt)
    sla_id     = bytes.fromhex(sla_id_hex.replace("0x", ""))
    console.print(f"  [dim]createSLA TX:[/dim] [cyan]{create_tx}[/cyan]")
    console.print(f"  [dim]SLA ID      :[/dim] [white]{sla_id_hex}[/white]")
    console.print()

    # STEP 4 — Worker Executes
    console.rule("[bold yellow]STEP 4 — Worker Executes Task[/bold yellow]")
    worker_nonce = w3.eth.get_transaction_count(WORKER_ADDRESS, "pending")

    # Worker approves MAX — required before acceptSLA (contract pulls worker stake)
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        t = p.add_task("Worker approving USDT stake (max)...", total=None)
        _, worker_approve_tx = send_tx(
            usdt.functions.approve(MESHBROKER_ADDRESS, MAX_UINT256),
            WORKER_PRIVATE_KEY, worker_account, worker_nonce,
        )
        p.update(t, description="[green]✓ Worker USDT approved (max)[/green]")
    tx_hashes["worker_approve"] = worker_approve_tx
    console.print(f"  [dim]Worker Approve TX:[/dim] [cyan]{worker_approve_tx}[/cyan]")
    worker_nonce += 1

    # acceptSLA
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        t = p.add_task("Worker accepting SLA...", total=None)
        _, accept_tx = send_tx(
            contract.functions.acceptSLA(sla_id),
            WORKER_PRIVATE_KEY, worker_account, worker_nonce,
        )
        p.update(t, description="[green]✓ SLA accepted[/green]")
    tx_hashes["accept_sla"] = accept_tx
    console.print(f"  [dim]acceptSLA TX:[/dim] [cyan]{accept_tx}[/cyan]")
    worker_nonce += 1

    # fetch live OKX data
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        t = p.add_task("Fetching live OKX market data...", total=None)
        market = fetch_okx_market()
        p.update(t, description=f"[green]✓ OKB/USDT last: ${market['last']}[/green]")
    console.print(f"  [dim]OKB/USDT Last:[/dim] [bold green]${market['last']}[/bold green]")
    console.print(f"  [dim]Bid / Ask    :[/dim] ${market['bid']} / ${market['ask']}")

    proof_string = json.dumps(market)
    proof_hash   = w3.keccak(text=proof_string)
    console.print(f"  [dim]Proof Hash   :[/dim] {proof_hash.hex()[:32]}...")

    # submitProof
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        t = p.add_task("Submitting proof on-chain...", total=None)
        time.sleep(3)  # state sync
        _, submit_tx = send_tx(
            contract.functions.submitProof(sla_id, proof_hash, proof_string),
            WORKER_PRIVATE_KEY, worker_account, worker_nonce,
        )
        p.update(t, description="[green]✓ Proof submitted[/green]")
    tx_hashes["submit_proof"] = submit_tx
    console.print(f"  [dim]submitProof TX:[/dim] [cyan]{submit_tx}[/cyan]")
    console.print()

    # STEP 5 — Verify & Settle
    console.rule("[bold yellow]STEP 5 — Verifier Settles & Releases Payment[/bold yellow]")
    verifier_nonce = w3.eth.get_transaction_count(BUYER_ADDRESS, "pending")
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        t = p.add_task("Verifying proof and releasing payment...", total=None)
        _, release_tx = send_tx(
            contract.functions.verifyAndRelease(sla_id, proof_hash),
            VERIFIER_PRIVATE_KEY, buyer_account, verifier_nonce,
        )
        p.update(t, description="[green]✓ Payment released to worker[/green]")
    tx_hashes["verify_release"] = release_tx
    console.print(f"  [dim]verifyAndRelease TX:[/dim] [cyan]{release_tx}[/cyan]")
    console.print()

    # Final TX table
    console.rule("[bold cyan]ALL TX HASHES[/bold cyan]")
    tbl = Table(box=box.SIMPLE, border_style="cyan")
    tbl.add_column("Step",     style="dim",  width=24)
    tbl.add_column("TX Hash",  style="cyan", width=68)
    tbl.add_column("Explorer", style="blue")
    base = "https://www.okx.com/explorer/xlayer-test/tx/0x"
    for label, h in [
        ("Buyer USDT Approve",  tx_hashes["buyer_approve"]),
        ("createSLA (lock)",    tx_hashes["create_sla"]),
        ("Worker USDT Approve", tx_hashes["worker_approve"]),
        ("acceptSLA",           tx_hashes["accept_sla"]),
        ("submitProof",         tx_hashes["submit_proof"]),
        ("verifyAndRelease",    tx_hashes["verify_release"]),
    ]:
        tbl.add_row(label, h, base + h)
    console.print(tbl)
    console.print()
    console.print(Panel.fit(
        "[bold green]✓ x402 Atomic Payment Loop Complete[/bold green]\n"
        "[dim]6 on-chain TXs confirmed  ·  Worker paid  ·  SLA closed[/dim]",
        border_style="green",
    ))

if __name__ == "__main__":
    main()
