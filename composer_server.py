#!/usr/bin/env python3
"""
MeshBroker — Composer Server (Phase 4.5)
=========================================
Serves dashboard/composer.html at http://localhost:7402/
  POST /compose  — Claude Haiku API → JSON SLA spec
  GET  /status   — live chain stats

Run: python3 composer_server.py
"""

import os, json, time, threading, webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from dotenv import load_dotenv
import requests
from web3 import Web3

load_dotenv()

PORT                   = 7402
ANTHROPIC_API_KEY      = os.getenv("ANTHROPIC_API_KEY")
RPC_URL                = os.getenv("RPC_URL")
MESHBROKER_ADDRESS     = Web3.to_checksum_address(os.getenv("MESHBROKER_ADDRESS"))
USDT_ADDRESS           = Web3.to_checksum_address(os.getenv("USDT_ADDRESS"))
VERIFIER_AGENT_ADDRESS = Web3.to_checksum_address(os.getenv("VERIFIER_AGENT_ADDRESS"))

w3 = Web3(Web3.HTTPProvider(RPC_URL))

USDT_ABI = [{"name":"balanceOf","type":"function","stateMutability":"view",
              "inputs":[{"name":"account","type":"address"}],
              "outputs":[{"name":"","type":"uint256"}]}]

TREASURY_ABI = [{"name":"protocolTreasury","type":"function","stateMutability":"view",
                 "inputs":[{"name":"","type":"address"}],
                 "outputs":[{"name":"","type":"uint256"}]}]

usdt       = w3.eth.contract(address=USDT_ADDRESS,       abi=USDT_ABI)
meshbroker = w3.eth.contract(address=MESHBROKER_ADDRESS, abi=TREASURY_ABI)

COMPOSER_HTML = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "dashboard", "composer.html"
)

SYSTEM_PROMPT = """You are an SLA specification engine for MeshBroker, a trustless AI agent payment protocol on X Layer (zkEVM).

Given a natural-language task description, output ONLY a valid JSON object (no markdown, no explanation) with this exact schema:
{
  "task": "<short task name, snake_case>",
  "description": "<one sentence>",
  "payment_usdt": <number 1-100>,
  "deadline_minutes": <number 5-1440>,
  "success_criteria": "<measurable, verifiable condition>",
  "proof_type": "<one of: api_response | computation_result | file_hash | attestation>",
  "risk_level": "<low | medium | high>",
  "metadata": {
    "category": "<data | compute | research | creative | security>",
    "estimated_tokens": <number>,
    "requires_internet": <true | false>
  }
}

Rules:
- payment_usdt must be reasonable for the task complexity
- deadline_minutes: simple tasks 5-30, complex 60-480
- success_criteria must be objectively verifiable
- Output ONLY the JSON object, nothing else"""

def call_haiku(user_input: str) -> dict:
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key":         ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        },
        json={
            "model":      "claude-haiku-4-5",
            "max_tokens": 512,
            "system":     SYSTEM_PROMPT,
            "messages":   [{"role": "user", "content": user_input}],
        },
        timeout=20,
    )
    resp.raise_for_status()
    text = resp.json()["content"][0]["text"].strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(text)

def get_chain_status() -> dict:
    try:
        block   = w3.eth.block_number
        escrow  = usdt.functions.balanceOf(MESHBROKER_ADDRESS).call() / 1_000_000
        try:
            treasury = meshbroker.functions.protocolTreasury(VERIFIER_AGENT_ADDRESS).call() / 1_000_000
        except Exception:
            treasury = 0.0
        return {"block": block, "escrow": f"{escrow:.2f}", "treasury": f"{treasury:.4f}", "rpc_ok": True}
    except Exception as e:
        return {"block": "—", "escrow": "—", "treasury": "—", "rpc_ok": False, "error": str(e)}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type",   "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _html(self, body):
        self.send_response(200)
        self.send_header("Content-Type",   "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            try:
                with open(COMPOSER_HTML, "rb") as f:
                    self._html(f.read())
            except FileNotFoundError:
                self._json({"error": f"composer.html not found at {COMPOSER_HTML}"}, 404)
        elif path == "/status":
            self._json(get_chain_status())
        else:
            self._json({"error": "Not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/compose":
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            try:
                payload = json.loads(body)
                task    = payload.get("task", "").strip()
                if not task:
                    self._json({"error": "task field required"}, 400)
                    return
                spec = call_haiku(task)
                self._json({"ok": True, "spec": spec})
            except json.JSONDecodeError:
                self._json({"error": "Invalid JSON body"}, 400)
            except requests.HTTPError as e:
                self._json({"error": f"Anthropic API error: {e}"}, 502)
            except Exception as e:
                self._json({"error": str(e)}, 500)
        else:
            self._json({"error": "Not found"}, 404)

def main():
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"\n  ╔══════════════════════════════════════╗")
    print(f"  ║   MeshBroker  ·  Composer Server     ║")
    print(f"  ║   http://localhost:{PORT}/              ║")
    print(f"  ╚══════════════════════════════════════╝\n")
    print(f"  GET  /         → composer UI")
    print(f"  POST /compose  → Claude Haiku SLA spec")
    print(f"  GET  /status   → live chain stats\n")
    print(f"  Ctrl+C to stop.\n")
    def _open():
        time.sleep(0.8)
        webbrowser.open(f"http://localhost:{PORT}/")
    threading.Thread(target=_open, daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")

if __name__ == "__main__":
    main()
