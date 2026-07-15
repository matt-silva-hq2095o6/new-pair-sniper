import os
from dataclasses import dataclass


@dataclass
class Config:
    rpc_wss: str
    telegram_token: str = ""
    telegram_chat_id: str = ""
    min_liquidity_eth: float = 0.5
    check_honeypot: bool = True
    poll_interval: float = 0.2


def load_config() -> Config:
    rpc = os.getenv("RPC_WSS")
    if not rpc:
        raise ValueError("RPC_WSS environment variable is required")

    return Config(
        rpc_wss=rpc,
        telegram_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        min_liquidity_eth=float(os.getenv("MIN_LIQUIDITY_ETH", "0.5")),
        check_honeypot=os.getenv("CHECK_HONEYPOT", "true").lower() in ("1", "true", "yes"),
    )
