import os
import time
import logging
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(name)s: %(message)s')
logger = logging.getLogger("BuyerAgent")

class BuyerAgent:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
        self.key = os.getenv("VERIFIER_PRIVATE_KEY") # Buyer and Verifier share the same account for demo
        self.account = self.w3.eth.account.from_key(self.key)
        self.mesh_addr = Web3.to_checksum_address(os.getenv("MESHBROKER_ADDRESS").strip("'\" "))
        self.usdt_addr = Web3.to_checksum_address(os.getenv("USDT_ADDRESS").strip("'\" "))
        
        self.abi = [
            {"name": "createSLA", "type": "function", "inputs": [{"name": "p", "type": "tuple", "components": [{"name": "paymentToken", "type": "address"}, {"name": "paymentAmount", "type": "uint256"}, {"name": "taskSpecHash", "type": "bytes32"}, {"name": "slaTermsHash", "type": "bytes32"}, {"name": "deadline", "type": "uint256"}, {"name": "verifierAgent", "type": "address"}]}]}
        ]
        self.contract = self.w3.eth.contract(address=self.mesh_addr, abi=self.abi)

    def create_job(self, task_name, reward_amount=10000000):
        logger.info(f"💼 BUYER ACTION: Creating new SLA for task '{task_name}'...")
        task_hash = self.w3.keccak(text=f"{task_name}-{time.time()}")
        
        try:
            tx = self.contract.functions.createSLA({
                'paymentToken': self.usdt_addr, 'paymentAmount': reward_amount,
                'taskSpecHash': task_hash, 'slaTermsHash': task_hash,
                'deadline': int(time.time()) + 86400, 'verifierAgent': self.account.address
            }).build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address, 'pending'),
                'gasPrice': int(self.w3.eth.gas_price * 1.2)
            })
            receipt = self.w3.eth.wait_for_transaction_receipt(self.w3.eth.send_raw_transaction(self.w3.eth.account.sign_transaction(tx, self.key).raw_transaction))
            
            for log in receipt.logs:
                if log.address.lower() == self.mesh_addr.lower():
                    logger.info(f"✅ Job Created. SLA ID: {log.topics[1].hex()}")
                    return log.topics[1].hex()
        except Exception as e:
            logger.error(f"Failed to create SLA: {e}")
            return None
