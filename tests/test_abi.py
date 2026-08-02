import pytest
from pairsniper.abi import keccak256, decode_pair_created_v2, decode_pool_created_v3


def test_keccak_hash():
    sig_v2 = "PairCreated(address,address,address,uint256)"
    assert keccak256(sig_v2.encode()).hex() == "0d3648de0fa6cb26621b183b36a929700a4427e080a736449dc33810f43ab6b6"

    sig_v3 = "PoolCreated(address,address,uint24,int24,address)"
    assert keccak256(sig_v3.encode()).hex() == "783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118"


def test_decode_pair_created_v2_valid():
    topic0 = "0x0d3648de0fa6cb26621b183b36a929700a4427e080a736449dc33810f43ab6b6"
    topic1 = "0x000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
    topic2 = "0x000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
    topics = [topic0, topic1, topic2]

    # 32 bytes pair address + 32 bytes pair length (1)
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
    topics = ["0x0d3648de0fa6cb26621b183b36a929700a4427e080a736449dc33810f43ab6b6"]
    data = "0x00"
    assert decode_pair_created_v2(topics, data) is None


def test_decode_pool_created_v3_valid():
    # PoolCreated(token0 indexed, token1 indexed, fee indexed, int24 tickSpacing, address pool)
    t0 = "0x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118"
    t1 = "0x000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
    t2 = "0x000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
    t3 = "0x00000000000000000000000000000000000000000000000000000000000001f4"  # 500 (0.05%)
    topics = [t0, t1, t2, t3]

    # tickSpacing: 10, pool: 0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640
    data = (
        "0x000000000000000000000000000000000000000000000000000000000000000a"
        "00000000000000000000000088e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
    )

    res = decode_pool_created_v3(topics, data)
    assert res is not None
    assert res["token0"].lower() == "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
    assert res["token1"].lower() == "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
    assert res["fee"] == 500
    assert res["tick_spacing"] == 10
    assert res["pool"].lower() == "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
