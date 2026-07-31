import pytest
from pairsniper.abi import keccak256, decode_pair_created_v2


def test_keccak_hash():
    # Uniswap V2 PairCreated signature
    sig = "PairCreated(address,address,address,uint256)"
    topic = keccak256(sig.encode())
    assert topic.hex() == "0d3648de0fa6cb26621b183b36a929700a4427e080a736449dc33810f43ab6b6"


def test_decode_pair_created_v2_valid():
    # Topic 0: Event hash
    # Topic 1: token0 (indexed)
    # Topic 2: token1 (indexed)
    # Data: pair address (32 bytes padded) + pair length/index (32 bytes padded)
    topic0 = "0x0d3648de0fa6cb26621b183b36a929700a4427e080a736449dc33810f43ab6b6"
    topic1 = "0x000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
    topic2 = "0x000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
    topics = [topic0, topic1, topic2]

    # Pair address: 0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc, length = 1
    data = (
        "0x000000000000000000000000b4e16d0168e52d35cacd2c6185b44281ec28c9dc"
        "0000000000000000000000000000000000000000000000000000000000000001"
    )

    res = decode_pair_created_v2(topics, data)
    assert res is not None
    assert res["token0"].lower() == "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
    assert res["token1"].lower() == "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
    assert res["pair"].lower() == "0xb4e16d0168e52d35cacd2c6185b44281ec28c9dc"
    assert res["pair_index"] == 1


def test_decode_pair_created_v2_malformed():
    # Missing indexed topic
    topics = ["0x0d3648de0fa6cb26621b183b36a929700a4427e080a736449dc33810f43ab6b6"]
    data = "0x00"
    assert decode_pair_created_v2(topics, data) is None
