import asyncio
import logging
from typing import Dict, Any, Optional, Set
from pairsniper.rpc import WsRpcClient
from pairsniper.abi import (
    PAIR_CREATED_TOPIC,
    POOL_CREATED_TOPIC,
    decode_pair_created_event,
    decode_pool_created_event,
)
from pairsniper.filter import PairFilter
from pairsniper.notifier import dispatch_notification

logger = logging.getLogger("pairsniper.watcher")


class FactoryWatcher:
    """Subscribes to factory logs over WebSockets and coordinates evaluation."""

    def __init__(self, config: Dict[str, Any], rpc: WsRpcClient, pair_filter: PairFilter):
        self.config = config
        self.rpc = rpc
        self.filter = pair_filter
        self._running = False
        self._seen_txs: Set[str] = set()
        self._max_cache = 2000
        self.factory_addresses = [
            addr.lower() for addr in config.get("factories", {}).values() if addr
        ]

    async def start(self) -> None:
        self._running = True
        backoff = 1

        while self._running:
            try:
                await self._run_subscription_loop()
                backoff = 1
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("ws connection dropped: %s, reconnecting in %ds", e, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)

    async def _run_subscription_loop(self) -> None:
        topics = [[PAIR_CREATED_TOPIC, POOL_CREATED_TOPIC]]
        sub_params = {"address": self.factory_addresses, "topics": topics}

        subscription_id = await self.rpc.subscribe("logs", sub_params)
        logger.info("listening for factory events (sub: %s)", subscription_id)

        while self._running:
            msg = await self.rpc.recv()
            if not msg:
                continue

            # standard eth subscription wrapper
            if msg.get("method") != "eth_subscription":
                continue

            params = msg.get("params", {})
            log_data = params.get("result")
            if not log_data:
                continue

            # FIXME: if node reorganizes blocks we might drop valid re-emitted pairs
            tx_hash = log_data.get("transactionHash", "")
            if tx_hash in self._seen_txs:
                continue
            self._remember_tx(tx_hash)

            asyncio.create_task(self._process_log(log_data))

    def _remember_tx(self, tx_hash: str) -> None:
        if not tx_hash:
            return
        if len(self._seen_txs) >= self._max_cache:
            # trim oldest items roughly
            self._seen_txs.clear()
        self._seen_txs.add(tx_hash)

    async def _process_log(self, log: Dict[str, Any]) -> None:
        topics = log.get("topics", [])
        if not topics:
            return

        event_sig = topics[0].lower()
        pair_data: Optional[Dict[str, Any]] = None

        try:
            if event_sig == PAIR_CREATED_TOPIC.lower():
                pair_data = decode_pair_created_event(log)
                pair_data["version"] = "v2"
            elif event_sig == POOL_CREATED_TOPIC.lower():
                pair_data = decode_pool_created_event(log)
                pair_data["version"] = "v3"
            else:
                return
        except Exception as err:
            logger.debug("decode failure on tx %s: %s", log.get("transactionHash"), err)
            return

        if not pair_data:
            return

        pair_data["blockNumber"] = int(log.get("blockNumber", "0x0"), 16)
        pair_data["txHash"] = log.get("transactionHash", "")

        res = await self.filter.evaluate(pair_data)
        if res.passed:
            logger.info("new pair passed: %s (symbol: %s)", pair_data.get("pair_address"), res.token_symbol)
            await dispatch_notification(self.config, pair_data, res)
        else:
            logger.debug("filtered out %s: %s", pair_data.get("pair_address"), res.reason)

    def stop(self) -> None:
        self._running = False
