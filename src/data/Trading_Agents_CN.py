"""
src/data/trading_agents_cn.py

Adapter for TradingAgents-CN structured outputs.
Translates Mandarin-language market signals into a fork allocation bias.

References:
- https://arxiv.org/abs/2412.20138 (TradingAgents, Wang et al. 2025)
- https://github.com/hsliuping/TradingAgents-CN
  (adds Tushare for A-share fundamentals + Chinese news feeds)

Integration plan:
1. Run TradingAgents-CN locally or via subprocess with a crypto-focused prompt.
2. Parse the structured JSON output (Trader / Research Manager / Portfolio Manager blocks).
3. Map the portfolio recommendation to a dex allocation bias vector.

Status: stub — returns empty dict until TradingAgents-CN is wired up.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def fetch_translation_signal(dex_universe: list[str]) -> dict[str, float]:
    """
    Returns a dex allocation bias from TradingAgents-CN structured output.
    Keys are dex names from the HL perpDexs registry.
    Values are bias weights (will be normalized by the aggregator).

    Until TradingAgents-CN is integrated, returns empty dict
    so the aggregator falls back to 100% whale signal.
    """
    logger.info("TradingAgents-CN adapter: stub active, returning empty signal")
    return {}


def parse_trading_agents_output(raw_output: dict[str, Any]) -> dict[str, float]:
    """
    Parses TradingAgents-CN JSON reasoning blocks into a dex bias vector.

    Expected input structure (from TradingAgents v0.2.4 structured outputs):
    {
      "trader": { "action": "BUY" | "SELL" | "HOLD", "reasoning": "..." },
      "research_manager": { "sentiment": float, "key_signals": [...] },
      "portfolio_manager": { "allocation": {...} }
    }

    TODO: implement once TradingAgents-CN subprocess is wired.
    """
    raise NotImplementedError("TradingAgents-CN parsing not yet implemented")

