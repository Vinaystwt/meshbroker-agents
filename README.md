<div align="center">

<img src="assets/logo.svg" alt="MeshBroker" width="600"/>

<br/><br/>

**The trustless SLA enforcement layer for the agentic economy.**

*When AI agents exchange value, someone has to be the sheriff.*

[![Network](https://img.shields.io/badge/Network-X%20Layer%20Testnet-blue?style=for-the-badge)](https://www.oklink.com/xlayer-test)
[![Protocol](https://img.shields.io/badge/Protocol-x402%20Payments-orange?style=for-the-badge)](https://x402.org)
[![Stack](https://img.shields.io/badge/Stack-Python%20+%20web3.py-yellow?style=for-the-badge)](https://python.org)
[![Live TXs](https://img.shields.io/badge/Live%20Transactions-12%20Confirmed-brightgreen?style=for-the-badge)](https://www.oklink.com/xlayer-test)

</div>

---

## What Is MeshBroker?

MeshBroker is an onchain SLA enforcement layer for AI agent commerce — a smart contract protocol that sits between agents that pay for work and agents that perform work, guaranteeing that payment only releases when the job is cryptographically proven to be complete.

It is not a trading bot. It is not a chatbot wrapper. It is **infrastructure** — the trust primitive that every other agent project on X Layer needs but nobody has built yet.

---

## Why We Built It

The agentic economy has a fundamental unsolved problem.

Every major payment protocol in 2026 — x402, AP2, ACP — solves the same thing beautifully: how do you *initiate* a payment to an AI agent? What none of them solve is what happens *after* the payment. How do you know the agent actually did the work? How do you stop an agent from hallucinating results, fabricating data, or returning garbage and keeping the money?

Right now you can't. Agents either operate on blind trust or they don't operate at all.

MeshBroker is the answer. It turns every agent interaction from a handshake into a contract — with automatic enforcement, cryptographic verification, and economic punishment for bad behavior.

---

## How It Works
```
  BuyerAgent                MeshBroker Contract              WorkerAgent
      │                            │                               │
      │──── createSLA() ──────────►│                               │
      │     [lock USDT escrow]     │                               │
      │                            │◄──── acceptSLA() ────────────│
      │                            │      [stake USDT bond]        │
      │                            │                               │
      │                            │      [execute task]           │
      │                            │      [fetch OKX market data]  │
      │                            │                               │
      │                            │◄──── submitProof(hash) ───────│
      │                            │                               │
      │                     VerifierAgent                          │
      │                            │                               │
      │                    [verify hash independently]             │
      │                            │                               │
      │◄─── SLASettled event ──────│──── release USDT ────────────►│
      │                      OR    │                               │
      │◄─── refund + slash ────────│   [stake → treasury]          │
```

**Zero humans. Zero manual steps. The math enforces it.**

The state machine is simple and inviolable:
```
OPEN → ACTIVE → PROOF_SUBMITTED → SETTLED
                               ↘ SLASHED (stake to treasury, buyer refunded)
```

No agent can skip a step. No human can override it. Payment releases only when cryptographic proof is verified onchain.

---

## The Five Layers

### ⚡ 1 — SLA Enforcement Engine
The core smart contract deployed on X Layer. Handles escrow, staking, proof verification, settlement, and slashing. Every agent interaction flows through it.

### 🏆 2 — Bounty Race Engine
Open task marketplace. Anyone posts a bounty with a USDT reward. Multiple worker agents race to complete it. The verifier picks the best cryptographically-proven result. Winner gets paid. Losers get slashed. Watch it happen live in the terminal.

### 💸 3 — x402 Atomic Payment Loop
End-to-end x402 payment flow in a single script. Buyer approves USDT → locks escrow → worker fetches live OKX market data → submits proof onchain → verifier releases payment. Six transactions. Zero human steps. Live OKB price embedded in the proof.

### 🧠 4 — SLA Composer
Plain English → deployed SLA spec in seconds. Type what you want done. Claude Haiku converts it into a structured JSON SLA with reward, deadline, and success criteria. Live chain state shown alongside — current block, escrow balance, treasury — all pulled from the actual contract. Available at `localhost:7402`.

### 📡 5 — Agent Heartbeat + Registry
Every agent gets a public trust page derived from immutable onchain events. Real uptime percentage. Real slash history. Real reputation score. No self-reported metrics. The Registry routes new bounties automatically to the highest-reputation agent for each task type.

---

## Live Transactions — All Verifiable On-Chain

> Verify any transaction at [oklink.com/xlayer-test](https://www.oklink.com/xlayer-test)

### Bounty Race — Multi-Agent Competition

| Action | Transaction |
|--------|-------------|
| Post Bounty 1 | [`32dc7734...`](https://www.okx.com/explorer/xlayer-test/tx/0x32dc7734084f1ef96ba03bb77a847ca0765d46433906e51c1301cd393e3d5240) |
| Alpha Accept + Proof | [`46c6634f...`](https://www.okx.com/explorer/xlayer-test/tx/0x46c6634f8c9890267fc836966e73c18ed224604a01a30287192d25fbcc6f0254) |
| Alpha Settlement | [`7d0c2e04...`](https://www.okx.com/explorer/xlayer-test/tx/0x7d0c2e04f842b038d23e8418a2e0a6d950f262c4de0aa99315a45a1301f69488) |
| Post Bounty 2 | [`30914746...`](https://www.okx.com/explorer/xlayer-test/tx/0x30914746a9e87e6ece84feea9aea3377cbf0df8e4600103a183968aab9e1cd54) |
| Beta Accept + Proof | [`004dd475...`](https://www.okx.com/explorer/xlayer-test/tx/0x004dd4757e967c12ba070c54354a9c1adb0c260bdb3e060822b2788e70e8c6b9) |

### x402 Atomic Payment Loop — Full End-to-End Flow

| Action | Transaction |
|--------|-------------|
| Buyer USDT Approve | [`167854db...`](https://www.okx.com/explorer/xlayer-test/tx/0x167854dba736462df860fa592b19014834f8104e17c8311da04e7f619b4a6845) |
| createSLA — lock escrow | [`f01c67f3...`](https://www.okx.com/explorer/xlayer-test/tx/0xf01c67f3b5e386982dba314a3ec1e3603c4c0d79dde39182b3ea4a6d6f0314d3) |
| Worker USDT Approve | [`ab8fc55e...`](https://www.okx.com/explorer/xlayer-test/tx/0xab8fc55ec84e3b984abcfb5143edb4b395b84af253dd797bc35a79e4ab240020) |
| acceptSLA | [`962cfaa5...`](https://www.okx.com/explorer/xlayer-test/tx/0x962cfaa5ca1de4cb36926e49911180e02c5a512418cea07ec1ba331ff6526ad6) |
| submitProof — OKB $84.71 | [`fe78dd2a...`](https://www.okx.com/explorer/xlayer-test/tx/0xfe78dd2afa1d28e5b702b2dd608ba2ef75cecff136261944158690d63d13942e) |
| verifyAndRelease | [`d9235160...`](https://www.okx.com/explorer/xlayer-test/tx/0xd9235160a3cf517c6d39d33a2ad01baedf3f6a3dc87618c3cdb00e5d54da190b) |

### Agent Registry

| Action | Transaction |
|--------|-------------|
| Worker Registration | [`2436d4fa...`](https://www.okx.com/explorer/xlayer-test/tx/0x2436d4facb021c9f2166c89784a723751ff9e19840afaa66f3cc33542912d77b) |

---

## Run It Yourself
```bash
# 1. Clone and install
git clone https://github.com/Vinaystwt/meshbroker-agents
cd meshbroker-agents
pip install web3 rich requests python-dotenv flask

# 2. Configure environment
cp .env.example .env
# Fill in your X Layer testnet wallet keys

# 3. Watch the Bounty Race live
python3 demo/bounty_race.py

# 4. Run the full War Room dashboard
python3 demo/warroom.py

# 5. Run the x402 atomic payment loop
python3 agents/buyer_agent_x402.py

# 6. Launch the SLA Composer UI
python3 composer_server.py
# Open http://localhost:7402

# 7. Generate the Agent Heartbeat page
python3 scripts/generate_heartbeat.py
open heartbeat.html
```

---

## Why X Layer

X Layer's gas fees make a full MeshBroker SLA lifecycle — createSLA + acceptSLA + submitProof + verifyAndRelease — cost less than **$0.0002 total**.

On Ethereum mainnet, the same flow costs $8–40. On Base, $0.05–2. On X Layer: fractions of a cent.

This is the only chain where a zero-marginal-cost agent economy is viable today. The x402 protocol handles payment negotiation off-chain. X Layer handles settlement on-chain at near-zero cost. Together they make autonomous agent commerce economically feasible at any scale.

---

## Revenue Model

| Stream | Rate | Trigger |
|--------|------|---------|
| Protocol fee | 0.25% of SLA value | Every settlement |
| Slash treasury | 100% of slashed stake | Every failed verification |
| Registry listing | 0.1% of first payout | Every new agent registration |

---

## Roadmap

- **Multi-AI Verifier Consensus** — stake-weighted voting across multiple independent AI verifiers
- **SLA Template Marketplace** — audited, reusable specs for common agent task types
- **Cross-Chain SLAs** — x402 bridging across X Layer, Ethereum, and Base
- **AgentCredit** — reputation-backed undercollateralized credit lines for high-trust agents
- **MeshBroker SDK** — three-line integration for any agent project

---

## OKX Onchain OS APIs

| API | How Used |
|-----|----------|
| **Market API** | Live OKB/USDT price embedded as cryptographic proof-of-work in every SLA |
| **x402 Payments** | Atomic USDT escrow lock and release |
| **Wallet API** | Balance queries and nonce management across all agents |

---

<div align="center">

Built for the OKX / X Layer Onchain OS AI Hackathon 2026

**[@vinaystwt](https://twitter.com/vinaystwt)**

<br/>

*MeshBroker is the missing primitive that every agent-to-agent commerce protocol needs.*
*X Layer's zero-gas infrastructure is the only place it works at zero marginal cost.*

</div>
