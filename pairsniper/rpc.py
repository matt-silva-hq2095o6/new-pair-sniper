import asyncio
import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional
import websockets

logger = logging.getLogger("pairsniper.rpc")


class RpcClient:
    def __init__(self, wss_url: str):
        self.wss_url = wss_url
        self._req_id = 0

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    async def subscribe_logs(self, addresses: List[str], topics: List[str]) -> AsyncIterator[dict]:
        req = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "eth_subscribe",
            "params": ["logs", {"address": addresses, "topics": [topics]}],
        }
        async with websockets.connect(self.wss_url) as ws:
            await ws.send(json.dumps(req))
            resp = json.loads(await ws.recv())
            sub_id = resp.get("result")
            logger.info(f"subscribed to logs, subscription id: {sub_id}")

            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                if data.get("method") == "eth_subscription":
                    params = data.get("params", {})
                    if params.get("subscription") == sub_id:
                        yield params.get("result", {})
