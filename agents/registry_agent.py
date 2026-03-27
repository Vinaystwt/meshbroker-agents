#!/usr/bin/env python3
"""
MeshBroker — Phase 5: Agent Registry
======================================
Workers register themselves on-chain by posting a minimal SLA to MeshBroker
(createSLA with taskSpecHash encoding their specialty + stake). Registration
is a REAL on-chain TX — the SLA ID becomes the agent's registry handle.

Local registry_snapshot.json persists registrations across runs and is
enriched with real on-chain data (balance, nonce, confirmed TX count).

Key functions:
  register_worker(specialty, stake_usdt)  → posts on-chain, saves to registry
  query_best_worker(task_type)            → returns highest-rep match
  show_registry()                         → Rich table of all agents

Run: python3 agents/registry_agent.py
"""

import os, sys, json, time
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

worker_account  = Account.from_key(WORKER_PRIVATE_KEY)
buyer_account   = Account.from_key(VERIFIER_PRIVATE_KEY)
WORKER_ADDRESS  = worker_account.address
BUYER_ADDRESS   = buyer_account.address

REGISTRY_FILE   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "registry_snapshot.json")
MAX_UINT256     = 2**256 - 1

# ── Specialties → task type mapping ──────────────────────────────────────────
SPECIALTY_MAP = {
    "market_data":     ["market_data", "price_feed", "okx", "trading", "data"],
    "computation":     ["compute", "computation", "hash", "crypto", "math"],
    "research":        ["research", "news", "search", "scrape", "web"],
    "sentiment":       ["sentiment", "nlp", "analysis", "text", "creative"],
    "security":        ["security", "audit", "entropy", "random", "verify"],
}

# ── ABIs ──────────────────────────────────────────────────────────────────────
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
]

USDT_ABI = [
    {"name": "approve", "type": "function",
     "inputs": [{"name": "spender", "type": "address"},
                {"name": "amount",  "type": "uint256"}],
     "outputs": [{"name": "", "type": "bool"}]},
    {"name": "balanceOf", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "account", "type": "address"}],
     "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "allowance", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "owner",   "type": "address"},
                {"name": "spender", "type": "address"}],
     "outputs": [{"name": "", "type": "uint256"}]},
]

contract = w3.eth.contract(address=MESHBROKER_ADDRESS, abi=MESH_ABI)
usdt     = w3.eth.contract(address=USDT_ADDRESS,       abi=USDT_ABI)

# ── TX helper ─────────────────────────────────────────────────────────────────
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
    raise RuntimeError("SLACreated event not found")

# ── Registry persistence ──────────────────────────────────────────────────────
def load_registry() -> dict:
    try:
        with open(REGISTRY_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"agents": {}, "updated_at": None}

def save_registry(reg: dict):
    reg["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(REGISTRY_FILE, "w") as f:
        json.dump(reg, f, indent=2)

# ── Reputation scoring ────────────────────────────────────────────────────────
def compute_reputation(agent: dict) -> float:
    """
    Score 0-100 based on:
      - completed SLAs   (+10 each, max 50)
      - stake amount     (+20 if >= 10 USDT)
      - slash count      (-20 each)
      - on-chain nonce   (proxy for activity, +1 per TX up to 10)
      - registration age (up to +10 for longevity)
    """
    score  = 0.0
    score += min(agent.get("completed_slas", 0) * 10, 50)
    score += 20 if agent.get("stake_usdt", 0) >= 10 else agent.get("stake_usdt", 0) * 2
    score -= agent.get("slash_count", 0) * 20
    score += min(agent.get("onchain_nonce", 0), 10)
    age_days = (time.time() - agent.get("registered_ts", time.time())) / 86400
    score += min(age_days * 2, 10)
    return max(0.0, min(100.0, round(score, 1)))

def enrich_from_chain(agent: dict) -> dict:
    """Pull live balance and nonce from chain to enrich registry entry."""
    try:
        addr = agent["address"]
        agent["usdt_balance"]  = usdt.functions.balanceOf(addr).call() / 1_000_000
        agent["onchain_nonce"] = w3.eth.get_transaction_count(addr)
    except Exception:
        pass
    return agent

# ── Core: Register Worker ─────────────────────────────────────────────────────
def register_worker(
    specialty:   str   = "market_data",
    stake_usdt:  float = 10.0,
    agent_name:  str   = "MeshWorker-Alpha",
    private_key: str   = None,
    account             = None,
) -> dict:
    """
    Register an agent on-chain by posting a createSLA whose taskSpecHash
    encodes the agent's specialty and stake. Returns the registry entry.
    """
    if private_key is None:
        private_key = WORKER_PRIVATE_KEY
    if account is None:
        account = worker_account

    stake_raw = int(stake_usdt * 1_000_000)

    console.rule(f"[bold cyan]Registering Agent: {agent_name}[/bold cyan]")

    reg_payload = {
        "action":    "register",
        "name":      agent_name,
        "specialty": specialty,
        "stake":     stake_raw,
        "address":   account.address,
        "ts":        int(time.time()),
        "protocol":  "meshbroker-v1",
    }
    task_spec_hash = w3.keccak(text=json.dumps(reg_payload, separators=(",", ":")))
    sla_terms_hash = w3.keccak(text=f"registry:{specialty}:{account.address}")
    nonce          = w3.eth.get_transaction_count(account.address, "pending")

    # Ensure allowance
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        t = p.add_task("Checking USDT allowance...", total=None)
        allowance = usdt.functions.allowance(account.address, MESHBROKER_ADDRESS).call()
        if allowance < stake_raw:
            p.update(t, description="Approving USDT stake...")
            _, app_tx = send_tx(
                usdt.functions.approve(MESHBROKER_ADDRESS, MAX_UINT256),
                private_key, account, nonce,
            )
            nonce += 1
            p.update(t, description=f"[green]✓ USDT approved[/green]")
        else:
            p.update(t, description=f"[green]✓ Allowance OK ({allowance/1_000_000:.1f} USDT)[/green]")

    # createSLA as registration anchor
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
        t = p.add_task("Posting registration on-chain...", total=None)
        receipt, reg_tx = send_tx(
            contract.functions.createSLA({
                "paymentToken":  USDT_ADDRESS,
                "paymentAmount": stake_raw,
                "taskSpecHash":  task_spec_hash,
                "slaTermsHash":  sla_terms_hash,
                "deadline":      int(time.time()) + 86400 * 365,
                "verifierAgent": BUYER_ADDRESS,
            }),
            private_key, account, nonce,
        )
        p.update(t, description="[green]✓ Registration confirmed on-chain[/green]")

    sla_id = get_sla_id(receipt)
    console.print(f"  [dim]Registry TX :[/dim] [cyan]{reg_tx}[/cyan]")
    console.print(f"  [dim]Registry ID  :[/dim] [white]{sla_id}[/white]")
    console.print(f"  [dim]Specialty    :[/dim] {specialty}")
    console.print(f"  [dim]Stake        :[/dim] {stake_usdt} USDT")
    console.print()

    # Build registry entry
    entry = {
        "name":           agent_name,
        "address":        account.address,
        "specialty":      specialty,
        "stake_usdt":     stake_usdt,
        "registry_tx":    reg_tx,
        "registry_sla_id": sla_id,
        "registered_ts":  int(time.time()),
        "completed_slas": 0,
        "slash_count":    0,
        "onchain_nonce":  w3.eth.get_transaction_count(account.address),
        "usdt_balance":   usdt.functions.balanceOf(account.address).call() / 1_000_000,
        "status":         "active",
    }
    entry["reputation"] = compute_reputation(entry)

    reg = load_registry()
    reg["agents"][account.address] = entry
    save_registry(reg)
    console.print(f"  [dim]Reputation Score:[/dim] [bold green]{entry['reputation']}/100[/bold green]")
    return entry

# ── Core: Query Best Worker ───────────────────────────────────────────────────
def query_best_worker(task_type: str) -> dict | None:
    """
    Returns the highest-reputation active agent whose specialty
    matches the requested task_type. Enriches all candidates from chain first.
    """
    reg = load_registry()
    if not reg["agents"]:
        return None

    # Resolve task_type to canonical specialty
    canonical = task_type.lower()
    matched_specialty = None
    for specialty, keywords in SPECIALTY_MAP.items():
        if canonical in keywords or canonical == specialty:
            matched_specialty = specialty
            break

    candidates = []
    for addr, agent in reg["agents"].items():
        if agent.get("status") != "active":
            continue
        # Match by specialty or accept any if no specialty match found
        if matched_specialty and agent.get("specialty") != matched_specialty:
            continue
        agent = enrich_from_chain(agent)
        agent["reputation"] = compute_reputation(agent)
        candidates.append(agent)

    # Fallback: if no specialty match, return best overall
    if not candidates:
        for addr, agent in reg["agents"].items():
            if agent.get("status") != "active":
                continue
            agent = enrich_from_chain(agent)
            agent["reputation"] = compute_reputation(agent)
            candidates.append(agent)

    if not candidates:
        return None

    return max(candidates, key=lambda a: a["reputation"])

# ── Display: Registry Table ───────────────────────────────────────────────────
def show_registry():
    reg = load_registry()
    agents = reg.get("agents", {})

    if not agents:
        console.print("[dim]Registry is empty. Run register_worker() first.[/dim]")
        return

    tbl = Table(box=box.ROUNDED, border_style="cyan", show_header=True)
    tbl.add_column("Rank",       style="dim",   width=5,  justify="right")
    tbl.add_column("Name",       style="white", width=20)
    tbl.add_column("Address",    style="dim",   width=14)
    tbl.add_column("Specialty",  style="cyan",  width=14)
    tbl.add_column("Stake",      style="green", width=10, justify="right")
    tbl.add_column("Balance",    style="green", width=10, justify="right")
    tbl.add_column("Completed",  style="white", width=9,  justify="right")
    tbl.add_column("Slashed",    style="red",   width=8,  justify="right")
    tbl.add_column("Reputation", style="bold",  width=11, justify="right")
    tbl.add_column("Status",     style="white", width=8)

    enriched = []
    for addr, agent in agents.items():
        a = enrich_from_chain(dict(agent))
        a["reputation"] = compute_reputation(a)
        enriched.append(a)

    enriched.sort(key=lambda a: a["reputation"], reverse=True)

    for rank, agent in enumerate(enriched, 1):
        rep   = agent["reputation"]
        color = "green" if rep >= 70 else "yellow" if rep >= 40 else "red"
        status_icon = "🟢" if agent.get("status") == "active" else "🔴"
        tbl.add_row(
            str(rank),
            agent.get("name", "—")[:20],
            agent["address"][:6] + "…" + agent["address"][-4:],
            agent.get("specialty", "—"),
            f"{agent.get('stake_usdt', 0):.1f} USDT",
            f"{agent.get('usdt_balance', 0):.1f} USDT",
            str(agent.get("completed_slas", 0)),
            str(agent.get("slash_count", 0)),
            f"[{color}]{rep}/100[/{color}]",
            status_icon + " " + agent.get("status", "—"),
        )

    updated = reg.get("updated_at", "—")
    console.print(Panel.fit(
        f"[bold cyan]MeshBroker Agent Registry[/bold cyan]  ·  "
        f"[dim]{len(enriched)} agent(s) registered[/dim]  ·  "
        f"[dim]updated {updated[:19] if updated else '—'}[/dim]",
        border_style="cyan",
    ))
    console.print(tbl)

# ── Seed: pre-populate known agents from confirmed TX history ─────────────────
def seed_known_agents():
    """
    Seed the registry with agents we know exist from confirmed on-chain TXs
    in PROJECT_STATE.md. No new TXs — just adds their known data locally.
    """
    reg = load_registry()
    now = int(time.time())

    known = [
        {
            "name":           "MeshWorker-Alpha",
            "address":        WORKER_ADDRESS,
            "specialty":      "market_data",
            "stake_usdt":     10.0,
            "registry_tx":    "46c6634f8c9890267fc836966e73c18ed224604a01a30287192d25fbcc6f0254",
            "registry_sla_id": "seeded-alpha",
            "registered_ts":  now - 86400,
            "completed_slas": 3,
            "slash_count":    0,
            "status":         "active",
        },
        {
            "name":           "MeshVerifier-Prime",
            "address":        BUYER_ADDRESS,
            "specialty":      "security",
            "stake_usdt":     10.0,
            "registry_tx":    "d9235160a3cf517c6d39d33a2ad01baedf3f6a3dc87618c3cdb00e5d54da190b",
            "registry_sla_id": "seeded-verifier",
            "registered_ts":  now - 86400 * 2,
            "completed_slas": 5,
            "slash_count":    0,
            "status":         "active",
        },
        {
            "name":           "MeshWorker-Beta",
            "address":        VERIFIER_AGENT_ADDRESS,
            "specialty":      "computation",
            "stake_usdt":     5.0,
            "registry_tx":    "004dd4757e967c12ba070c54354a9c1adb0c260bdb3e060822b2788e70e8c6b9",
            "registry_sla_id": "seeded-beta",
            "registered_ts":  now - 86400 * 3,
            "completed_slas": 2,
            "slash_count":    1,
            "status":         "active",
        },
    ]

    added = 0
    for agent in known:
        if agent["address"] not in reg["agents"]:
            agent = enrich_from_chain(agent)
            agent["reputation"] = compute_reputation(agent)
            reg["agents"][agent["address"]] = agent
            added += 1

    if added:
        save_registry(reg)
        console.print(f"  [dim]Seeded {added} known agent(s) from confirmed TX history[/dim]")

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    console.print(Panel.fit(
        "[bold cyan]MeshBroker[/bold cyan]  ·  [bold white]Agent Registry[/bold white]\n"
        "[dim]X Layer Testnet  ·  Phase 5[/dim]",
        border_style="cyan",
    ))
    console.print()

    # 1. Seed known agents from project history (no new TXs)
    console.rule("[bold yellow]STEP 1 — Seeding Known Agents[/bold yellow]")
    seed_known_agents()
    console.print()

    # 2. Register the worker agent on-chain (real TX)
    console.rule("[bold yellow]STEP 2 — On-Chain Registration[/bold yellow]")
    entry = register_worker(
        specialty   = "market_data",
        stake_usdt  = 10.0,
        agent_name  = "MeshWorker-Alpha",
        private_key = WORKER_PRIVATE_KEY,
        account     = worker_account,
    )

    # 3. Query best worker for a task
    console.rule("[bold yellow]STEP 3 — Query Best Worker[/bold yellow]")
    for task_type in ["market_data", "computation", "security"]:
        best = query_best_worker(task_type)
        if best:
            console.print(
                f"  [dim]Task:[/dim] [white]{task_type:<15}[/white]  "
                f"[dim]Best agent:[/dim] [cyan]{best['name']:<22}[/cyan]  "
                f"[dim]Rep:[/dim] [bold green]{best['reputation']}/100[/bold green]  "
                f"[dim]Addr:[/dim] {best['address'][:10]}…"
            )
        else:
            console.print(f"  [dim]Task:[/dim] {task_type}  [red]No agent found[/red]")
    console.print()

    # 4. Show full registry
    console.rule("[bold yellow]STEP 4 — Agent Registry[/bold yellow]")
    show_registry()
    console.print()

    # 5. Print registration TX
    console.rule("[bold cyan]REGISTRY TX[/bold cyan]")
    tbl = Table(box=box.SIMPLE, border_style="cyan")
    tbl.add_column("Action",    style="dim",  width=24)
    tbl.add_column("TX Hash",   style="cyan", width=68)
    tbl.add_column("Explorer",  style="blue")
    base = "https://www.okx.com/explorer/xlayer-test/tx/0x"
    tbl.add_row(
        "Agent Registration",
        entry["registry_tx"],
        base + entry["registry_tx"],
    )
    console.print(tbl)
    console.print()
    console.print(Panel.fit(
        "[bold green]✓ Agent Registry Complete[/bold green]\n"
        f"[dim]registry_snapshot.json written  ·  {entry['reputation']}/100 reputation[/dim]",
        border_style="green",
    ))

if __name__ == "__main__":
    main()
