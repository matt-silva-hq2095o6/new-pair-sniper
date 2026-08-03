import pytest
from pairsniper.filter import PairFilter, FilterDecision

WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
SCAM_TOKEN = "0x1111111111111111111111111111111111111111"


@pytest.fixture
def base_filter():
    return PairFilter(
        min_liquidity_usd=5000.0,
        blacklisted_tokens=[SCAM_TOKEN],
        quote_tokens=[WETH, USDC],
    )


def test_blacklist_rejection(base_filter):
    decision, reason = base_filter.check_tokens(SCAM_TOKEN, WETH)
    assert decision == FilterDecision.REJECT
    assert "blacklisted" in reason.lower()

    decision, reason = base_filter.check_tokens(WETH, SCAM_TOKEN)
    assert decision == FilterDecision.REJECT
    assert "blacklisted" in reason.lower()


def test_blacklist_case_insensitive(base_filter):
    # RPC logs might emit lowercased hex while config has checksummed
    mixed_case = "0x1111111111111111111111111111111111111111".upper().replace("0X", "0x")
    decision, reason = base_filter.check_tokens(mixed_case, WETH)
    assert decision == FilterDecision.REJECT


def test_unknown_quote_token(base_filter):
    random_token_a = "0x2222222222222222222222222222222222222222"
    random_token_b = "0x3333333333333333333333333333333333333333"
    
    decision, reason = base_filter.check_tokens(random_token_a, random_token_b)
    assert decision == FilterDecision.REJECT
    assert "no recognized quote token" in reason.lower()


def test_liquidity_threshold(base_filter):
    # 10 ETH reserve at $2500/ETH = $25k liquidity, should pass $5k min
    res = base_filter.eval_liquidity(
        reserve_quote=10.0 * 10**18,
        quote_decimals=18,
        quote_price_usd=2500.0,
    )
    assert res.passed is True
    assert res.estimated_usd == 25000.0

    # 0.5 ETH reserve = $1250 liquidity, below $5k
    res_low = base_filter.eval_liquidity(
        reserve_quote=int(0.5 * 10**18),
        quote_decimals=18,
        quote_price_usd=2500.0,
    )
    assert res_low.passed is False
    assert res_low.estimated_usd == 1250.0


def test_zero_reserve_liquidity(base_filter):
    # freshly deployed pair without initial sync or mint
    res = base_filter.eval_liquidity(
        reserve_quote=0,
        quote_decimals=18,
        quote_price_usd=2500.0,
    )
    # print(f"debug zero reserve: {res}")
    assert res.passed is False
    assert res.estimated_usd == 0.0
