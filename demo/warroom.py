import os, time, threading, queue, sys
from datetime import datetime
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.table import Table
from rich import box
from dotenv import load_dotenv

# Import your actual agents
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.buyer_agent import BuyerAgent
from agents.worker_agent import WorkerAgent
from agents.verifier_agent import VerifierAgent

load_dotenv()

# --- Shared State ---
event_queue = queue.Queue()
messages = []
stats = {"locked": 0.0, "settled": 0.0, "slashed": 0.0, "refunded": 0.0}

def log_event(agent, msg, color="white"):
    ts = datetime.now().strftime("%H:%M:%S")
    event_queue.put({"ts": ts, "agent": agent, "msg": msg, "color": color})

# --- Scenario Logic ---
def run_orchestrator():
    try:
        buyer = BuyerAgent()
        worker = WorkerAgent()
        verifier = VerifierAgent()
        
        # SCENARIO 1: Honest OKX Data Run
        log_event("SYSTEM", "🚀 INITIALIZING SCENARIO 1: THE HONEST WORKER", "magenta")
        time.sleep(1)
        log_event("BuyerAgent", "Creating 10 USDT SLA for OKX Market Data...", "cyan")
        sla_id = buyer.create_job("Fetch OKX Market Data", 10000000)
        if not sla_id: return
        stats["locked"] += 10.0
        
        time.sleep(2)
        log_event("WorkerAgent", "SLA detected. Approving stake and accepting...", "yellow")
        worker.execute_honest_task(sla_id)
        log_event("WorkerAgent", "✅ Proof submitted: OKB Price secured on-chain.", "yellow")
        
        time.sleep(2)
        log_event("VerifierAgent", "Proof hash verified. Releasing payment...", "green")
        stats["settled"] += 10.0
        log_event("SYSTEM", "🎉 SCENARIO 1 COMPLETE: SUCCESS", "green")
        
        time.sleep(4)
        
        # SCENARIO 2: The Hallucination (Slashing)
        log_event("SYSTEM", "🚀 INITIALIZING SCENARIO 2: THE HALLUCINATION", "magenta")
        log_event("BuyerAgent", "Creating 10 USDT SLA: 'Write a poem on India'...", "cyan")
        sla_id_2 = buyer.create_job("Poem Task", 10000000)
        stats["locked"] += 10.0
        
        time.sleep(2)
        log_event("WorkerAgent", "Submitting generated response...", "yellow")
        time.sleep(2)
        log_event("VerifierAgent", "🔍 Analyzing output... Error detected.", "green")
        log_event("VerifierAgent", "❌ REJECTED: Content does not match task constraints.", "red")
        
        time.sleep(1)
        log_event("VerifierAgent", "Initiating on-chain SLASHING of worker stake...", "red")
        verifier.slash_worker(sla_id_2, "Hallucination detected.")
        stats["slashed"] += 0.5
        stats["refunded"] += 10.0
        log_event("SYSTEM", "🛡️  BUYER REFUNDED: 10 USDT returned to wallet.", "cyan")
        log_event("SYSTEM", "💀 SCENARIO 2 COMPLETE: WORKER SLASHED", "red")

        time.sleep(4)

        # SCENARIO 3: The Security Breach (Tampering)
        log_event("SYSTEM", "🚀 INITIALIZING SCENARIO 3: SECURITY BREACH", "magenta")
        log_event("BuyerAgent", "Creating 10 USDT SLA: Sentiment Analysis...", "cyan")
        sla_id_3 = buyer.create_job("Security Test", 10000000)
        stats["locked"] += 10.0

        time.sleep(2)
        log_event("WorkerAgent", "Proof submitted to contract...", "yellow")
        log_event("SYSTEM", "🚨 SIMULATING TAMPERING: Modifying output data...", "red")
        time.sleep(2)

        log_event("VerifierAgent", "⚠️  HASH MISMATCH DETECTED: 0xABC... != 0xDEF...", "red")
        log_event("VerifierAgent", "Evidence of tampering found. Rejecting proof.", "red")
        
        verifier.slash_worker(sla_id_3, "Tampering detected.")
        stats["slashed"] += 0.5
        stats["refunded"] += 10.0
        log_event("SYSTEM", "🛡️  BUYER REFUNDED: 10 USDT secured.", "cyan")
        log_event("SYSTEM", "🎉 ALL SCENARIOS COMPLETE.", "magenta")

    except Exception as e:
        log_event("ERROR", str(e), "red")

# --- UI Rendering ---
def build_layout():
    layout = Layout()
    layout.split_column(Layout(name="header", size=3), Layout(name="body", ratio=1))
    layout["body"].split_row(Layout(name="logs", ratio=2), Layout(name="status", ratio=1))
    
    header_text = Text("MESHBROKER WAR ROOM // X LAYER TESTNET // MULTI-AGENT ORCHESTRATION", style="bold white", justify="center")
    layout["header"].update(Panel(header_text, style="on blue"))
    
    log_content = Text()
    for m in messages[-22:]:
        log_content.append(f"{m['ts']} ", style="dim")
        log_content.append(f"[{m['agent']:^13}] ", style=f"bold {m['color']}")
        log_content.append(f"{m['msg']}\n")
    layout["logs"].update(Panel(log_content, title="[bold cyan]LIVE AGENT ACTIVITY FEED", border_style="cyan"))
    
    status_text = Text.from_markup(f"""
[bold yellow]PROTOCOL HEALTH[/]
[dim]──────────────────────────────[/]
[white]Total Locked:   [/][bold yellow]{stats['locked']:.2f} USDT[/]
[white]Total Settled:  [/][bold green]{stats['settled']:.2f} USDT[/]
[white]Total Refunded: [/][bold cyan]{stats['refunded']:.2f} USDT[/]
[white]Total Slashed:  [/][bold red]{stats['slashed']:.2f} USDT[/]

[bold cyan]ACTIVE SLAS[/]
[dim]──────────────────────────────[/]
[green]●[/] Honest Run:   [bold green]SETTLED[/]
[red]●[/] Hallucination: [bold red]REFUNDED[/]
[red]●[/] Security:    [bold red]REFUNDED[/]

[bold magenta]NETWORK[/]
[dim]──────────────────────────────[/]
[white]Chain:[/] X Layer Testnet
[white]Mode:[/]  Autonomous AI
    """)
    layout["status"].update(Panel(status_text, title="[bold magenta]ON-CHAIN STATE", border_style="magenta"))
    return layout

if __name__ == "__main__":
    threading.Thread(target=run_orchestrator, daemon=True).start()
    console = Console()
    with Live(build_layout(), refresh_per_second=4, screen=True) as live:
        while True:
            while not event_queue.empty():
                messages.append(event_queue.get())
            live.update(build_layout())
            time.sleep(0.1)
