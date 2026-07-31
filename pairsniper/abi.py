from dataclasses import dataclass
from typing import Optional

# Uniswap V2: PairCreated(address indexed token0, address indexed token1, address pair, uint)
TOPIC_V2_PAIR_CREATED = "0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9"

# Uniswap V3: PoolCreated(address indexed token0, address indexed token1, uint24 indexed fee, int24 tickSpacing, address pool)
TOPIC_V3_POOL_CREATED = "0x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e0653d4994ea033e2"


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


def _decode_int24(hex_str: str) -> int:
    val = int(hex_str, 16)
    # sign extend 24-bit integer
    if val >= 0x800000:
        val -= 0x1000000
    return val


def decode_log(log: dict) -> Optional[PairCreatedEvent]:
    topics = log.get("topics", [])
    if not topics:
        return None

    t0 = topics[0].lower()
    blk = int(log.get("blockNumber", "0x0"), 16)
    tx = log.get("transactionHash", "")
    factory = log.get("address", "").lower()
    data = log.get("data", "")
    if data.startswith("0x"):
        data = data[2:]

    if t0 == TOPIC_V2_PAIR_CREATED.lower():
        if len(topics) < 3 or len(data) < 64:
            return None
        token0 = clean_address(topics[1])
        token1 = clean_address(topics[2])
        pair = clean_address(data[:64])
        pair_idx = int(data[64:128], 16) if len(data) >= 128 else 0
        return PairCreatedEvent(
            protocol="v2",
            factory=factory,
            token0=token0,
            token1=token1,
            pair=pair,
            block_number=blk,
            tx_hash=tx,
            extra={"pair_index": pair_idx},
        )

    elif t0 == TOPIC_V3_POOL_CREATED.lower():
        # v3 has token0, token1, fee as indexed topics
        if len(topics) < 4 or len(data) < 64:
            return None
        token0 = clean_address(topics[1])
        token1 = clean_address(topics[2])
        fee = int(topics[3], 16)
        
        # data has tickSpacing (int24 padded to 32 bytes) then pool (address padded to 32 bytes)
        raw_tick = data[:64]
        raw_pool = data[64:128] if len(data) >= 128 else data[:64]
        
        tick_spacing = _decode_int24(raw_tick[-6:])
        pool = clean_address(raw_pool)

        return PairCreatedEvent(
            protocol="v3",
            factory=factory,
            token0=token0,
            token1=token1,
            pair=pool,
            block_number=blk,
            tx_hash=tx,
            extra={"fee": fee, "tick_spacing": tick_spacing},
        )

    return None
