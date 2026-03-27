# MeshBroker — Engineering Context File
## Load this at the start of every coding session

### Stack
- Python 3.14, web3.py, rich, requests, dotenv
- X Layer Testnet (zkEVM), MockUSDT (6 decimals), MeshBroker contract
- All agents use VERIFIER_PRIVATE_KEY for buyer/verifier, WORKER_PRIVATE_KEY for worker

### Repo Structure
```
agents/
  buyer_agent.py         — createSLA(), uses VERIFIER_PRIVATE_KEY
  worker_agent.py        — acceptSLA(), submitProof(), OKX Market API
  verifier_agent.py      — verifyAndRelease(), rejectProof() slash
  bounty_engine.py       — full bounty race engine
  buyer_agent_x402.py    — COMPLETE x402 atomic loop (6 TXs end to end)
  registry_agent.py      — on-chain agent registration + best-worker query
core/
  composer_engine.py     — Claude Haiku → JSON SLA spec (Python class)
  reputation.py          — real on-chain event reads
demo/
  warroom.py             — Rich dashboard, live chain polling, 3 scenarios
  bounty_race.py         — 2-worker race, winner paid, loser slashed
  full_demo.sh           — runs everything in sequence
scripts/
  generate_heartbeat.py  — generates heartbeat.html
composer_server.py       — Flask server, POST /compose, GET /status
dashboard/composer.html  — redesigned dark UI, wired to composer_server.py
run_scenario_1.py        — honest worker scenario
check_treasury.py        — reads protocol treasury balance
heartbeat.html           — live agent trust page
registry_snapshot.json   — persisted agent registry state
```

### Current Status
- [x] War Room — live on-chain reads, 3 scenarios CONFIRMED WORKING
- [x] Reputation — real event reads with mock fallback CONFIRMED WORKING
- [x] Bounty Engine — post/race/judge CONFIRMED WORKING
- [x] Bounty Race demo — 2-worker race, slash loser CONFIRMED WORKING
- [x] Heartbeat page — CONFIRMED WORKING (Block #26,135,570)
- [x] x402 atomic loop — CONFIRMED WORKING (6 TX hashes)
- [x] Composer server — CONFIRMED WORKING (localhost:7402)
- [x] Agent Registry — CONFIRMED WORKING (1 registry TX)
- [x] main branch pushed to GitHub
- [ ] README final version — not yet written
- [ ] X thread — not yet posted
- [ ] Video recorded — not yet done
- [ ] Form submitted — not yet done

### All Confirmed Live TX Hashes (X Layer Testnet)
Bounty Race:
- Bounty 1 Post     : 32dc7734084f1ef96ba03bb77a847ca0765d46433906e51c1301cd393e3d5240
- Alpha Accept+Proof: 46c6634f8c9890267fc836966e73c18ed224604a01a30287192d25fbcc6f0254
- Alpha Settlement  : 7d0c2e04f842b038d23e8418a2e0a6d950f262c4de0aa99315a45a1301f69488
- Bounty 2 Post     : 30914746a9e87e6ece84feea9aea3377cbf0df8e4600103a183968aab9e1cd54
- Beta Accept+Proof : 004dd4757e967c12ba070c54354a9c1adb0c260bdb3e060822b2788e70e8c6b9

x402 Atomic Loop:
- Buyer USDT Approve : 167854dba736462df860fa592b19014834f8104e17c8311da04e7f619b4a6845
- createSLA (lock)   : f01c67f3b5e386982dba314a3ec1e3603c4c0d79dde39182b3ea4a6d6f0314d3
- Worker USDT Approve: ab8fc55ec84e3b984abcfb5143edb4b395b84af253dd797bc35a79e4ab240020
- acceptSLA          : 962cfaa5ca1de4cb36926e49911180e02c5a512418cea07ec1ba331ff6526ad6
- submitProof        : fe78dd2afa1d28e5b702b2dd608ba2ef75cecff136261944158690d63d13942e
- verifyAndRelease   : d9235160a3cf517c6d39d33a2ad01baedf3f6a3dc87618c3cdb00e5d54da190b

Agent Registry:
- Registration TX   : 2436d4facb021c9f2166c89784a723751ff9e19840afaa66f3cc33542912d77b

TOTAL: 12 confirmed live TX hashes

### Live Chain Data (last confirmed)
- Block: #26,141,117+
- Escrow Balance: 225.62 USDT
- Protocol Treasury: accumulating (slashed funds confirmed)
- Worker Balance: 1015.10 USDT
- Buyer Balance: 749.42 USDT

### Architecture Notes for New Code
- No contracts/ folder — ABI hardcoded inline in each agent
- No Hardhat/Foundry — pure Python + web3.py only
- Gas: always int(w3.eth.gas_price * 1.2)
- Nonce: always fetch with 'pending', increment manually for sequential TXs
- MockUSDT: 6 decimals, 10 USDT = 10_000_000 units

### Next Phases
Phase 6: README final + X thread (5 tweets) + video script (4 min)
Phase 7: GitHub cleanup + Loom recording + form submission
