import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore


@dataclass
class Config:
    rpc_wss: str
    telegram_token: str = ""
    telegram_chat_id: str = ""
    min_liquidity_eth: float = 0.5
    check_honeypot: bool = True
    v2_factories: List[str] = field(default_factory=lambda: [
        "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",  # Uniswap V2
        "0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac",  # SushiSwap
    ])
    v3_factories: List[str] = field(default_factory=lambda: [
        "0x1F98431c8aD98523631AE4a59f267346ea31F984",  # Uniswap V3
    ])
    dry_run: bool = False


def load_config(path: Optional[str] = None) -> Config:
    """Loads config from a TOML file if present, falling back to env vars."""
    cfg_dict = {}

    target_path = Path(path) if path else Path("pairsniper.toml")
    if target_path.exists():
        with open(target_path, "rb") as f:
            data = tomllib.load(f)
            cfg_dict = data.get("pairsniper", data)

    rpc = cfg_dict.get("rpc_wss") or os.getenv("RPC_WSS")
    if not rpc:
        raise ValueError("rpc_wss must be set in config file or RPC_WSS env var")

    tg_token = cfg_dict.get("telegram_token", os.getenv("TELEGRAM_BOT_TOKEN", ""))
    tg_chat = cfg_dict.get("telegram_chat_id", os.getenv("TELEGRAM_CHAT_ID", ""))
    min_liq = float(cfg_dict.get("min_liquidity_eth", os.getenv("MIN_LIQUIDITY_ETH", "0.5")))
    honeypot = cfg_dict.get("check_honeypot", os.getenv("CHECK_HONEYPOT", "true").lower() in ("1", "true", "yes"))

    v2 = cfg_dict.get("v2_factories")
    v3 = cfg_dict.get("v3_factories")

    kwargs = {
        "rpc_wss": rpc,
        "telegram_token": str(tg_token),
        "telegram_chat_id": str(tg_chat),
        "min_liquidity_eth": min_liq,
        "check_honeypot": bool(honeypot),
    }
    if v2 is not None:
        kwargs["v2_factories"] = [addr.lower() for addr in v2]
    if v3 is not None:
        kwargs["v3_factories"] = [addr.lower() for addr in v3]

    return Config(**kwargs)
