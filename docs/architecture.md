# ArcMigrant — architecture notes

## Data flow

```
[Hyperliquid /info API]          [TradingAgents-CN]
  leaderboard (top 50)             Tushare + Mandarin news
  perpDexs (fork registry)         structured JSON outputs
  clearinghouseState × dex         (Trader / ResearchMgr / PortfolioMgr)
  userFills (recency weight)
         │                                │
         ▼                                ▼
  whale_tracker.py              trading_agents_cn.py
  MigrationSignal                   dict[dex, float]
  {dex: weight}
         │                                │
         └──────────────┬─────────────────┘
                        ▼
                 aggregator.py
                 RebalancePayload
                 {allocations: {dex: weight}, ...}
                        │
                        ▼
                   keeper.py
                   signs Arc tx
                        │
                        ▼
                WhaleIndex.sol (Arc)
                rebalance(allocations)
                        │
                        ▼
                Circle Gateway
                cross-chain USDC moves
```

## Signal weighting

Default blend: 80% whale migration signal, 20% translation alpha.
Configurable via `WHALE_WEIGHT` / `TRANSLATION_WEIGHT` in `aggregator.py`.

The translation alpha weight is intentionally low at launch — it grows as
TradingAgents-CN integration matures and out-of-sample signal quality is validated.

## WhaleIndex.sol design

- ERC-20 token `ARCM`, minted on USDC deposit, burned on withdrawal.
- USDC vault holds all collateral.
- `rebalance(bytes calldata payload)` — keeper-only, updates fork allocations.
- Circle Gateway calls are triggered inside `rebalance()` to move USDC across chains.
- Keeper authorization: single EOA for hackathon; multisig or oracle network post-launch.

## Fork detection logic

Hyperliquid's `clearinghouseState` endpoint accepts an optional `dex` parameter.
`""` = main HL perpetuals. Named strings (e.g. `"Aster"`, `"Polynomial"`) = forks.
The full fork registry is fetched dynamically via `perpDexs` — no hardcoding.

Migration signal = normalized sum of `totalNtlPos` per dex across top-N whales.

## Rate limiting notes

The public `https://api.hyperliquid.xyz/info` endpoint has no published rate limit,
but 50 addresses × N dexes = N×50 concurrent requests. Use `asyncio.gather` with
a semaphore (default: 20 concurrent) and fall back to Quicknode's
`hl_batchClearinghouseStates` if limits are hit.

