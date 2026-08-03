import asyncio
import logging
import httpx
from typing import Optional, Dict, Any

log = logging.getLogger("pairsniper.notifier")


def _escape_tg(text: str) -> str:
    # Telegram MarkdownV2 requires escaping these characters outside code blocks
    chars = r"_*[]()~`>#+-=|{}.!"
    out = []
    for ch in str(text):
        if ch in chars:
            out.append(f"\\{ch}")
        else:
            out.append(ch)
    return "".join(out)


class Notifier:
    """Sends alert payloads to Discord webhooks or Telegram chats."""

    def __init__(self, discord_url: Optional[str] = None, tg_token: Optional[str] = None, tg_chat_id: Optional[str] = None):
        self.discord_url = discord_url
        self.tg_token = tg_token
        self.tg_chat_id = tg_chat_id
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=8.0)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def send(self, title: str, details: Dict[str, Any]):
        client = await self._get_client()
        tasks = []
        if self.discord_url:
            tasks.append(self._send_discord(client, title, details))
        if self.tg_token and self.tg_chat_id:
            tasks.append(self._send_telegram(client, title, details))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _post_with_retry(self, client: httpx.AsyncClient, url: str, json_data: dict, max_retries: int = 2) -> Optional[httpx.Response]:
        for attempt in range(max_retries + 1):
            try:
                res = await client.post(url, json=json_data)
                if res.status_code == 429:
                    retry_after = 1.0
                    try:
                        retry_after = float(res.json().get("retry_after", 1.0))
                    except Exception:
                        pass
                    # log.debug(f"rate limited on {url}, sleeping {retry_after}s")
                    await asyncio.sleep(min(retry_after, 5.0))
                    continue
                return res
            except httpx.RequestError as e:
                if attempt == max_retries:
                    log.error(f"request to {url} failed after {max_retries} retries: {e}")
                    return None
                await asyncio.sleep(0.5)
        return None

    async def _send_discord(self, client: httpx.AsyncClient, title: str, data: Dict[str, Any]):
        fields = []
        for k, v in data.items():
            fields.append({"name": str(k), "value": f"`{v}`" if "0x" in str(v) else str(v), "inline": True})

        payload = {
            "embeds": [{
                "title": title,
                "color": 0x2ecc71 if "PASSED" in str(data.get("status", "")) else 0xe74c3c,
                "fields": fields,
                "footer": {"text": "pairsniper-v2"}
            }]
        }

        res = await self._post_with_retry(client, self.discord_url, payload)
        if res and res.status_code >= 400:
            log.warning(f"discord webhook rejected: {res.status_code} - {res.text[:120]}")

    async def _send_telegram(self, client: httpx.AsyncClient, title: str, data: Dict[str, Any]):
        url = f"https://api.telegram.org/bot{self.tg_token}/sendMessage"
        
        # FIXME: telegram HTML mode is less brittle than MarkdownV2, rewrite this next
        lines = [f"*{_escape_tg(title)}*"]
        for k, v in data.items():
            val_str = str(v)
            if val_str.startswith("0x"):
                lines.append(f"{_escape_tg(k)}: `{val_str}`")
            else:
                lines.append(f"{_escape_tg(k)}: {_escape_tg(val_str)}")
        text = "\n".join(lines)

        payload = {
            "chat_id": self.tg_chat_id,
            "text": text,
            "parse_mode": "MarkdownV2",
            "disable_web_page_preview": True
        }
        res = await self._post_with_retry(client, url, payload)
        if res and res.status_code >= 400:
            log.warning(f"tg send rejected: {res.status_code} - {res.text[:120]}")
