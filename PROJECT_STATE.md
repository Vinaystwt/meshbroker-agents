# MeshBroker — Engineering Context File
## Load this at the start of every coding session

### Stack
- Python 3.14, web3.py, rich, requests, dotenv
- X Layer Testnet (zkEVM), MockUSDT (6 decimals), MeshBroker contract
- All agents use VERIFIER_PRIVATE_KEY for buyer/verifier, WORKER_PRIVATE_KEY for worker

### Repo Structure
```
agents/
  buyer_agent.py       — createSLA(), uses VERIFIER_PRIVATE_KEY
  worker_agent.py      — acceptSLA(), submitProof(), fetches OKX Market API
  verifier_agent.py    — verifyAndRelease(), rejectProof() (slash)
  bounty_engine.py     — full bounty race engine (post/race/judge)
core/
  composer_engine.py   — Claude Haiku API → JSON SLA spec
  reputation.py        — on-chain event reads → trust scores
demo/
  warroom.py           — Rich terminal dashboard, live chain polling
  bounty_race.py       — 2-worker race demo, prints all TX hashes
  full_demo.sh         — runs everything in sequence
scripts/
  generate_heartbeat.py — generates heartbeat.html (static, no server)
run_scenario_1.py      — honest worker scenario, prints TX hashes
check_treasury.py      — reads protocol treasury balance
heartbeat.html         — generated agent trust page (open in browser)
```

### Contract Functions (ABI patterns in agents)
- createSLA(tuple) → emits event with slaId in topics[1]
- acceptSLA(bytes32)
- submitProof(bytes32, bytes32, string)
- verifyAndRelease(bytes32, bytes32)
- rejectProof(bytes32, string)
- protocolTreasury(address) → uint256
- MockUSDT.balanceOf(address) → uint256
- MockUSDT.approve(address, uint256) → bool

### .env Keys Used
RPC_URL, MESHBROKER_ADDRESS, USDT_ADDRESS,
WORKER_PRIVATE_KEY, VERIFIER_PRIVATE_KEY, VERIFIER_AGENT_ADDRESS,
ANTHROPIC_API_KEY

### Current Status
- [x] War Room — live on-chain reads, 3 scenarios CONFIRMED WORKING
- [x] Reputation — real event reads with mock fallback CONFIRMED WORKING
- [x] Bounty Engine — post/race/judge CONFIRMED WORKING
- [x] Bounty Race demo — 2-worker race, slash loser CONFIRMED WORKING
- [x] Heartbeat page — CONFIRMED WORKING (Block #26,135,570)
- [x] main branch pushed to GitHub
- [ ] x402 atomic loop — not yet built
- [ ] Agent Registry — not yet built
- [ ] README final version — not yet written
- [ ] X thread — not yet posted
- [ ] Video recorded — not yet done

### Confirmed Live TX Hashes (X Layer Testnet)
Bounty Race Run 1:
- Bounty 1 Post     : 32dc7734084f1ef96ba03bb77a847ca0765d46433906e51c1301cd393e3d5240
- Alpha Accept+Proof: 46c6634f8c9890267fc836966e73c18ed224604a01a30287192d25fbcc6f0254
- Alpha Settlement  : 7d0c2e04f842b038d23e8418a2e0a6d950f262c4de0aa99315a45a1301f69488
- Bounty 2 Post     : 30914746a9e87e6ece84feea9aea3377cbf0df8e4600103a183968aab9e1cd54
- Beta Accept+Proof : 004dd4757e967c12ba070c54354a9c1adb0c260bdb3e060822b2788e70e8c6b9

### Known Working
- heartbeat.html — live block #26,135,570, escrow 215.57 USDT, treasury 1.05 USDT
- War Room — all 3 scenarios complete, live chain panel confirmed
- OKX Market API — live OKB price $85.09 fetched in race
- MockUSDT approve+transfer working
- Protocol Treasury accumulating slashed funds (1.05 USDT confirmed)
- Slashing mechanic — confirmed working on-chain

### Architecture Notes for New Code
- No contracts/ folder — contract is already deployed, ABI hardcoded inline in each agent
- No Hardhat/Foundry — pure Python + web3.py only
- dashboard/composer.html exists but is static UI only, no backend wired
- Bounty Engine uses same MeshBroker contract — createSLA = post bounty
- Worker uses WORKER_PRIVATE_KEY, Buyer/Verifier use VERIFIER_PRIVATE_KEY
- Gas: always use int(w3.eth.gas_price * 1.2), never hardcode gas price
- Nonce: always fetch with 'pending' tag, increment manually for sequential TXs

### Next Phases
Phase 4: x402 atomic payment loop (agents/buyer_agent_x402.py)
Phase 5: Agent Registry (agents/registry_agent.py)  
Phase 6: README final + X thread + video script
Phase 7: Loom recording + form submission
