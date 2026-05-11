"""
tests/test_hyperliquid.py

Basic smoke tests for the Hyperliquid API client.
Run with: pytest tests/test_hyperliquid.py -v
"""

import pytest
from unittest.mock import patch, MagicMock

from src.data.hyperliquid import (
    fetch_leaderboard,
    fetch_perp_dexs,
    get_whale_addresses,
)

MOCK_LEADERBOARD = {
    "leaderboardRows": [
        {"ethAddress": f"0x{'a' * 40}", "accountValue": "1000000", "windowPnl": {"allTime": "500000"}, "vlm": "10000000"},
        {"ethAddress": f"0x{'b' * 40}", "accountValue": "800000",  "windowPnl": {"allTime": "400000"}, "vlm": "8000000"},
    ]
}

MOCK_PERP_DEXS = ["", "Aster", "Polynomial"]


@patch("src.data.hyperliquid.requests.get")
def test_fetch_leaderboard_returns_top_n(mock_get):
    mock_get.return_value = MagicMock(status_code=200)
    mock_get.return_value.json.return_value = MOCK_LEADERBOARD
    result = fetch_leaderboard(top_n=1)
    assert len(result) == 1
    assert result[0]["ethAddress"] == f"0x{'a' * 40}"


@patch("src.data.hyperliquid.requests.post")
def test_fetch_perp_dexs(mock_post):
    mock_post.return_value = MagicMock(status_code=200)
    mock_post.return_value.json.return_value = MOCK_PERP_DEXS
    result = fetch_perp_dexs()
    assert "" in result
    assert "Aster" in result


@patch("src.data.hyperliquid.requests.get")
def test_get_whale_addresses(mock_get):
    mock_get.return_value = MagicMock(status_code=200)
    mock_get.return_value.json.return_value = MOCK_LEADERBOARD
    addresses = get_whale_addresses(top_n=2)
    assert len(addresses) == 2
    assert all(addr.startswith("0x") for addr in addresses)

