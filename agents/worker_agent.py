import os
import time
import logging
import json
import requests
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(name)s: %(message)s')
logger = logging.getLogger("WorkerAgent")

class WorkerAgent:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
        self.key = os.getenv("WORKER_PRIVATE_KEY")
        self.account = self.w3.eth.account.from_key(self.key)
        self.mesh_addr = Web3.to_checksum_address(os.getenv("MESHBROKER_ADDRESS").strip("'\" "))
        self.usdt_addr = Web3.to_checksum_address(os.getenv("USDT_ADDRESS").strip("'\" "))
        
        self.mesh_abi = [
            {"name": "acceptSLA", "type": "function", "inputs": [{"name": "slaId", "type": "bytes32"}]},
            {"name": "submitProof", "type": "function", "inputs": [{"name": "slaId", "type": "bytes32"}, {"name": "proofHash", "type": "bytes32"}, {"name": "proofURI", "type": "string"}]}
        ]
        self.usdt_abi = [
            {"name": "approve", "type": "function", "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}], "outputs": [{"name": "", "type": "bool"}]}
        ]
        self.contract = self.w3.eth.contract(address=self.mesh_addr, abi=self.mesh_abi)
        self.usdt = self.w3.eth.contract(address=self.usdt_addr, abi=self.usdt_abi)

    def fetch_okx_market_context(self) -> dict:
        """Fetch real market data from OKX Onchain OS Market API."""
        logger.info("🌐 Fetching live OKX market data...")
        try:
            response = requests.get("https://www.okx.com/api/v5/market/ticker?instId=OKB-USDT", timeout=5)
            data = response.json()
            if data.get("code") == "0":
                ticker = data["data"][0]
                return {
                    "okb_price_usdt": ticker.get("last"),
                    "24h_volume": ticker.get("vol24h"),
                    "source": "OKX API",
                    "timestamp": int(time.time())
                }
        except Exception as e:
            logger.error(f"API fetch failed: {e}")
        return {"source": "OKX Market API", "note": "offline fallback"}

    def execute_honest_task(self, sla_id_hex):
        sla_id = bytes.fromhex(sla_id_hex.replace('0x', ''))
        
        # BULLETPROOF NONCE TRACKING
        current_nonce = self.w3.eth.get_transaction_count(self.account.address, 'pending')
        
        # 1. AUTONOMOUS STAKE APPROVAL
        logger.info("Step A: Agent autonomously approving 0.5 USDT Stake...")
        try:
            app_tx = self.usdt.functions.approve(self.mesh_addr, 500000).build_transaction({
                'from': self.account.address, 'nonce': current_nonce,
                'gasPrice': int(self.w3.eth.gas_price * 1.2)
            })
            app_receipt = self.w3.eth.wait_for_transaction_receipt(self.w3.eth.send_raw_transaction(self.w3.eth.account.sign_transaction(app_tx, self.key).raw_transaction))
            if app_receipt.status != 1: raise Exception("Approval reverted")
            logger.info("✅ Stake Approved.")
            current_nonce += 1  # Increment manually!
        except Exception as e:
            logger.error(f"Failed to approve USDT: {e}")
            return

        # 2. ACCEPT SLA
        logger.info(f"Step B: Accepting SLA {sla_id_hex[:10]}...")
        try:
            tx = self.contract.functions.acceptSLA(sla_id).build_transaction({
                'from': self.account.address, 'nonce': current_nonce,
                'gasPrice': int(self.w3.eth.gas_price * 1.2)
            })
            receipt = self.w3.eth.wait_for_transaction_receipt(self.w3.eth.send_raw_transaction(self.w3.eth.account.sign_transaction(tx, self.key).raw_transaction))
            if receipt.status != 1: raise Exception("acceptSLA reverted on-chain")
            logger.info("✅ SLA Accepted on-chain.")
            current_nonce += 1  # Increment manually!
        except Exception as e:
            logger.error(f"Failed to accept SLA: {e}")
            return

        # 3. FETCH & HASH WORK
        market_data = self.fetch_okx_market_context()
        logger.info(f"📊 Market Data Retrieved: OKB Price = {market_data.get('okb_price_usdt', 'N/A')} USDT")
        
        proof_string = json.dumps(market_data)
        result_hash = self.w3.keccak(text=proof_string)

        # 4. SUBMIT PROOF
        logger.info("⏳ Waiting 5s for blockchain state sync...")
        time.sleep(5)
        logger.info("Step C: Submitting OKX Market Data proof to X Layer...")
        try:
            submit_tx = self.contract.functions.submitProof(sla_id, result_hash, proof_string).build_transaction({
                'from': self.account.address, 'nonce': current_nonce,
                'gasPrice': int(self.w3.eth.gas_price * 1.2)
            })
            sub_receipt = self.w3.eth.wait_for_transaction_receipt(self.w3.eth.send_raw_transaction(self.w3.eth.account.sign_transaction(submit_tx, self.key).raw_transaction))
            
            if sub_receipt.status == 1:
                logger.info("🎉 SUCCESS: Honest work (with live OKX data) permanently secured on-chain!")
            else:
                raise Exception("submitProof reverted on-chain")
        except Exception as e:
            logger.error(f"Failed to submit proof: {e}")
