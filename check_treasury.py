import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

def run_audit():
    w3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
    mesh_addr = Web3.to_checksum_address(os.getenv("MESHBROKER_ADDRESS").strip("'\" "))
    usdt_addr = Web3.to_checksum_address(os.getenv("USDT_ADDRESS").strip("'\" "))

    mesh_abi = [{"name": "protocolTreasury", "type": "function", "inputs": [{"name": "", "type": "address"}], "outputs": [{"name": "", "type": "uint256"}]}]
    usdt_abi = [{"name": "balanceOf", "type": "function", "inputs": [{"name": "account", "type": "address"}], "outputs": [{"name": "", "type": "uint256"}]}]

    mesh = w3.eth.contract(address=mesh_addr, abi=mesh_abi)
    usdt = w3.eth.contract(address=usdt_addr, abi=usdt_abi)

    print("\n--- ON-CHAIN AUDIT ---")
    print(f"MeshBroker: {mesh_addr}")
    print(f"USDT Token: {usdt_addr}")
    print("-" * 22)
    treasury = mesh.functions.protocolTreasury(usdt_addr).call()
    balance = usdt.functions.balanceOf(mesh_addr).call()
    print(f"Protocol Treasury Mapping: {treasury} units")
    print(f"MeshBroker USDT Balance:   {balance} units")
    print("✅ THE MONEY IS THERE!" if treasury > 0 else "⚖️ Treasury is currently empty.")

if __name__ == "__main__":
    run_audit()
