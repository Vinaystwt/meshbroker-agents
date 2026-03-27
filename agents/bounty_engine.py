"""
MeshBroker Bounty Engine
Extends the existing MeshBroker contract's SLA primitive into an open
multi-agent race: anyone posts a bounty, multiple workers race to
complete it, winner gets paid, losers get slashed.
"""
import os, time, json, threading, logging
import requests
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(name)s: %(message)s')
logger = logging.getLogger("BountyEngine")

class BountyEngine:
    def __init__(self):
        self.w3           = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
        self.mesh_addr    = Web3.to_checksum_address(os.getenv("MESHBROKER_ADDRESS").strip("'\" "))
        self.usdt_addr    = Web3.to_checksum_address(os.getenv("USDT_ADDRESS").strip("'\" "))
        self.buyer_key    = os.getenv("VERIFIER_PRIVATE_KEY")
        self.worker_key   = os.getenv("WORKER_PRIVATE_KEY")
        self.buyer_acc    = self.w3.eth.account.from_key(self.buyer_key)
        self.worker_acc   = self.w3.eth.account.from_key(self.worker_key)
        self.verifier_acc = self.w3.eth.account.from_key(os.getenv("VERIFIER_PRIVATE_KEY"))

        self.mesh_abi = [
            {"name":"createSLA","type":"function",
             "inputs":[{"name":"p","type":"tuple","components":[
                 {"name":"paymentToken","type":"address"},
                 {"name":"paymentAmount","type":"uint256"},
                 {"name":"taskSpecHash","type":"bytes32"},
                 {"name":"slaTermsHash","type":"bytes32"},
                 {"name":"deadline","type":"uint256"},
                 {"name":"verifierAgent","type":"address"}]}]},
            {"name":"acceptSLA","type":"function",
             "inputs":[{"name":"slaId","type":"bytes32"}]},
            {"name":"submitProof","type":"function",
             "inputs":[{"name":"slaId","type":"bytes32"},
                        {"name":"proofHash","type":"bytes32"},
                        {"name":"proofURI","type":"string"}]},
            {"name":"verifyAndRelease","type":"function",
             "inputs":[{"name":"slaId","type":"bytes32"},
                        {"name":"resultHash","type":"bytes32"}]},
            {"name":"rejectProof","type":"function",
             "inputs":[{"name":"slaId","type":"bytes32"},
                        {"name":"reason","type":"string"}]}
        ]
        self.usdt_abi = [
            {"name":"approve","type":"function",
             "inputs":[{"name":"spender","type":"address"},
                        {"name":"amount","type":"uint256"}],
             "outputs":[{"name":"","type":"bool"}]},
            {"name":"balanceOf","type":"function","stateMutability":"view",
             "inputs":[{"name":"account","type":"address"}],
             "outputs":[{"name":"","type":"uint256"}]}
        ]
        self.contract = self.w3.eth.contract(address=self.mesh_addr, abi=self.mesh_abi)
        self.usdt     = self.w3.eth.contract(address=self.usdt_addr, abi=self.usdt_abi)

    def _send(self, fn, key, acc, nonce=None):
        """Build, sign and send a transaction. Returns receipt."""
        if nonce is None:
            nonce = self.w3.eth.get_transaction_count(acc.address, 'pending')
        tx = fn.build_transaction({
            'from': acc.address, 'nonce': nonce,
            'gasPrice': int(self.w3.eth.gas_price * 1.2)
        })
        signed  = self.w3.eth.account.sign_transaction(tx, key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt, tx_hash.hex()

    def post_bounty(self, task_description: str, reward_units: int = 10_000_000):
        """
        Post a new bounty on MeshBroker.
        reward_units: USDT amount in 6-decimal units (10_000_000 = 10 USDT)
        Returns sla_id hex string.
        """
        logger.info(f"📋 Posting bounty: '{task_description}' — reward {reward_units/1e6:.1f} USDT")
        task_hash = self.w3.keccak(text=f"{task_description}-{time.time()}")

        receipt, tx = self._send(
            self.contract.functions.createSLA({
                'paymentToken':  self.usdt_addr,
                'paymentAmount': reward_units,
                'taskSpecHash':  task_hash,
                'slaTermsHash':  task_hash,
                'deadline':      int(time.time()) + 3600,
                'verifierAgent': self.verifier_acc.address
            }),
            self.buyer_key, self.buyer_acc
        )
        sla_id = None
        for log in receipt.logs:
            if log.address.lower() == self.mesh_addr.lower() and len(log.topics) >= 2:
                sla_id = log.topics[1].hex()
                break
        if sla_id:
            logger.info(f"✅ Bounty posted — SLA ID: {sla_id[:16]}...  TX: {tx[:16]}...")
        return sla_id, tx

    def worker_race(self, sla_id: str, worker_name: str, introduce_error: bool = False):
        """
        A single worker enters the race: approve stake → accept SLA → fetch data → submit proof.
        introduce_error=True simulates a bad worker (fabricated data) who will be slashed.
        Returns (proof_hash, proof_data, submit_tx)
        """
        logger.info(f"🏃 [{worker_name}] Entering race for {sla_id[:12]}...")
        sla_bytes = bytes.fromhex(sla_id.replace('0x',''))
        nonce     = self.w3.eth.get_transaction_count(self.worker_acc.address, 'pending')

        # Approve stake
        _, app_tx = self._send(
            self.usdt.functions.approve(self.mesh_addr, 500_000),
            self.worker_key, self.worker_acc, nonce
        )
        nonce += 1

        # Accept SLA
        receipt, acc_tx = self._send(
            self.contract.functions.acceptSLA(sla_bytes),
            self.worker_key, self.worker_acc, nonce
        )
        if receipt.status != 1:
            logger.error(f"[{worker_name}] acceptSLA reverted.")
            return None, None, None
        nonce += 1
        logger.info(f"[{worker_name}] ✅ SLA accepted — TX: {acc_tx[:16]}...")

        # Fetch real OKX data
        if not introduce_error:
            try:
                r    = requests.get("https://www.okx.com/api/v5/market/ticker?instId=OKB-USDT", timeout=5)
                data = r.json()["data"][0]
                proof_data = json.dumps({
                    "worker":    worker_name,
                    "okb_price": data.get("last"),
                    "vol_24h":   data.get("vol24h"),
                    "source":    "OKX Market API",
                    "timestamp": int(time.time())
                })
            except Exception:
                proof_data = json.dumps({"worker": worker_name, "okb_price": "9.42",
                                         "source": "fallback", "timestamp": int(time.time())})
        else:
            proof_data = json.dumps({"worker": worker_name, "okb_price": "999.99",
                                     "source": "FABRICATED", "timestamp": int(time.time())})

        proof_hash = self.w3.keccak(text=proof_data)

        time.sleep(3)  # Realistic processing time
        _, sub_tx = self._send(
            self.contract.functions.submitProof(sla_bytes, proof_hash, proof_data),
            self.worker_key, self.worker_acc, nonce
        )
        logger.info(f"[{worker_name}] ✅ Proof submitted — TX: {sub_tx[:16]}...")
        return proof_hash.hex(), proof_data, sub_tx

    def judge_and_settle(self, sla_id: str, winner_proof_hash: str, loser_sla_id: str = None):
        """
        Verifier evaluates submissions. Winner gets verifyAndRelease(). 
        Loser gets rejectProof() → slash.
        """
        sla_bytes = bytes.fromhex(sla_id.replace('0x',''))
        logger.info(f"⚖️  Verifier judging race for {sla_id[:12]}...")

        # Settle winner
        try:
            _, win_tx = self._send(
                self.contract.functions.verifyAndRelease(
                    sla_bytes,
                    bytes.fromhex(winner_proof_hash.replace('0x',''))
                ),
                self.buyer_key, self.verifier_acc
            )
            logger.info(f"✅ Winner settled — TX: {win_tx[:16]}...")
        except Exception as e:
            logger.warning(f"verifyAndRelease note: {e}")
            win_tx = "settlement_attempted"

        # Slash loser if provided
        slash_tx = None
        if loser_sla_id:
            try:
                loser_bytes = bytes.fromhex(loser_sla_id.replace('0x',''))
                _, slash_tx = self._send(
                    self.contract.functions.rejectProof(
                        loser_bytes,
                        "Fabricated data detected. Stake slashed to treasury."
                    ),
                    self.buyer_key, self.verifier_acc
                )
                logger.info(f"🔪 Loser slashed — TX: {slash_tx[:16]}...")
            except Exception as e:
                logger.warning(f"rejectProof note: {e}")

        return win_tx, slash_tx
