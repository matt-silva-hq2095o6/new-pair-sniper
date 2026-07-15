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

## Quickstart

Run against an active WS node:

```bash
pairsniper --rpc-ws wss://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
```

Or pass options via environment:

```bash
export RPC_WS_URL="wss://base-mainnet.g.alchemy.com/v2/YOUR_KEY"
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
export TELEGRAM_CHAT_ID="-100..."
pairsniper
```
