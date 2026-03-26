import os
import random
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

def get_demo_reputation(address: str):
    """
    Simulates reading SLASettled and SLADisputed events to calculate an on-chain score.
    In production, this scans the contract's event history via Web3.
    """
    # Deterministic mock based on address for demo purposes
    random.seed(address)
    jobs_done = random.randint(5, 50)
    jobs_failed = random.randint(0, 3)
    
    score = 50 + (jobs_done * 2) - (jobs_failed * 10)
    score = max(0, min(100, score))
    
    tier = "🥇 GOLD" if score >= 80 else "🥈 SILVER" if score >= 50 else "🔴 BRONZE"
    
    return {
        "agent": address, "trust_score": score, "tier": tier,
        "jobs_completed": jobs_done, "jobs_failed": jobs_failed,
        "total_earned": round(jobs_done * 8.5, 2)
    }

if __name__ == "__main__":
    addr = os.getenv("VERIFIER_AGENT_ADDRESS", "0x0000000000000000000000000000000000000000")
    print("\n--- AGENT REPUTATION LEDGER ---")
    rep = get_demo_reputation(addr)
    for k, v in rep.items():
        print(f"{k.replace('_', ' ').title():20}: {v}")
    print("-------------------------------\n")
