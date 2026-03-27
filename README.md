<div align="center">

# ⬡ MeshBroker

### Trustless SLA Enforcement for AI Agent Commerce

*AI agents that pay each other — with cryptographic proof, on-chain escrow, and automatic slashing.*

**Built on X Layer (zkEVM) · Powered by OKX Onchain OS · OKX/X Layer AI Hackathon 2026**

---

[![X Layer](https://img.shields.io/badge/Network-X%20Layer%20Testnet-00d4ff?style=flat-square)](https://www.okx.com/explorer/xlayer-test)
[![Python](https://img.shields.io/badge/Python-3.14-00ff9d?style=flat-square)](https://python.org)
[![web3.py](https://img.shields.io/badge/web3.py-7.x-ffb700?style=flat-square)](https://web3py.readthedocs.io)
[![License](https://img.shields.io/badge/License-MIT-white?style=flat-square)](LICENSE)

</div>

---

## The Problem

AI agents are being deployed to do real work — fetch data, run computations, generate content, execute trades. But when one agent needs to pay another, there is no enforcement layer. The paying agent has to trust that the work was done. The working agent has to trust that payment will come. In a world of autonomous agents, trust doesn't scale.

## The Solution

MeshBroker is a trustless SLA enforcement layer. Payment is locked in escrow before work begins. The worker submits cryptographic proof of execution. A verifier agent checks the proof on-chain. Payment releases automatically on success — or the worker gets slashed on failure. No human in the loop. No trust required.
```
Buyer locks USDT  →  Worker executes task  →  Verifier settles on-chain
     createSLA()        submitProof()            verifyAndRelease()
                                                 OR rejectProof() → slash
```

---

## Live Demo

Every transaction below is real — confirmed on X Layer Testnet.

### Bounty Race (2 workers compete, loser slashed)

| Action | TX Hash |
|--------|---------|
| Post Bounty 1 | [`32dc7734...`](https://www.okx.com/explorer/xlayer-test/tx/0x32dc7734084f1ef96ba03bb77a847ca0765d46433906e51c1301cd393e3d5240) |
| Alpha Accept + Proof | [`46c6634f...`](https://www.okx.com/explorer/xlayer-test/tx/0x46c6634f8c9890267fc836966e73c18ed224604a01a30287192d25fbcc6f0254) |
| Alpha Settlement | [`7d0c2e04...`](https://www.okx.com/explorer/xlayer-test/tx/0x7d0c2e04f842b038d23e8418a2e0a6d950f262c4de0aa99315a45a1301f69488) |
| Post Bounty 2 | [`30914746...`](https://www.okx.com/explorer/xlayer-test/tx/0x30914746a9e87e6ece84feea9aea3377cbf0df8e4600103a183968aab9e1cd54) |
| Beta Accept + Proof | [`004dd475...`](https://www.okx.com/explorer/xlayer-test/tx/0x004dd4757e967c12ba070c54354a9c1adb0c260bdb3e060822b2788e70e8c6b9) |

### x402 Atomic Payment Loop (end-to-end in one script)

| Action | TX Hash |
|--------|---------|
| Buyer USDT Approve | [`167854db...`](https://www.okx.com/explorer/xlayer-test/tx/0x167854dba736462df860fa592b19014834f8104e17c8311da04e7f619b4a6845) |
| createSLA (lock escrow) | [`f01c67f3...`](https://www.okx.com/explorer/xlayer-test/tx/0xf01c67f3b5e386982dba314a3ec1e3603c4c0d79dde39182b3ea4a6d6f0314d3) |
| Worker USDT Approve | [`ab8fc55e...`](https://www.okx.com/explorer/xlayer-test/tx/0xab8fc55ec84e3b984abcfb5143edb4b395b84af253dd797bc35a79e4ab240020) |
| acceptSLA | [`962cfaa5...`](https://www.okx.com/explorer/xlayer-test/tx/0x962cfaa5ca1de4cb36926e49911180e02c5a512418cea07ec1ba331ff6526ad6) |
| submitProof | [`fe78dd2a...`](https://www.okx.com/explorer/xlayer-test/tx/0xfe78dd2afa1d28e5b702b2dd608ba2ef75cecff136261944158690d63d13942e) |
| verifyAndRelease | [`d9235160...`](https://www.okx.com/explorer/xlayer-test/tx/0xd9235160a3cf517c6d39d33a2ad01baedf3f6a3dc87618c3cdb00e5d54da190b) |

### Agent Registry

| Action | TX Hash |
|--------|---------|
| Worker Registration | [`2436d4fa...`](https://www.okx.com/explorer/xlayer-test/tx/0x2436d4facb021c9f2166c89784a723751ff9e19840afaa66f3cc33542912d77b) |

**12 confirmed on-chain transactions. Real USDT. Real slashing. Real proof.**

---

## How It Works

### 1. SLA Composer
Type a task in plain English. Claude Haiku converts it to a structured SLA spec with payment amount, deadline, proof type, and success criteria — ready to deploy on-chain.
```bash
python3 composer_server.py
# Open http://localhost:7402
# Type: "Fetch live OKB/USDT price and return bid, ask, volume"
# Get back: structured JSON SLA spec in ~3 seconds
```

### 2. Buyer Agent
Locks USDT in escrow on X Layer via `createSLA()`. The SLA spec hash is committed on-chain — immutable, verifiable.
```bash
python3 agents/buyer_agent.py
```

### 3. Worker Agent
Accepts the SLA, executes the task (live OKX market data via OKX Onchain OS API), and submits a cryptographic proof hash on-chain.
```bash
python3 agents/worker_agent.py
```

### 4. Verifier Agent
Reads the proof from chain. If valid — releases payment to worker. If invalid — slashes the worker's stake and sends funds to the protocol treasury.
```bash
python3 agents/verifier_agent.py
```

### 5. Bounty Race
Two workers compete for the same job simultaneously. First valid proof wins. Loser gets slashed. Demonstrates the protocol's economic incentive layer.
```bash
python3 demo/bounty_race.py
```

### 6. x402 Atomic Payment Loop
Simulates the x402 HTTP payment standard — buyer hits a paywall, signs a payment header, locks escrow, worker delivers, verifier settles. Six transactions, end to end, in one script.
```bash
python3 agents/buyer_agent_x402.py
```

### 7. Agent Registry
Workers register on-chain with specialty and stake. The registry scores reputation from completed SLAs, stake size, activity, and slash history. Buyers query for the best available worker by task type.
```bash
python3 agents/registry_agent.py
```

---

## Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    MeshBroker Protocol                  │
│                   (X Layer Testnet)                     │
├─────────────┬──────────────────┬────────────────────────┤
│ Buyer Agent │  Worker Agent    │  Verifier Agent        │
│             │                  │                        │
│ createSLA() │  acceptSLA()     │  verifyAndRelease()    │
│ USDT escrow │  submitProof()   │  OR rejectProof()      │
│             │  OKX Market API  │  → slash + treasury    │
└─────────────┴──────────────────┴────────────────────────┘
        │                                    │
        ▼                                    ▼
┌───────────────┐                  ┌─────────────────────┐
│ SLA Composer  │                  │   Agent Registry    │
│ Claude Haiku  │                  │  Reputation Scores  │
│ → JSON spec   │                  │  On-chain anchored  │
└───────────────┘                  └─────────────────────┘
        │                                    │
        └──────────────┬─────────────────────┘
                       ▼
              ┌─────────────────┐
              │  Bounty Engine  │
              │  Race + Slash   │
              │  War Room Demo  │
              └─────────────────┘
```

---

## Stack

| Layer | Technology |
|-------|-----------|
| Blockchain | X Layer Testnet (zkEVM) |
| Payment Token | MockUSDT (6 decimals) |
| Smart Contract | MeshBroker (deployed, ABI inline) |
| Language | Python 3.14 |
| Web3 | web3.py 7.x |
| AI | Claude Haiku (SLA composition) |
| Market Data | OKX Onchain OS Market API |
| Terminal UI | Rich |
| Composer UI | Vanilla HTML/CSS/JS, JetBrains Mono |

---

## Quick Start
```bash
# Clone
git clone https://github.com/Vinaystwt/meshbroker-agents
cd meshbroker-agents

# Install dependencies
pip3 install python-dotenv web3 rich requests --break-system-packages

# Configure environment
cp .env.example .env
# Fill in your RPC_URL, MESHBROKER_ADDRESS, USDT_ADDRESS,
# WORKER_PRIVATE_KEY, VERIFIER_PRIVATE_KEY, VERIFIER_AGENT_ADDRESS,
# ANTHROPIC_API_KEY

# Run the full war room demo
python3 demo/warroom.py

# Run the x402 atomic payment loop
python3 agents/buyer_agent_x402.py

# Run the bounty race
python3 demo/bounty_race.py

# Start the SLA composer UI
python3 composer_server.py
```

---

## Repo Structure
```
agents/
  buyer_agent.py          — createSLA(), USDT escrow
  worker_agent.py         — acceptSLA(), OKX data, submitProof()
  verifier_agent.py       — verifyAndRelease(), rejectProof()
  bounty_engine.py        — 2-worker race engine
  buyer_agent_x402.py     — x402 atomic payment loop
  registry_agent.py       — on-chain agent registry
core/
  composer_engine.py      — Claude Haiku → JSON SLA spec
  reputation.py           — on-chain event reads → trust scores
demo/
  warroom.py              — Rich terminal dashboard, 3 scenarios
  bounty_race.py          — 2-worker race, live TX output
  full_demo.sh            — runs everything in sequence
composer_server.py        — local server for composer UI
dashboard/composer.html   — SLA composer interface
heartbeat.html            — live agent trust page
registry_snapshot.json    — persisted agent registry
```

---

## Live Chain State

| Metric | Value |
|--------|-------|
| Network | X Layer Testnet (zkEVM) |
| Contract | MeshBroker (deployed) |
| Escrow Balance | 225.62 USDT |
| Protocol Treasury | Accumulating from slashed workers |
| Total TX Count | 12 confirmed on-chain |
| Worker Balance | 1,015.10 USDT |
| Buyer Balance | 749.42 USDT |

---

## Environment Variables

Create a `.env` file in the repo root. **Never commit this file.**
```
RPC_URL=
MESHBROKER_ADDRESS=
USDT_ADDRESS=
WORKER_PRIVATE_KEY=
VERIFIER_PRIVATE_KEY=
VERIFIER_AGENT_ADDRESS=
ANTHROPIC_API_KEY=
```

A `.env.example` file with empty values is provided for reference.

---

<div align="center">

Built with on X Layer · OKX Onchain OS AI Hackathon 2026

</div>
