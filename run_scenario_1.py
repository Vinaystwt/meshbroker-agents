"""
MeshBroker Scenario 1 — Honest Worker with OKX API
Prints every TX hash cleanly for submission form.
"""
import os, time, logging
from web3 import Web3
from dotenv import load_dotenv
from agents.worker_agent import WorkerAgent
from agents.verifier_agent import VerifierAgent

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(name)s: %(message)s')
logger = logging.getLogger("Scenario1")

DIVIDER = "=" * 60

def run():
    logger.info(f"\n{DIVIDER}")
    logger.info(" MESHBROKER SCENARIO 1: HONEST WORKER + OKX API")
    logger.info(f"{DIVIDER}\n")

    w3            = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
    buyer_key     = os.getenv("VERIFIER_PRIVATE_KEY")
    buyer_acc     = w3.eth.account.from_key(buyer_key)
    mesh_addr     = Web3.to_checksum_address(os.getenv("MESHBROKER_ADDRESS").strip("'\" "))
    usdt_addr     = Web3.to_checksum_address(os.getenv("USDT_ADDRESS").strip("'\" "))
    verifier_addr = Web3.to_checksum_address(os.getenv("VERIFIER_AGENT_ADDRESS").strip("'\" "))

    mesh_abi = [
        {"name":"createSLA","type":"function",
         "inputs":[{"name":"p","type":"tuple","components":[
             {"name":"paymentToken","type":"address"},
             {"name":"paymentAmount","type":"uint256"},
             {"name":"taskSpecHash","type":"bytes32"},
             {"name":"slaTermsHash","type":"bytes32"},
             {"name":"deadline","type":"uint256"},
             {"name":"verifierAgent","type":"address"}]}]},
        {"name":"verifyAndRelease","type":"function",
         "inputs":[{"name":"slaId","type":"bytes32"},
                    {"name":"resultHash","type":"bytes32"}]}
    ]
    contract = w3.eth.contract(address=mesh_addr, abi=mesh_abi)

    # 1. Create SLA
    task_hash  = w3.keccak(text=f"OKX-Market-Data-{time.time()}")
    nonce      = w3.eth.get_transaction_count(buyer_acc.address, 'pending')
    create_tx  = contract.functions.createSLA({
        'paymentToken': usdt_addr, 'paymentAmount': 10_000_000,
        'taskSpecHash': task_hash, 'slaTermsHash': task_hash,
        'deadline': int(time.time()) + 86400, 'verifierAgent': verifier_addr
    }).build_transaction({'from': buyer_acc.address, 'nonce': nonce,
                          'gasPrice': int(w3.eth.gas_price * 1.2)})
    signed   = w3.eth.account.sign_transaction(create_tx, buyer_key)
    tx_hash1 = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt1 = w3.eth.wait_for_transaction_receipt(tx_hash1)

    sla_id = None
    for log in receipt1.logs:
        if log.address.lower() == mesh_addr.lower() and len(log.topics) >= 2:
            sla_id = log.topics[1]
            break

    logger.info(f"TX 1 — createSLA        : {tx_hash1.hex()}")
    logger.info(f"        SLA ID           : {sla_id.hex() if sla_id else 'not found'}")

    # 2. Worker executes (fetches OKX data, submits proof)
    worker = WorkerAgent()
    worker.execute_honest_task(sla_id.hex())

    # 3. Verifier releases
    time.sleep(5)
    verifier = VerifierAgent()
    try:
        rel_abi = [{"name":"verifyAndRelease","type":"function",
                    "inputs":[{"name":"slaId","type":"bytes32"},
                               {"name":"resultHash","type":"bytes32"}]}]
        rel_c   = w3.eth.contract(address=mesh_addr, abi=rel_abi)
        rel_tx  = rel_c.functions.verifyAndRelease(
            sla_id,
            w3.keccak(text="release")
        ).build_transaction({
            'from': verifier.account.address,
            'nonce': w3.eth.get_transaction_count(verifier.account.address, 'pending'),
            'gasPrice': int(w3.eth.gas_price * 1.2)
        })
        signed3  = w3.eth.account.sign_transaction(rel_tx, verifier.key)
        tx_hash3 = w3.eth.send_raw_transaction(signed3.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_hash3)
        logger.info(f"TX 3 — verifyAndRelease : {tx_hash3.hex()}")
    except Exception as e:
        logger.warning(f"verifyAndRelease note: {e}")

    logger.info(f"\n{DIVIDER}")
    logger.info(" SCENARIO 1 COMPLETE")
    logger.info(f" Verify at: https://www.oklink.com/xlayer-test/tx/<hash>")
    logger.info(f"{DIVIDER}\n")

if __name__ == "__main__":
    run()
