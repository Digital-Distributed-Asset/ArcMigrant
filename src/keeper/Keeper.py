"""
src/keeper/keeper.py

Signs and submits the rebalance transaction to WhaleIndex.sol on Arc Testnet.
Called after the signal aggregator produces a RebalancePayload.

Arc Testnet:
  RPC:      https://rpc.testnet.arc.network
  Chain ID: 5042002
  USDC:     0x3600000000000000000000000000000000000000
"""

import os
import json
import logging
from pathlib import Path
from web3 import Web3
from web3.middleware import SignAndSendRawMiddlewareBuilder
from eth_account import Account
from dotenv import load_dotenv

from src.signals.aggregator import compute_rebalance, RebalancePayload

load_dotenv()
logger = logging.getLogger(__name__)

# ─── Arc Testnet config ──────────────────────────────────────────────────────

ARC_RPC_URL    = os.getenv("ARC_RPC_URL", "https://rpc.testnet.arc.network")
ARC_CHAIN_ID   = int(os.getenv("ARC_CHAIN_ID", "5042002"))
KEEPER_PK      = os.getenv("KEEPER_PRIVATE_KEY")
CONTRACT_ADDR  = os.getenv("WHALE_INDEX_ADDRESS")

# CCTP domain IDs for Hyperliquid forks
# "" = HL mainnet (Arc-native, domain 0 = no cross-chain move needed)
# Update as fork chain IDs and domains become known
DEX_DOMAINS: dict[str, int] = {
    "":           0,    # HL mainnet on Arc — no Gateway transfer
    "Aster":      0,    # placeholder — update when Aster domain is published
    "Polynomial": 0,    # placeholder — update when Polynomial domain is published
}

DEX_VAULTS: dict[str, str] = {
    "":           "0x0000000000000000000000000000000000000000",
    "Aster":      "0x0000000000000000000000000000000000000000",  # TODO
    "Polynomial": "0x0000000000000000000000000000000000000000",  # TODO
}

# ─── WhaleIndex ABI (minimal — only rebalance() needed for the keeper) ───────

WHALE_INDEX_ABI = json.loads("""
[
  {
    "inputs": [
      {"internalType": "bytes32[]", "name": "keys",    "type": "bytes32[]"},
      {"internalType": "uint16[]",  "name": "bps",     "type": "uint16[]"},
      {"internalType": "uint32[]",  "name": "domains", "type": "uint32[]"},
      {"internalType": "address[]", "name": "vaults",  "type": "address[]"}
    ],
    "name": "rebalance",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "vaultBalance",
    "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
    "stateMutability": "view",
    "type": "function"
  }
]
""")


# ─── Encoding helpers ─────────────────────────────────────────────────────────

def encode_dex_key(dex_name: str) -> bytes:
    """keccak256 of the dex name string — mirrors the Solidity bytes32 key."""
    return Web3.keccak(text=dex_name)


def payload_to_contract_args(payload: RebalancePayload) -> tuple:
    """
    Converts RebalancePayload to the four parallel arrays rebalance() expects.
    Allocation floats → basis points (rounded, total enforced to 10000).
    """
    allocs = payload.allocations
    dex_names = list(allocs.keys())

    keys    = [encode_dex_key(d) for d in dex_names]
    domains = [DEX_DOMAINS.get(d, 0) for d in dex_names]
    vaults  = [
        Web3.to_checksum_address(DEX_VAULTS.get(d, "0x" + "0" * 40))
        for d in dex_names
    ]

    # Convert floats to basis points, enforce sum = 10000
    raw_bps = [round(allocs[d] * 10_000) for d in dex_names]
    diff = 10_000 - sum(raw_bps)
    if diff != 0:
        # Adjust the largest allocation to absorb rounding error
        max_idx = raw_bps.index(max(raw_bps))
        raw_bps[max_idx] += diff

    return keys, raw_bps, domains, vaults


# ─── Main keeper function ─────────────────────────────────────────────────────

def run_keeper(dry_run: bool = False) -> str | None:
    """
    Computes the rebalance signal and submits the transaction to Arc.
    Returns the tx hash on success, None if dry_run.
    """
    if not KEEPER_PK:
        raise EnvironmentError("KEEPER_PRIVATE_KEY not set in .env")
    if not CONTRACT_ADDR:
        raise EnvironmentError("WHALE_INDEX_ADDRESS not set in .env")

    # Connect to Arc Testnet
    w3 = Web3(Web3.HTTPProvider(ARC_RPC_URL))
    assert w3.is_connected(), f"Cannot connect to Arc RPC at {ARC_RPC_URL}"
    logger.info(f"Connected to Arc Testnet — chain ID: {w3.eth.chain_id}")

    account = Account.from_key(KEEPER_PK)
    w3.middleware_onion.add(SignAndSendRawMiddlewareBuilder.build(account))
    w3.eth.default_account = account.address

    # Compute signal
    payload = compute_rebalance()
    logger.info(f"Rebalance payload: {payload}")

    if dry_run:
        keys, bps, domains, vaults = payload_to_contract_args(payload)
        logger.info("Dry run — contract args:")
        logger.info(f"  keys:    {[k.hex() for k in keys]}")
        logger.info(f"  bps:     {bps}")
        logger.info(f"  domains: {domains}")
        logger.info(f"  vaults:  {vaults}")
        return None

    # Build and send transaction
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT_ADDR),
        abi=WHALE_INDEX_ABI,
    )

    keys, bps, domains, vaults = payload_to_contract_args(payload)

    tx_hash = contract.functions.rebalance(keys, bps, domains, vaults).transact({
        "chainId": ARC_CHAIN_ID,
        "gas": 500_000,
    })

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    logger.info(f"Rebalance confirmed — tx: {tx_hash.hex()}, block: {receipt.blockNumber}")
    logger.info(f"View on Arc Explorer: https://testnet.arcscan.app/tx/{tx_hash.hex()}")

    return tx_hash.hex()


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run_keeper(dry_run=args.dry_run)

