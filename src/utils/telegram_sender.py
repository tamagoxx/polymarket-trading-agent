"""Telegram sender for trading signals."""
import httpx
from loguru import logger


class TelegramSender:
    """Kirim signal ke Telegram chat."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Kirim message ke Telegram."""
        try:
            url = f"{self.api_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            }
            with httpx.Client(timeout=15) as client:
                resp = client.post(url, json=payload)
                data = resp.json()
                if data.get("ok"):
                    msg_id = data.get("result", {}).get("message_id", "N/A")
                    logger.info(f"Telegram message sent: {msg_id}")
                    return True
                else:
                    logger.error(f"Telegram error: {data}")
                    return False
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def send_signal(self, signal: dict) -> bool:
        """Format dan kirim single signal ke Telegram."""
        question = signal.get("question", "N/A")[:80]
        signal_type = signal.get("signal_type", "NEUTRAL")
        edge = signal.get("edge", 0)
        confidence = signal.get("confidence", 0)
        reasoning = (signal.get("reasoning", [""])[0][:150] or "N/A")
        url = signal.get("url", "https://polymarket.com")

        emoji = {"BUY": "🟢", "SELL": "🔴", "NEUTRAL": "⚪"}.get(signal_type, "⚪")

        text = (
            f"{emoji} <b>POLYMARKET SIGNAL</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>{question}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Signal: <b>{signal_type}</b>\n"
            f"📐 Edge: <b>{edge:+.1%}</b>\n"
            f"🎯 Confidence: <b>{confidence:.0%}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>{reasoning}...</i>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 <a href=\"{url}\">View Market</a>"
        )
        return self.send_message(text)

    def send_scan_summary(self, top_signals: list, total_markets: int = 0) -> bool:
        """Kirim summary scan result."""
        count = len(top_signals)
        if count == 0:
            text = (
                "🤖 <b>Polymarket Scan Complete</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Scanned {total_markets} markets\n"
                f"No actionable signals found.\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                "<i>Run time: just now</i>"
            )
        else:
            signal_lines = []
            for i, s in enumerate(top_signals[:5], 1):
                q = s.get("question", "N/A")[:40]
                st = s.get("signal_type", "?")
                e = s.get("edge", 0)
                c = s.get("confidence", 0)
                signal_lines.append(
                    f"{i}. <b>{q}</b>\n"
                    f"   {st} {e:+.1%} | {c:.0%}"
                )

            text = (
                f"🤖 <b>Polymarket Scan — {count} Signal{'s' if count > 1 else ''}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                + "\n\n".join(signal_lines)
                + f"\n━━━━━━━━━━━━━━━━━━━━\n"
                f"<i>Scanned {total_markets} markets via TinyFiAi bot</i>"
            )
        return self.send_message(text)


def send_telegram_signal(bot_token: str, chat_id: str, signal: dict) -> bool:
    """Helper: kirim single signal."""
    sender = TelegramSender(bot_token, chat_id)
    return sender.send_signal(signal)


def send_telegram_summary(bot_token: str, chat_id: str, signals: list, total_markets: int = 0) -> bool:
    """Helper: kirim scan summary."""
    sender = TelegramSender(bot_token, chat_id)
    return sender.send_scan_summary(signals, total_markets)
