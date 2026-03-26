import os
import time
import logging
from web3 import Web3
from dotenv import load_dotenv
from agents.worker_agent import WorkerAgent

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(name)s: %(message)s')
logger = logging.getLogger("WarRoom-Scenario1")

def run_honest_scenario():
    logger.info("🟢 STARTING SCENARIO 1: THE HONEST WORKER (WITH OKX API)")
    w3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
    buyer_acc = w3.eth.account.from_key(os.getenv("VERIFIER_PRIVATE_KEY"))
    mesh_addr = Web3.to_checksum_address(os.getenv("MESHBROKER_ADDRESS").strip("'\" "))
    usdt_addr = Web3.to_checksum_address(os.getenv("USDT_ADDRESS").strip("'\" "))
    verifier_addr = Web3.to_checksum_address(os.getenv("VERIFIER_AGENT_ADDRESS").strip("'\" "))
    
    mesh_abi = [
        {"name": "createSLA", "type": "function", "inputs": [{"name": "p", "type": "tuple", "components": [{"name": "paymentToken", "type": "address"}, {"name": "paymentAmount", "type": "uint256"}, {"name": "taskSpecHash", "type": "bytes32"}, {"name": "slaTermsHash", "type": "bytes32"}, {"name": "deadline", "type": "uint256"}, {"name": "verifierAgent", "type": "address"}]}]},
        {"name": "verifyAndRelease", "type": "function", "inputs": [{"name": "slaId", "type": "bytes32"}, {"name": "resultHash", "type": "bytes32"}]}
    ]
    contract = w3.eth.contract(address=mesh_addr, abi=mesh_abi)

    # 1. Create SLA
    task_hash = w3.keccak(text=f"Honest-Task-{time.time()}")
    create_tx = contract.functions.createSLA({
        'paymentToken': usdt_addr, 'paymentAmount': 10000000, 'taskSpecHash': task_hash,
        'slaTermsHash': task_hash, 'deadline': int(time.time()) + 86400, 'verifierAgent': verifier_addr
    }).build_transaction({
        'from': buyer_acc.address, 'nonce': w3.eth.get_transaction_count(buyer_acc.address), 'gas': 1200000, 'gasPrice': int(w3.eth.gas_price * 1.2)
    })
    
    receipt = w3.eth.wait_for_transaction_receipt(w3.eth.send_raw_transaction(w3.eth.account.sign_transaction(create_tx, buyer_acc.key).raw_transaction))
    
    sla_id = None
    for log in receipt.logs:
        if log.address.lower() == mesh_addr.lower():
            sla_id = log.topics[1]
            break

    logger.info(f"✅ SLA Created: {sla_id.hex()}")

    # 2. Worker Executes Task & Fetches OKX Data
    worker = WorkerAgent()
    worker.execute_honest_task(sla_id.hex())

    # 3. Verifier Approves
    logger.info("Step 4: Verifier Agent approving the OKX API data...")
    time.sleep(5)
    
    try:
        release_tx = contract.functions.verifyAndRelease(sla_id, w3.keccak(text="dummy")).build_transaction({
            'from': buyer_acc.address, 'nonce': w3.eth.get_transaction_count(buyer_acc.address), 'gas': 1000000, 'gasPrice': int(w3.eth.gas_price * 1.2)
        })
        w3.eth.wait_for_transaction_receipt(w3.eth.send_raw_transaction(w3.eth.account.sign_transaction(release_tx, buyer_acc.key).raw_transaction))
        logger.info("🎉 SUCCESS: Payment Released to Worker!")
    except Exception as e:
        logger.warning(f"Note: verifyAndRelease failed (likely ABI mismatch, check your contract): {e}")

if __name__ == "__main__":
    run_honest_scenario()
