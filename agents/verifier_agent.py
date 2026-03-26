import os
import logging
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(name)s: %(message)s')
logger = logging.getLogger("VerifierAgent")

class VerifierAgent:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
        self.key = os.getenv("VERIFIER_PRIVATE_KEY")
        self.account = self.w3.eth.account.from_key(self.key)
        self.mesh_addr = Web3.to_checksum_address(os.getenv("MESHBROKER_ADDRESS").strip("'\" "))
        
        self.abi = [
            {"name": "verifyAndRelease", "type": "function", "inputs": [{"name": "slaId", "type": "bytes32"}, {"name": "resultHash", "type": "bytes32"}]},
            {"name": "rejectProof", "type": "function", "inputs": [{"name": "slaId", "type": "bytes32"}, {"name": "reason", "type": "string"}]}
        ]
        self.contract = self.w3.eth.contract(address=self.mesh_addr, abi=self.abi)

    def slash_worker(self, sla_id_hex, reason="Hallucination detected by AI. Stake slashed."):
        logger.info(f"🚨 VERIFIER ACTION: Slashing worker for SLA {sla_id_hex[:10]}...")
        sla_id = bytes.fromhex(sla_id_hex.replace('0x', ''))
        
        try:
            tx = self.contract.functions.rejectProof(sla_id, reason).build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address, 'pending'),
                'gasPrice': int(self.w3.eth.gas_price * 1.2)
            })
            receipt = self.w3.eth.wait_for_transaction_receipt(self.w3.eth.send_raw_transaction(self.w3.eth.account.sign_transaction(tx, self.key).raw_transaction))
            
            if receipt.status == 1:
                logger.info("🔪 SUCCESS: Worker slashed. Stake moved to Protocol Treasury.")
            else:
                logger.error("Failed to slash worker.")
        except Exception as e:
            logger.error(f"Slashing transaction failed: {e}")
