"""
src/signals/aggregator.py

Fuses the whale migration signal and the translation alpha signal
into a single rebalance JSON consumed by the keeper.

Weights are configurable. Default: 80% whale migration, 20% translation alpha.
"""

import json
import logging
from dataclasses import asdict, dataclass

from src.signals.whale_tracker import MigrationSignal, run_migration_signal

logger = logging.getLogger(__name__)

WHALE_WEIGHT = 0.80
TRANSLATION_WEIGHT = 0.20


@dataclass
class RebalancePayload:
    allocations: dict[str, float]   # {dex: weight}, sums to 1.0
    whale_ntl: float
    whale_count: int
    translation_active: bool
    version: int = 1


def _get_translation_signal() -> dict[str, float]:
    """
    Stub: returns equal-weight allocation across all dexes.
    Replace with TradingAgents-CN adapter output once integrated.
    See: src/data/trading_agents_cn.py
    """
    logger.info("Translation signal: using stub (equal weight)")
    return {}


def _blend(
    whale: dict[str, float],
    translation: dict[str, float],
    w_whale: float = WHALE_WEIGHT,
    w_trans: float = TRANSLATION_WEIGHT,
) -> dict[str, float]:
    """
    Weighted blend of two allocation dicts.
    If translation signal is empty, full weight goes to whale signal.
    """
    all_dexes = set(whale.keys()) | set(translation.keys())
    if not translation:
        return whale

    blended = {}
    for dex in all_dexes:
        w = whale.get(dex, 0.0) * w_whale
        t = translation.get(dex, 0.0) * w_trans
        blended[dex] = w + t

    total = sum(blended.values()) or 1.0
    return {dex: val / total for dex, val in blended.items()}


def compute_rebalance(
    top_n: int = 50,
    dry_run: bool = False,
) -> RebalancePayload:
    """
    Main entry point. Returns the full rebalance payload.
    If dry_run=True, prints the JSON and exits without submitting.
    """
    migration = run_migration_signal(top_n=top_n)
    translation = _get_translation_signal()

    allocations = _blend(migration.weights, translation)

    payload = RebalancePayload(
        allocations=allocations,
        whale_ntl=migration.total_ntl,
        whale_count=migration.whale_count,
        translation_active=bool(translation),
    )

    if dry_run:
        print(json.dumps(asdict(payload), indent=2))

    return payload


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--top-n", type=int, default=50)
    args = parser.parse_args()

    compute_rebalance(top_n=args.top_n, dry_run=args.dry_run)

