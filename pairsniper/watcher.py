import asyncio
import logging
from typing import Dict, Any, Optional
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
        self.factory_addresses = [
            addr.lower() for addr in config.get("factories", {}).values() if addr
        ]

    async def start(self) -> None:
        self._running = True
        logger.info("starting factory watcher for %d addresses", len(self.factory_addresses))

        topics = [[PAIR_CREATED_TOPIC, POOL_CREATED_TOPIC]]
        sub_params = {"address": self.factory_addresses, "topics": topics}

        subscription_id = await self.rpc.subscribe("logs", sub_params)
        logger.info("subscribed to logs with id: %s", subscription_id)

        while self._running:
            try:
                msg = await self.rpc.recv()
                if not msg or "params" not in msg:
                    continue

                log_data = msg["params"].get("result")
                if not log_data:
                    continue

                # print("raw log:", log_data)
                asyncio.create_task(self._process_log(log_data))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("error reading from ws: %s", e)
                await asyncio.sleep(1)

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
            logger.debug("failed to decode log %s: %s", log.get("transactionHash"), err)
            return

        if not pair_data:
            return

        pair_data["blockNumber"] = int(log.get("blockNumber", "0x0"), 16)
        pair_data["txHash"] = log.get("transactionHash", "")

        res = await self.filter.evaluate(pair_data)
        if res.passed:
            logger.info("pair %s passed checks, sending alert", pair_data.get("pair_address"))
            await dispatch_notification(self.config, pair_data, res)
        else:
            logger.debug("rejected pair %s: %s", pair_data.get("pair_address"), res.reason)

    def stop(self) -> None:
        self._running = False
