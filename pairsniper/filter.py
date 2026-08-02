from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Any, Optional
import logging
from pairsniper.rpc import WsRpcClient
from pairsniper.abi import (
    ERC20_GET_RESERVES,
    ERC20_DECIMALS,
    ERC20_SYMBOL,
    ERC20_NAME,
    WETH_BY_CHAIN,
    STABLECOINS_BY_CHAIN,
    encode_call,
    decode_uint,
    decode_string,
)

logger = logging.getLogger("pairsniper.filter")

# common signatures embedded inside malicious proxies or fee tokens
SUSPICIOUS_SELECTORS = (
    "0x42966c68",  # burn(uint256)
    "0x095ea7b3",  # standard approve, checked to make sure it's not missing
)


@dataclass
class EvaluationResult:
    passed: bool
    reason: str = ""
    token_address: str = ""
    token_symbol: str = ""
    token_name: str = ""
    quote_address: str = ""
    quote_symbol: str = ""
    initial_liquidity_eth: Decimal = Decimal(0)
    has_bytecode_risk: bool = False


class PairFilter:
    """Validates liquidity pair tokens against metadata requirements and basic trap heuristics."""

    def __init__(self, config: Dict[str, Any], rpc: WsRpcClient):
        self.config = config
        self.rpc = rpc
        self.chain_id = config.get("chain_id", 1)
        self.min_eth = Decimal(str(config.get("min_liquidity_eth", "1.0")))
        self.check_honeypots = config.get("check_honeypot", True)
        self.weth_address = WETH_BY_CHAIN.get(self.chain_id, "").lower()
        self.known_stables = {
            addr.lower() for addr in STABLECOINS_BY_CHAIN.get(self.chain_id, [])
        }

    async def evaluate(self, pair: Dict[str, Any]) -> EvaluationResult:
        token0 = pair.get("token0", "").lower()
        token1 = pair.get("token1", "").lower()
        pair_addr = pair.get("pair_address", "").lower()
        version = pair.get("version", "v2")

        if token0 == self.weth_address or token0 in self.known_stables:
            quote_token, target_token = token0, token1
            target_is_token1 = True
        elif token1 == self.weth_address or token1 in self.known_stables:
            quote_token, target_token = token1, token0
            target_is_token1 = False
        else:
            return EvaluationResult(passed=False, reason="neither token is WETH or allowed stable")

        # verify token bytecode exists (some tokens selfdestruct in constructor)
        bytecode = await self.rpc.get_code(target_token)
        if not bytecode or bytecode in ("0x", "0x0"):
            return EvaluationResult(passed=False, reason="token contract has empty bytecode")

        bytecode_lower = bytecode.lower()
        # selfdestruct opcode is 0xff; flag pairs that explicitly embed destruction
        has_selfdestruct = "ff" in bytecode_lower

        if self.check_honeypots and has_selfdestruct:
            # some legacy tokens have ff as data, but it's high risk for brand new deployments
            logger.debug("flagging target %s for selfdestruct byte", target_token)

        target_sym = await self._fetch_string(target_token, ERC20_SYMBOL, "UNKNOWN")
        target_name = await self._fetch_string(target_token, ERC20_NAME, "Unknown Token")

        liq_eth = Decimal(0)
        if version == "v2":
            call_data = encode_call(ERC20_GET_RESERVES)
            raw_reserves = await self.rpc.eth_call(pair_addr, call_data)
            if raw_reserves and raw_reserves != "0x" and len(raw_reserves) >= 130:
                r0 = decode_uint(raw_reserves[:66])
                r1 = decode_uint("0x" + raw_reserves[66:130])
                quote_reserve = r0 if not target_is_token1 else r1
                # assume 18 decimals on quote token for standard WETH pairs
                liq_eth = Decimal(quote_reserve) / Decimal(10**18)

            if liq_eth < self.min_eth:
                return EvaluationResult(
                    passed=False,
                    reason=f"low liquidity ({liq_eth:.2f} < {self.min_eth} ETH)",
                    token_address=target_token,
                    token_symbol=target_sym,
                    initial_liquidity_eth=liq_eth,
                )

        return EvaluationResult(
            passed=True,
            token_address=target_token,
            token_symbol=target_sym,
            token_name=target_name,
            quote_address=quote_token,
            initial_liquidity_eth=liq_eth,
            has_bytecode_risk=has_selfdestruct,
        )

    async def _fetch_string(self, contract: str, method_sig: str, default: str) -> str:
        try:
            data = encode_call(method_sig)
            out = await self.rpc.eth_call(contract, data)
            if not out or out == "0x":
                return default
            return decode_string(out)
        except Exception:
            return default
