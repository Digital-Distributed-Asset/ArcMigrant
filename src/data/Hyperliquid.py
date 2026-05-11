"""
src/data/hyperliquid.py

Hyperliquid public /info API client.
Covers: leaderboard, perpDexs, clearinghouseState, userFills.
All heavy calls use aiohttp for async batching.
"""

import asyncio
from typing import Any

import aiohttp
import requests

INFO_URL = "https://api.hyperliquid.xyz/info"
LEADERBOARD_URL = "https://stats-data.hyperliquid.xyz/Mainnet/leaderboard"


# ---------------------------------------------------------------------------
# Sync helpers (low-frequency, setup calls)
# ---------------------------------------------------------------------------

def fetch_leaderboard(top_n: int = 50) -> list[dict]:
    """
    Returns the top N traders from the HL leaderboard, ranked by all-time PnL.
    Each entry: {ethAddress, accountValue, windowPnl: {allTime, ...}, vlm}
    """
    resp = requests.get(LEADERBOARD_URL, timeout=10)
    resp.raise_for_status()
    rows = resp.json().get("leaderboardRows", [])
    return rows[:top_n]


def fetch_perp_dexs() -> list[str]:
    """
    Returns registered perp DEX names on Hyperliquid.
    "" = main HL, "Aster", "Polynomial", etc. = forks.
    """
    resp = requests.post(INFO_URL, json={"type": "perpDexs"}, timeout=10)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Async helpers (high-frequency, per-whale calls)
# ---------------------------------------------------------------------------

async def _post(session: aiohttp.ClientSession, payload: dict) -> Any:
    async with session.post(INFO_URL, json=payload) as resp:
        resp.raise_for_status()
        return await resp.json()


async def fetch_clearinghouse_batch(
    addresses: list[str],
    dex: str = "",
) -> list[dict]:
    """
    Fetches clearinghouseState for a list of addresses on a given dex.
    Returns list of raw API responses in the same order as addresses.
    """
    async with aiohttp.ClientSession() as session:
        tasks = [
            _post(session, {"type": "clearinghouseState", "user": addr, "dex": dex})
            for addr in addresses
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)


async def fetch_fills_batch(addresses: list[str]) -> list[list[dict]]:
    """
    Fetches recent userFills for a list of addresses.
    Returns list of fill arrays in the same order as addresses.
    """
    async with aiohttp.ClientSession() as session:
        tasks = [
            _post(session, {"type": "userFills", "user": addr})
            for addr in addresses
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)


# ---------------------------------------------------------------------------
# Convenience wrappers
# ---------------------------------------------------------------------------

def get_whale_addresses(top_n: int = 50) -> list[str]:
    rows = fetch_leaderboard(top_n)
    return [r["ethAddress"] for r in rows]


def get_all_dexes() -> list[str]:
    return fetch_perp_dexs()
