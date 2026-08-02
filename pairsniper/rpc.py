import asyncio
import json
import logging
import random
from typing import Any, AsyncIterator, Dict, List, Optional
import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger("pairsniper.rpc")


class RpcClient:
    """Manages persistent WebSocket connection with auto-reconnect and eth_call queries."""

    def __init__(self, wss_url: str):
        self.wss_url = wss_url
        self._req_id = 0
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._pending_calls: Dict[int, asyncio.Future] = {}

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    async def eth_call(self, to: str, data: str, block: str = "latest") -> str:
        # TODO: batch calls when checking multiple reserves at once
        req_id = self._next_id()
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "eth_call",
            "params": [{"to": to, "data": data}, block],
        }

        # Fallback to direct one-off if main listener loop isn't active or busy
        async with websockets.connect(self.wss_url, ping_interval=20) as ws:
            await ws.send(json.dumps(payload))
            resp_raw = await ws.recv()
            resp = json.loads(resp_raw)
            if "error" in resp:
                raise RuntimeError(f"eth_call error: {resp['error']}")
            return resp.get("result", "0x")

    async def subscribe_logs(
        self, addresses: List[str], topics: List[str]
    ) -> AsyncIterator[dict]:
        backoff = 1.0
        max_backoff = 30.0

        while True:
            try:
                logger.info(f"connecting to {self.wss_url}...")
                async with websockets.connect(
                    self.wss_url,
                    ping_interval=15,
                    ping_timeout=10,
                    max_size=10_000_000,
                ) as ws:
                    req_id = self._next_id()
                    sub_payload = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "method": "eth_subscribe",
                        "params": ["logs", {"address": addresses, "topics": [topics]}],
                    }
                    await ws.send(json.dumps(sub_payload))
                    init_resp = json.loads(await ws.recv())
                    if "error" in init_resp:
                        logger.error(f"subscription failed: {init_resp['error']}")
                        await asyncio.sleep(backoff)
                        continue

                    sub_id = init_resp.get("result")
                    logger.info(f"active log sub id: {sub_id}")
                    backoff = 1.0  # reset on successful handshake

                    while True:
                        raw = await ws.recv()
                        # print(f"DEBUG raw msg: {raw}")
                        data = json.loads(raw)
                        if data.get("method") == "eth_subscription":
                            res = data.get("params", {}).get("result")
                            if res:
                                yield res

            except (ConnectionClosed, OSError, asyncio.TimeoutError) as err:
                jitter = random.uniform(0.1, 0.5)
                sleep_time = min(backoff + jitter, max_backoff)
                logger.warning(f"ws disconnected ({err}), retrying in {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
                backoff = min(backoff * 2, max_backoff)
            except Exception:
                logger.exception("unexpected rpc crash, backing off")
                await asyncio.sleep(backoff)
