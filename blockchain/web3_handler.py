"""
blockchain/web3_handler.py
──────────────────────────
Handles blockchain logging via Web3.py + Ganache.
Falls back to a simulated TX hash if Ganache is not running —
so the demo always works regardless of blockchain status.
"""
import hashlib
import json
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Ganache default RPC endpoint
GANACHE_URL = "http://127.0.0.1:7545"

# Pre-compiled contract ABI (matches contract.sol)
CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "string",  "name": "imageHash",  "type": "string"},
            {"internalType": "uint256", "name": "riskScore",  "type": "uint256"},
            {"internalType": "uint256", "name": "timestamp",  "type": "uint256"},
        ],
        "name": "storeTransaction",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "getCount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

# Placeholder — replace with actual deployed contract address when using Ganache
CONTRACT_ADDRESS = "0x0000000000000000000000000000000000000000"

_w3 = None
_contract = None


def _connect():
    """Try to connect to Ganache. Returns (web3, contract) or (None, None)."""
    global _w3, _contract
    if _w3 is not None:
        return _w3, _contract
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(GANACHE_URL, request_kwargs={"timeout": 3}))
        if not w3.is_connected():
            return None, None
        # Use first available account as sender
        account = w3.eth.accounts[0] if w3.eth.accounts else None
        if not account:
            return None, None
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=CONTRACT_ABI,
        )
        _w3 = w3
        _contract = contract
        return w3, contract
    except Exception as e:
        logger.warning(f"Blockchain connection failed: {e}")
        return None, None


def _simulate_tx_hash(image_hash: str, risk_score: int) -> str:
    """Generate a deterministic fake TX hash for demo purposes."""
    raw = f"{image_hash}{risk_score}{time.time_ns()}".encode()
    return "0x" + hashlib.sha256(raw).hexdigest()


def log_to_blockchain(
    image_hash: str,
    risk_score: int,
    timestamp: Optional[int] = None,
) -> dict:
    """
    Attempt to log the fraud record to Ganache blockchain.
    Falls back to simulation if Ganache is unavailable.

    Returns
    -------
    {
        "tx_hash":   str,
        "simulated": bool,   True if Ganache was not available
        "status":    str,    "success" | "simulated" | "error"
    }
    """
    ts = timestamp or int(time.time())
    w3, contract = _connect()

    if w3 and contract:
        try:
            from web3 import Web3
            account = w3.eth.accounts[0]
            tx = contract.functions.storeTransaction(
                image_hash, risk_score, ts
            ).transact({"from": account, "gas": 200_000})
            receipt = w3.eth.wait_for_transaction_receipt(tx, timeout=10)
            return {
                "tx_hash":   receipt.transactionHash.hex(),
                "simulated": False,
                "status":    "success",
                "block":     receipt.blockNumber,
            }
        except Exception as e:
            logger.error(f"On-chain log failed: {e}")

    # Graceful fallback — simulated TX
    return {
        "tx_hash":   _simulate_tx_hash(image_hash, risk_score),
        "simulated": True,
        "status":    "simulated",
        "block":     None,
    }
