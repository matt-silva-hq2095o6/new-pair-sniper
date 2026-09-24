# pairsniper

CLI tool to tail EVM Uniswap-v2 and v3 factory logs over raw WebSockets, decode PairCreated/PoolCreated events on the fly, and filter out low liquidity garbage or honeypots before dispatching alerts.

Built because web3.py overhead was dropping frames on busy blocks during burst periods on Base and Arbitrum.

## Install

Requires Python 3.11+.

```bash
git clone https://github.com/aevans/pairsniper.git
cd pairsniper
pip install -e .
```

## Usage

Run against Ethereum mainnet or L2s:

```bash
pairsniper --rpc-ws wss://base-mainnet.g.alchemy.com/v2/KEY --min-liquidity-usd 2500
```

Flags:
- `--rpc-ws`: WebSocket RPC endpoint (or `RPC_WS_URL` env var)
- `--rpc-http`: Optional HTTP RPC endpoint for fallback state queries
- `--chain`: Preset network config (`ethereum`, `base`, `arbitrum`, `bsc`)
- `--v3`: Also listen for Uniswap v3 / Pancake v3 PoolCreated logs
- `--min-liquidity-usd`: Minimum pooled WETH/USDC before firing webhook (default: 0)
- `--honeypot-check`: Run bytecode and simulate buy/sell tax before alert
- `--webhook-url`: Discord or Telegram webhook for alerts

## Config File

You can also drop a `config.json` in the current working directory:

```json
{
  "rpc_ws_url": "wss://base-mainnet.g.alchemy.com/v2/xyz",
  "chain": "base",
  "watch_v2": true,
  "watch_v3": true,
  "min_liquidity_usd": 1000,
  "telegram_bot_token": "...",
  "telegram_chat_id": "..."
}
```

<!-- last-sync: 2026-09-24 -->
