# ArcMigrant

> A USDC-backed, Arc-native index that auto-rebalances exposure across Hyperliquid forks by tracking where top-trader capital actually migrates — augmented by a cross-lingual signal layer that surfaces Mandarin market intelligence English-only indices miss.

Built for the **Agora Agents Hackathon** — Canteen × Circle on Arc.

---

## What it does

ArcMigrant is an on-chain index token deployed on Arc (Circle's stablecoin-native L1). Users deposit USDC and receive `ARCM` tokens representing proportional exposure to a live, rebalancing portfolio of Hyperliquid fork positions.

Two off-chain signals drive each weekly rebalance:

**1. Whale Migration Signal** — monitors the top 50 Hyperliquid traders by all-time PnL, tracks their `totalNtlPos` across HL mainnet and all registered forks (Aster, Polynomial, etc.) via the public `/info` API, and computes a normalized exposure vector. Where smart money actually trades is where the index allocates.

**2. Translation Alpha Signal** — a TradingAgents-CN-derived agent ingests Mandarin-language crypto news and macro signals (Tushare, Chinese financial feeds) and emits a structured JSON rebalance bias. English-only indices are blind to this flow. ArcMigrant is not.

The aggregated signal is signed by a keeper and delivered to `WhaleIndex.sol` on Arc. Circle Gateway handles cross-chain USDC moves at cent-level fees.

---

## Architecture

```
Hyperliquid API          TradingAgents-CN
     │                        │
     ▼                        ▼
Whale Tracker           Translation Agent
     │                        │
     └──────────┬─────────────┘
                ▼
         Signal Aggregator
         (weighted JSON)
                │
                ▼
        Keeper / Oracle Bridge
                │
                ▼
         WhaleIndex.sol  ──►  Circle Gateway
         (Arc ERC-20)         (cross-chain USDC)
```

Full architecture diagram: [`docs/architecture.md`](docs/architecture.md)

---

## Repo structure

```
ArcMigrant/
├── contracts/
│   ├── WhaleIndex.sol            # ERC-20 index token + USDC vault + rebalance logic
│   └── interfaces/
│       └── ICircleGateway.sol    # Circle Gateway interface stub
├── src/
│   ├── data/
│   │   ├── hyperliquid.py        # HL API client (leaderboard, clearinghouse, fills, perpDexs)
│   │   └── trading_agents_cn.py  # TradingAgents-CN structured output adapter
│   ├── signals/
│   │   ├── whale_tracker.py      # Migration signal computation
│   │   └── aggregator.py         # Weighted signal fusion → rebalance JSON
│   └── keeper/
│       └── keeper.py             # Signs and submits rebalance tx to Arc
├── tests/
│   ├── test_hyperliquid.py
│   └── test_signals.py
├── scripts/
│   └── deploy.py                 # Arc testnet deployment
├── docs/
│   └── architecture.md
├── requirements.txt
└── .env.example
```

---

## Quickstart

```bash
git clone https://github.com/<your-handle>/ArcMigrant.git
cd ArcMigrant
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in Arc RPC, keeper private key
```

Run the signal pipeline locally (no on-chain writes):

```bash
python -m src.signals.aggregator --dry-run
```

Deploy contracts to Arc testnet:

```bash
python scripts/deploy.py --network arc-testnet
```

---

## Tech stack

| Layer | Stack |
|---|---|
| Smart contracts | Solidity 0.8.x, deployed on Arc (HyperEVM-compatible) |
| Off-chain pipeline | Python 3.11, `aiohttp`, `web3.py` |
| Cross-chain settlement | Circle Gateway (USDC) |
| Whale data | Hyperliquid public `/info` API |
| Translation signal | TradingAgents-CN (Tushare + structured JSON outputs) |

---

## Hackathon context

- **Event:** Agora Agents Hackathon — Canteen × Circle on Arc
- **Track:** Trading / Market infrastructure
- **Primary idea:** Hyperliquid Whale Index (Idea 2) + Translation Alpha layer (Idea 4)
- **Chain:** Arc (Circle's stablecoin-native L1)

---

## Status

- [x] Repo scaffolded
- [ ] Hyperliquid API client
- [ ] Whale tracker signal module
- [ ] TradingAgents-CN adapter
- [ ] Signal aggregator
- [ ] `WhaleIndex.sol` draft
- [ ] Arc testnet deployment
- [ ] Keeper bridge
- [ ] Circle Gateway integration
- [ ] Demo + submission writeup

---

## License

MIT
