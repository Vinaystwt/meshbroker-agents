"""
MeshBroker Bounty Race Demo
Run this to watch 2 workers race for a live OKX data bounty.
Winner gets paid. Loser gets slashed. All on X Layer testnet.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.bounty_engine import BountyEngine

DIVIDER = "=" * 62

def main():
    print(f"\n{DIVIDER}")
    print(" MESHBROKER BOUNTY RACE — X LAYER TESTNET")
    print(" Two AI agents race. Winner paid. Loser slashed.")
    print(f"{DIVIDER}\n")

    engine = BountyEngine()

    # --- POST BOUNTY ---
    print("📋 STEP 1: Posting open bounty on MeshBroker...\n")
    sla_id, post_tx = engine.post_bounty(
        "Fetch live OKB/USDT price from OKX Market API and return verified JSON report",
        reward_units=10_000_000  # 10 USDT
    )
    if not sla_id:
        print("❌ Failed to post bounty. Check your .env and contract address.")
        return

    print(f"\n  ✅ Bounty live on-chain!")
    print(f"  SLA ID  : {sla_id}")
    print(f"  Post TX : {post_tx}")
    print(f"\n{DIVIDER}\n")

    # --- WORKER ALPHA RACES (honest) ---
    print("🏃 STEP 2: Worker Alpha enters the race (honest)...\n")
    alpha_hash, alpha_data, alpha_tx = engine.worker_race(sla_id, "Alpha", introduce_error=False)
    if not alpha_hash:
        print("❌ Alpha failed to enter race.")
        return

    print(f"\n  Alpha proof TX: {alpha_tx}")
    print(f"  Alpha data: {alpha_data[:80]}...\n")

    # --- POST A SECOND BOUNTY FOR BETA TO DEMONSTRATE SLASH ---
    print(f"{DIVIDER}")
    print("📋 STEP 3: Posting second bounty for Beta (bad actor demo)...\n")
    sla_id_2, post_tx_2 = engine.post_bounty(
        "Fetch live OKB/USDT price — second concurrent bounty",
        reward_units=10_000_000
    )
    if not sla_id_2:
        print("❌ Failed to post second bounty.")
        return

    print(f"\n  SLA ID 2: {sla_id_2}")
    print(f"  Post TX 2: {post_tx_2}\n")

    print("🏃 STEP 4: Worker Beta enters race (bad actor — fabricated data)...\n")
    beta_hash, beta_data, beta_tx = engine.worker_race(sla_id_2, "Beta", introduce_error=True)

    print(f"\n{DIVIDER}")
    print("⚖️  STEP 5: Verifier judges both races...\n")

    # Settle Alpha (winner)
    win_tx, _ = engine.judge_and_settle(sla_id, alpha_hash)

    # Slash Beta (loser)
    _, slash_tx = engine.judge_and_settle(sla_id_2, beta_hash or "0x00", loser_sla_id=sla_id_2)

    print(f"\n{DIVIDER}")
    print(" RACE COMPLETE — FULL TX HASH SUMMARY")
    print(f"{DIVIDER}")
    print(f"  Bounty 1 Post   : {post_tx}")
    print(f"  Alpha Accept+Proof: {alpha_tx}")
    print(f"  Alpha Settlement : {win_tx}")
    print(f"  Bounty 2 Post   : {post_tx_2}")
    if beta_tx:
        print(f"  Beta Accept+Proof: {beta_tx}")
    if slash_tx:
        print(f"  Beta Slash TX   : {slash_tx}")
    print(f"{DIVIDER}")
    print("\n  ✅ Copy these TX hashes into your README and submission form.")
    print("  🔍 Verify all at: https://www.oklink.com/xlayer-test\n")

if __name__ == "__main__":
    main()
