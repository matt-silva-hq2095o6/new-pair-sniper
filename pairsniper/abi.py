from dataclasses import dataclass
from typing import Optional

# Uniswap V2 PairCreated(address indexed token0, address indexed token1, address pair, uint)
TOPIC_V2_PAIR_CREATED = "0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9"


@dataclass
class PairCreatedEvent:
    protocol: str
    factory: str
    token0: str
    token1: str
    pair: str
    block_number: int
    tx_hash: str
    extra: dict


def clean_address(raw: str) -> str:
    if raw.startswith("0x"):
        raw = raw[2:]
    return "0x" + raw[-40:].lower()


def decode_v2_pair(log: dict) -> Optional[PairCreatedEvent]:
    topics = log.get("topics", [])
    if not topics or topics[0].lower() != TOPIC_V2_PAIR_CREATED.lower():
        return None

    if len(topics) < 3:
        return None

    token0 = clean_address(topics[1])
    token1 = clean_address(topics[2])

    # data holds address pair (offset 0..32) and uint (offset 32..64)
    data = log.get("data", "")
    if data.startswith("0x"):
        data = data[2:]

    if len(data) < 64:
        return None

    pair = clean_address(data[:64])
    pair_idx = int(data[64:128], 16) if len(data) >= 128 else 0

    blk = int(log.get("blockNumber", "0x0"), 16)
    tx_hash = log.get("transactionHash", "")
    factory = log.get("address", "").lower()

    return PairCreatedEvent(
        protocol="v2",
        factory=factory,
        token0=token0,
        token1=token1,
        pair=pair,
        block_number=blk,
        tx_hash=tx_hash,
        extra={"pair_index": pair_idx},
    )
