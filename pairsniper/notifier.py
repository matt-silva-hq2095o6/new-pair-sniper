import logging
import httpx
from typing import Optional, Dict, Any

log = logging.getLogger("pairsniper.notifier")


class Notifier:
    def __init__(self, discord_url: Optional[str] = None, tg_token: Optional[str] = None, tg_chat_id: Optional[str] = None):
        self.discord_url = discord_url
        self.tg_token = tg_token
        self.tg_chat_id = tg_chat_id
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def send(self, title: str, details: Dict[str, Any]):
        client = await self._get_client()
        if self.discord_url:
            await self._send_discord(client, title, details)
        if self.tg_token and self.tg_chat_id:
            await self._send_telegram(client, title, details)

    async def _send_discord(self, client: httpx.AsyncClient, title: str, data: Dict[str, Any]):
        fields = []
        for k, v in data.items():
            fields.append({"name": str(k), "value": str(v), "inline": True})

        payload = {
            "embeds": [{
                "title": title,
                "color": 0x00ff88,
                "fields": fields
            }]
        }
        try:
            res = await client.post(self.discord_url, json=payload)
            if res.status_code >= 400:
                log.warning(f"discord webhook failed: {res.status_code} {res.text}")
        except Exception as e:
            log.error(f"failed sending discord alert: {e}")

    async def _send_telegram(self, client: httpx.AsyncClient, title: str, data: Dict[str, Any]):
        url = f"https://api.telegram.org/bot{self.tg_token}/sendMessage"
        lines = [f"*{title}*"]
        for k, v in data.items():
            lines.append(f"{k}: `{v}`")
        text = "\n".join(lines)

        payload = {
            "chat_id": self.tg_chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            res = await client.post(url, json=payload)
            if res.status_code >= 400:
                log.warning(f"tg send failed: {res.status_code} {res.text}")
        except Exception as e:
            log.error(f"failed sending telegram alert: {e}")
