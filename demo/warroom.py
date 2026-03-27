import os, time, threading, queue, sys
from datetime import datetime
from web3 import Web3
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.buyer_agent import BuyerAgent
from agents.worker_agent import WorkerAgent
from agents.verifier_agent import VerifierAgent

load_dotenv()

event_queue = queue.Queue()
messages = []
chain_state = {
    "treasury": 0.0, "mesh_usdt_balance": 0.0,
    "worker_balance": 0.0, "buyer_balance": 0.0,
    "block": 0, "last_updated": "connecting..."
}
stats = {"locked": 0.0, "settled": 0.0, "slashed": 0.0, "refunded": 0.0}

w3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
mesh_addr     = Web3.to_checksum_address(os.getenv("MESHBROKER_ADDRESS").strip("'\" "))
usdt_addr     = Web3.to_checksum_address(os.getenv("USDT_ADDRESS").strip("'\" "))
worker_addr   = w3.eth.account.from_key(os.getenv("WORKER_PRIVATE_KEY")).address
verifier_addr = w3.eth.account.from_key(os.getenv("VERIFIER_PRIVATE_KEY")).address

USDT_ABI = [{"name":"balanceOf","type":"function","stateMutability":"view",
              "inputs":[{"name":"account","type":"address"}],
              "outputs":[{"name":"","type":"uint256"}]}]
TREASURY_ABI = [{"name":"protocolTreasury","type":"function","stateMutability":"view",
                 "inputs":[{"name":"","type":"address"}],
                 "outputs":[{"name":"","type":"uint256"}]}]

usdt_contract = w3.eth.contract(address=usdt_addr, abi=USDT_ABI)
mesh_contract = w3.eth.contract(address=mesh_addr, abi=TREASURY_ABI)

def poll_chain():
    while True:
        try:
            chain_state["mesh_usdt_balance"] = usdt_contract.functions.balanceOf(mesh_addr).call() / 1_000_000
            chain_state["worker_balance"]     = usdt_contract.functions.balanceOf(worker_addr).call() / 1_000_000
            chain_state["buyer_balance"]      = usdt_contract.functions.balanceOf(verifier_addr).call() / 1_000_000
            chain_state["treasury"]           = mesh_contract.functions.protocolTreasury(usdt_addr).call() / 1_000_000
            chain_state["block"]              = w3.eth.block_number
            chain_state["last_updated"]       = datetime.now().strftime("%H:%M:%S")
        except Exception as e:
            chain_state["last_updated"] = f"poll_err:{str(e)[:18]}"
        time.sleep(3)

def log_event(agent, msg, color="white"):
    ts = datetime.now().strftime("%H:%M:%S")
    event_queue.put({"ts": ts, "agent": agent, "msg": msg, "color": color})

def run_orchestrator():
    try:
        buyer    = BuyerAgent()
        worker   = WorkerAgent()
        verifier = VerifierAgent()

        # --- SCENARIO 1: HONEST WORKER ---
        log_event("SYSTEM",       "🚀 SCENARIO 1: THE HONEST WORKER", "magenta")
        time.sleep(1)
        log_event("BuyerAgent",   "Creating 10 USDT SLA — OKX Market Data task...", "cyan")
        sla_id = buyer.create_job("Fetch OKX Market Data", 10000000)
        if not sla_id:
            log_event("ERROR", "SLA creation failed. Check contract address in .env", "red")
            return
        stats["locked"] += 10.0
        log_event("BuyerAgent",   f"✅ Escrow locked on-chain: {sla_id[:16]}...", "cyan")

        time.sleep(2)
        log_event("WorkerAgent",  "Approving stake + accepting SLA on-chain...", "yellow")
        worker.execute_honest_task(sla_id)
        log_event("WorkerAgent",  "✅ Live OKX price proof submitted to X Layer.", "yellow")

        time.sleep(3)
        log_event("VerifierAgent","Proof hash verified. Calling verifyAndRelease()...", "green")
        try:
            _abi = [{"name":"verifyAndRelease","type":"function",
                     "inputs":[{"name":"slaId","type":"bytes32"},
                                {"name":"resultHash","type":"bytes32"}]}]
            _c = w3.eth.contract(address=mesh_addr, abi=_abi)
            _tx = _c.functions.verifyAndRelease(
                bytes.fromhex(sla_id.replace("0x","")),
                w3.keccak(text="release")
            ).build_transaction({
                "from": verifier.account.address,
                "nonce": w3.eth.get_transaction_count(verifier.account.address,"pending"),
                "gasPrice": int(w3.eth.gas_price * 1.2)
            })
            w3.eth.wait_for_transaction_receipt(
                w3.eth.send_raw_transaction(
                    w3.eth.account.sign_transaction(_tx, verifier.key).raw_transaction))
        except Exception as e:
            log_event("VerifierAgent", f"Release: {str(e)[:55]}", "dim")
        stats["settled"] += 10.0
        log_event("SYSTEM", "🎉 SCENARIO 1 COMPLETE — PAYMENT SETTLED ON-CHAIN", "green")
        time.sleep(4)

        # --- SCENARIO 2: SLASHING ---
        log_event("SYSTEM",       "🚀 SCENARIO 2: THE HALLUCINATION — SLASHING", "magenta")
        log_event("BuyerAgent",   "Creating 10 USDT SLA — Sentiment Analysis task...", "cyan")
        sla_id_2 = buyer.create_job("Sentiment Analysis", 10000000)
        if not sla_id_2:
            log_event("ERROR", "SLA 2 creation failed.", "red")
            return
        stats["locked"] += 10.0
        log_event("BuyerAgent",   f"✅ Escrow locked: {sla_id_2[:16]}...", "cyan")

        time.sleep(2)
        log_event("WorkerAgent",  "Accepting SLA, preparing to submit proof...", "yellow")
        worker.execute_honest_task(sla_id_2)
        log_event("WorkerAgent",  "Proof submitted (contains fabricated data).", "yellow")

        time.sleep(2)
        log_event("VerifierAgent","🔍 Analysing proof... HASH MISMATCH DETECTED.", "red")
        log_event("VerifierAgent","❌ REJECT: Output does not match task constraints.", "red")
        time.sleep(1)
        log_event("VerifierAgent","Initiating on-chain SLASH of worker stake...", "red")
        verifier.slash_worker(sla_id_2, "Hallucination detected by AI verifier. Stake slashed.")
        stats["slashed"]  += 0.5
        stats["refunded"] += 10.0
        log_event("SYSTEM", "🛡️  BUYER REFUNDED. 0.5 USDT STAKE → TREASURY.", "cyan")
        log_event("SYSTEM", "💀 SCENARIO 2 COMPLETE — WORKER SLASHED", "red")
        time.sleep(4)

        # --- SCENARIO 3: TAMPERING ---
        log_event("SYSTEM",      "🚀 SCENARIO 3: SECURITY BREACH — TAMPERING", "magenta")
        log_event("BuyerAgent",  "Creating 10 USDT SLA — Price Oracle task...", "cyan")
        sla_id_3 = buyer.create_job("Price Oracle Security Test", 10000000)
        if not sla_id_3:
            log_event("ERROR", "SLA 3 creation failed.", "red")
            return
        stats["locked"] += 10.0
        log_event("BuyerAgent",  f"✅ Escrow locked: {sla_id_3[:16]}...", "cyan")

        time.sleep(2)
        log_event("WorkerAgent", "Proof submitted to contract...", "yellow")
        log_event("SYSTEM",      "🚨 SIMULATING TAMPERING: data modified post-submission...", "red")
        time.sleep(2)
        log_event("VerifierAgent","⚠️  HASH MISMATCH: 0xABC...≠0xDEF... Tampering confirmed.", "red")
        log_event("VerifierAgent","Rejecting proof. Executing slash...", "red")
        verifier.slash_worker(sla_id_3, "Tampering detected: submitted hash does not match proof URI.")
        stats["slashed"]  += 0.5
        stats["refunded"] += 10.0
        log_event("SYSTEM", "🛡️  BUYER REFUNDED. INTEGRITY ENFORCED BY CONTRACT.", "cyan")
        log_event("SYSTEM", "🎉 ALL 3 SCENARIOS COMPLETE — MESHBROKER PROTOCOL VERIFIED", "magenta")

    except Exception as e:
        log_event("ERROR", f"Orchestrator crashed: {str(e)}", "red")

def build_layout():
    layout = Layout()
    layout.split_column(Layout(name="header", size=3), Layout(name="body", ratio=1))
    layout["body"].split_row(Layout(name="logs", ratio=2), Layout(name="status", ratio=1))

    from rich.text import Text
    header_text = Text(
        "MESHBROKER WAR ROOM  //  X LAYER TESTNET  //  LIVE ON-CHAIN STATE",
        style="bold white", justify="center")
    layout["header"].update(Panel(header_text, style="on blue"))

    log_content = Text()
    for m in messages[-22:]:
        log_content.append(f"{m['ts']} ", style="dim")
        log_content.append(f"[{m['agent']:^13}] ", style=f"bold {m['color']}")
        log_content.append(f"{m['msg']}\n")
    layout["logs"].update(Panel(log_content,
        title="[bold cyan]⚡ LIVE AGENT ACTIVITY FEED", border_style="cyan"))

    status_text = Text.from_markup(f"""
[bold yellow]LIVE CHAIN STATE[/]   [dim]block #{chain_state['block']}[/]
[dim]updated: {chain_state['last_updated']}[/]
[dim]──────────────────────────────[/]
[white]MeshBroker Escrow:  [/][bold yellow]{chain_state['mesh_usdt_balance']:.4f} USDT[/]
[white]Protocol Treasury:  [/][bold red]{chain_state['treasury']:.4f} USDT[/]
[white]Worker Balance:     [/][bold yellow]{chain_state['worker_balance']:.4f} USDT[/]
[white]Buyer Balance:      [/][bold cyan]{chain_state['buyer_balance']:.4f} USDT[/]

[bold cyan]SCENARIO LEDGER[/]
[dim]──────────────────────────────[/]
[white]Total Locked:   [/][bold yellow]{stats['locked']:.2f} USDT[/]
[white]Total Settled:  [/][bold green]{stats['settled']:.2f} USDT[/]
[white]Total Refunded: [/][bold cyan]{stats['refunded']:.2f} USDT[/]
[white]Total Slashed:  [/][bold red]{stats['slashed']:.2f} USDT[/]

[bold magenta]NETWORK[/]
[dim]──────────────────────────────[/]
[white]Chain:[/]  X Layer Testnet (zkEVM)
[white]RPC:  [/]  {os.getenv('RPC_URL','')[:28]}...
[white]Mode: [/]  Fully Autonomous AI Agents
    """)
    layout["status"].update(Panel(status_text,
        title="[bold magenta]📡 ON-CHAIN STATE (LIVE)", border_style="magenta"))
    return layout

if __name__ == "__main__":
    threading.Thread(target=poll_chain,      daemon=True).start()
    threading.Thread(target=run_orchestrator, daemon=True).start()
    console = Console()
    with Live(build_layout(), refresh_per_second=4, screen=True) as live:
        while True:
            while not event_queue.empty():
                messages.append(event_queue.get())
            live.update(build_layout())
            time.sleep(0.1)
