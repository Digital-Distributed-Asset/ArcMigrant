"""
scripts/deploy.py

Deploys WhaleIndex.sol to Arc Testnet.

Prerequisites:
  1. Arc Testnet wallet set up (MetaMask or any EVM wallet)
  2. Testnet USDC in the wallet from https://faucet.circle.com
  3. .env populated with ARC_RPC_URL, KEEPER_PRIVATE_KEY

Arc Testnet:
  RPC:      https://rpc.testnet.arc.network
  Chain ID: 5042002
  USDC:     0x3600000000000000000000000000000000000000
  Explorer: https://testnet.arcscan.app
  Faucet:   https://faucet.circle.com  (select Arc Testnet)

Usage:
  python scripts/deploy.py
  python scripts/deploy.py --dry-run    # validates config without deploying
"""

import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─── Arc Testnet constants ────────────────────────────────────────────────────

ARC_RPC_URL  = os.getenv("ARC_RPC_URL", "https://rpc.testnet.arc.network")
ARC_CHAIN_ID = int(os.getenv("ARC_CHAIN_ID", "5042002"))
USDC_ADDRESS = "0x3600000000000000000000000000000000000000"

# Circle Gateway on Arc Testnet.
# Check https://docs.arc.network/arc/references/contract-addresses for the
# current live address — update here and in .env before deploying.
GATEWAY_ADDRESS = os.getenv("GATEWAY_ADDRESS", "0x0000000000000000000000000000000000000000")

KEEPER_PK = os.getenv("KEEPER_PRIVATE_KEY")


# ─── WhaleIndex compiled bytecode + ABI ──────────────────────────────────────
#
# Two options:
#
# Option 1 (recommended for hackathon speed): Deploy via Remix IDE.
#   - Paste contracts/WhaleIndex.sol into https://remix.ethereum.org
#   - Compile with Solidity 0.8.20
#   - Deploy with Injected Provider (MetaMask on Arc Testnet)
#   - Copy the deployed address into .env as WHALE_INDEX_ADDRESS
#   - Run keeper.py — no need for this script at all
#
# Option 2 (this script): compile locally with solc or Foundry and paste
#   the output ABI + bytecode below, then run this script.
#
# The ABI and bytecode placeholders below are filled after local compilation.
# See README in contracts/ for Foundry compile command.

WHALE_INDEX_ABI = json.loads("""
[
  {
    "inputs": [
      {"internalType": "address", "name": "_usdc",    "type": "address"},
      {"internalType": "address", "name": "_gateway", "type": "address"},
      {"internalType": "address", "name": "_keeper",  "type": "address"}
    ],
    "stateMutability": "nonpayable",
    "type": "constructor"
  },
  {
    "inputs": [{"internalType": "uint256", "name": "usdcAmount", "type": "uint256"}],
    "name": "deposit",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [{"internalType": "uint256", "name": "arcmAmount", "type": "uint256"}],
    "name": "withdraw",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
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
  },
  {
    "inputs": [],
    "name": "totalSupply",
    "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [{"internalType": "address", "name": "", "type": "address"}],
    "name": "balanceOf",
    "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [{"internalType": "address", "name": "newKeeper", "type": "address"}],
    "name": "setKeeper",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  }
]
""")

# Paste compiled bytecode here after running:
#   forge build
#   cat out/WhaleIndex.sol/WhaleIndex.json | python -c "import json,sys; print(json.load(sys.stdin)['bytecode']['object'])"
WHALE_INDEX_BYTECODE = os.getenv("WHALE_INDEX_BYTECODE", "")


# ─── Deployment ───────────────────────────────────────────────────────────────

def validate_config() -> bool:
    """Checks all required config is present before attempting deployment."""
    ok = True

    if not KEEPER_PK:
        logger.error("KEEPER_PRIVATE_KEY not set in .env")
        ok = False

    if GATEWAY_ADDRESS == "0x0000000000000000000000000000000000000000":
        logger.warning(
            "GATEWAY_ADDRESS is still the zero address placeholder.\n"
            "  → Check https://docs.arc.network/arc/references/contract-addresses\n"
            "  → Set GATEWAY_ADDRESS in .env before deploying"
        )
        # Warning only — not a blocking error for testnet

    if not WHALE_INDEX_BYTECODE:
        logger.warning(
            "WHALE_INDEX_BYTECODE not set.\n"
            "  → Compile WhaleIndex.sol first (see contracts/README.md)\n"
            "  → Or use Remix IDE as the faster alternative (Option 1 above)"
        )
        ok = False

    return ok


def deploy(dry_run: bool = False) -> str | None:
    """
    Deploys WhaleIndex to Arc Testnet.
    Returns the deployed contract address on success.
    """
    logger.info("─── ArcMigrant deployment script ───")
    logger.info(f"  RPC:      {ARC_RPC_URL}")
    logger.info(f"  Chain ID: {ARC_CHAIN_ID}")
    logger.info(f"  USDC:     {USDC_ADDRESS}")
    logger.info(f"  Gateway:  {GATEWAY_ADDRESS}")

    if not validate_config():
        logger.error("Config validation failed — fix the errors above before deploying.")
        return None

    if dry_run:
        logger.info("Dry run — config looks good. Run without --dry-run to deploy.")
        return None

    # Connect
    w3 = Web3(Web3.HTTPProvider(ARC_RPC_URL))
    if not w3.is_connected():
        logger.error(f"Cannot connect to Arc RPC at {ARC_RPC_URL}")
        return None
    logger.info(f"Connected — latest block: {w3.eth.block_number}")

    account = Account.from_key(KEEPER_PK)
    logger.info(f"Deployer: {account.address}")
    logger.info(f"Balance:  {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} ETH")

    # Build deploy transaction
    contract = w3.eth.contract(abi=WHALE_INDEX_ABI, bytecode=WHALE_INDEX_BYTECODE)

    keeper_address = account.address  # keeper = deployer for hackathon

    tx = contract.constructor(
        Web3.to_checksum_address(USDC_ADDRESS),
        Web3.to_checksum_address(GATEWAY_ADDRESS),
        Web3.to_checksum_address(keeper_address),
    ).build_transaction({
        "from":     account.address,
        "chainId":  ARC_CHAIN_ID,
        "gas":      2_000_000,
        "gasPrice": w3.eth.gas_price,
        "nonce":    w3.eth.get_transaction_count(account.address),
    })

    # Sign and send
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    logger.info(f"Tx sent: {tx_hash.hex()}")
    logger.info("Waiting for confirmation...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    contract_address = receipt.contractAddress

    logger.info(f"✓ WhaleIndex deployed at: {contract_address}")
    logger.info(f"  Block:    {receipt.blockNumber}")
    logger.info(f"  Gas used: {receipt.gasUsed}")
    logger.info(f"  Explorer: https://testnet.arcscan.app/address/{contract_address}")
    logger.info("")
    logger.info("Next step: add to .env →")
    logger.info(f"  WHALE_INDEX_ADDRESS={contract_address}")

    # Write address to .env automatically
    _update_env("WHALE_INDEX_ADDRESS", contract_address)

    return contract_address


def _update_env(key: str, value: str):
    """Appends or updates a key in .env file."""
    env_path = Path(".env")
    if not env_path.exists():
        env_path.write_text(f"{key}={value}\n")
        return

    lines = env_path.read_text().splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}")

    env_path.write_text("\n".join(lines) + "\n")
    logger.info(f".env updated with {key}")


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Deploy WhaleIndex to Arc Testnet")
    parser.add_argument("--dry-run", action="store_true", help="Validate config only")
    args = parser.parse_args()

    deploy(dry_run=args.dry_run)

