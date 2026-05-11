"""
src/signals/whale_tracker.py

Computes the whale migration signal:
a normalized dict of {dex: weight} representing where top-trader
capital is currently deployed across Hyperliquid forks.
"""

import asyncio
import logging
from dataclasses import dataclass

from src.data.hyperliquid import (
    fetch_clearinghouse_batch,
    get_all_dexes,
    get_whale_addresses,
)

logger = logging.getLogger(__name__)


@dataclass
class MigrationSignal:
    weights: dict[str, float]   # {dex_name: allocation_weight}, sums to 1.0
    total_ntl: float            # aggregate notional tracked (USD)
    whale_count: int            # number of wallets contributing


async def compute_migration_signal(
    top_n: int = 50,
    min_ntl_threshold: float = 10_000.0,
) -> MigrationSignal:
    """
    Core signal computation.

    For each registered fork, sums totalNtlPos across the top N whales.
    Returns normalized weights ready for the signal aggregator.

    min_ntl_threshold: ignore positions below this USD size (filters dust).
    """
    addresses = get_whale_addresses(top_n)
    dexes = get_all_dexes()

    logger.info(f"Tracking {len(addresses)} whales across {len(dexes)} dexes: {dexes}")

    exposure: dict[str, float] = {dex: 0.0 for dex in dexes}
    contributing_whales: set[str] = set()

    for dex in dexes:
        results = await fetch_clearinghouse_batch(addresses, dex=dex)
        for addr, result in zip(addresses, results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to fetch {addr} on dex={dex!r}: {result}")
                continue
            try:
                ntl = float(result["marginSummary"]["totalNtlPos"])
                if ntl >= min_ntl_threshold:
                    exposure[dex] += ntl
                    contributing_whales.add(addr)
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Parse error for {addr} on dex={dex!r}: {e}")

    total = sum(exposure.values())
    if total == 0:
        logger.warning("No exposure found — returning equal weights")
        n = len(dexes) or 1
        weights = {dex: 1.0 / n for dex in dexes}
    else:
        weights = {dex: val / total for dex, val in exposure.items()}

    return MigrationSignal(
        weights=weights,
        total_ntl=total,
        whale_count=len(contributing_whales),
    )



def run_migration_signal(**kwargs) -> MigrationSignal:
    """Sync entry point for use outside async contexts."""
    return asyncio.run(compute_migration_signal(**kwargs))

