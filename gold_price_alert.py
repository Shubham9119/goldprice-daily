"""
Gold price (per 10 gram, India) fetch + WhatsApp/Telegram alert.

Design notes (security):
- No secrets are hardcoded anywhere in this file. Every credential (GoldAPI
  token, CallMeBot API key, Telegram bot token/chat id) is read from
  environment variables at runtime. In GitHub Actions these come from
  encrypted repo Secrets; locally they come from a .env file that is
  git-ignored (see README).
- The script only ever makes outbound GET/POST requests to a small, fixed
  set of URLs (least privilege) — it does not accept or execute any
  user-supplied URL, command, or code, so there is no injection surface.
- All network calls use an explicit timeout so a hung request can't stall
  the scheduled job indefinitely (denial-of-service resilience).
- API response fields are validated (range-checked) before use; if a value
  is missing or implausible the script fails loudly instead of silently
  sending a garbage/blank alert.

Why an API instead of scraping a price-comparison site:
Sites like Goodreturns render their "today's price" client-side or serve
cached/stale HTML to non-browser requests (confirmed: a plain HTTP fetch
returned a stale 2017 snapshot while the live browser page showed current
data). That makes plain HTML scraping unreliable for this kind of
frequently-updated, JS-assisted content. GoldAPI.io is used instead: a
lightweight JSON API purpose-built for this, which returns the current
24K/22K price per gram in whatever currency you ask for (INR here)
directly, with no HTML parsing involved.
"""

import os
import sys
import logging
from dataclasses import dataclass

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("gold_price_alert")

# Fixed, non-configurable source URL — not derived from any user input.
GOLD_API_URL = "https://www.goldapi.io/api/XAU/INR"
REQUEST_TIMEOUT_SECONDS = 15


@dataclass
class GoldPrice:
    price_24k_per_gram: float
    price_22k_per_gram: float

    @property
    def price_24k_per_10g(self) -> float:
        return round(self.price_24k_per_gram * 10, 2)

    @property
    def price_22k_per_10g(self) -> float:
        return round(self.price_22k_per_gram * 10, 2)


def fetch_gold_price() -> GoldPrice:
    """
    Fetch today's gold price (per gram, INR) from GoldAPI.io.

    Requires the GOLD_API_TOKEN env var (free signup at goldapi.io, no
    card required). The token is sent as a request header, never as a
    URL query parameter, so it won't leak into logs or browser history.
    """
    token = os.environ.get("GOLD_API_TOKEN")
    if not token:
        raise RuntimeError(
            "GOLD_API_TOKEN is not set. Sign up free at https://www.goldapi.io/ "
            "and add the token as a GOLD_API_TOKEN secret/env var."
        )

    try:
        response = requests.get(
            GOLD_API_URL,
            headers={"x-access-token": token, "Accept": "application/json"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        # Fail closed: never send an alert built from partial/garbage data.
        raise RuntimeError(f"Could not reach GoldAPI.io: {exc}") from exc

    try:
        data = response.json()
        price_24k = float(data["price_gram_24k"])
        price_22k = float(data["price_gram_22k"])
    except (ValueError, KeyError, TypeError) as exc:
        raise RuntimeError(
            f"Unexpected GoldAPI.io response shape, could not parse price: {exc}"
        ) from exc

    # Sanity check the parsed numbers are in a plausible range for INR/gram
    # gold prices, to catch a mis-parse or bad response before it goes out
    # as an alert.
    for label, value in (("24k", price_24k), ("22k", price_22k)):
        if not (1000 <= value <= 100000):
            raise RuntimeError(f"Parsed {label} price {value} looks implausible — aborting.")

    return GoldPrice(price_24k_per_gram=price_24k, price_22k_per_gram=price_22k)


def build_message(price: GoldPrice) -> str:
    return (
        "Gold price update (India)\n"
        f"24K: Rs {price.price_24k_per_10g:,.2f} / 10g\n"
        f"22K: Rs {price.price_22k_per_10g:,.2f} / 10g"
    )


def send_whatsapp_callmebot(message: str) -> None:
    """
    Send a WhatsApp message via CallMeBot's free API.
    Setup (one-time, see README): add the CallMeBot contact on WhatsApp,
    send the activation phrase, and it replies with your personal API key.

    Required env vars:
      CALLMEBOT_PHONE   - your WhatsApp number with country code, e.g. 91XXXXXXXXXX
      CALLMEBOT_APIKEY  - the key CallMeBot sent you
    """
    phone = os.environ.get("CALLMEBOT_PHONE")
    apikey = os.environ.get("CALLMEBOT_APIKEY")
    if not phone or not apikey:
        log.info("CallMeBot env vars not set — skipping WhatsApp send.")
        return

    try:
        resp = requests.get(
            "https://api.callmebot.com/whatsapp.php",
            params={"phone": phone, "text": message, "apikey": apikey},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        log.info("WhatsApp alert sent via CallMeBot.")
    except requests.RequestException as exc:
        # Don't crash the whole job just because one channel failed —
        # log and let other channels (e.g. Telegram) still be attempted.
        log.error("CallMeBot send failed: %s", exc)


def send_telegram(message: str) -> None:
    """
    Send a message via a Telegram bot (completely free, no rate limits
    for personal use). Setup (see README): create a bot with @BotFather,
    then send it any message and fetch your chat id once.

    Required env vars:
      TELEGRAM_BOT_TOKEN
      TELEGRAM_CHAT_ID
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        log.info("Telegram env vars not set — skipping Telegram send.")
        return

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": message},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        log.info("Telegram alert sent.")
    except requests.RequestException as exc:
        log.error("Telegram send failed: %s", exc)


def main() -> int:
    try:
        price = fetch_gold_price()
    except RuntimeError as exc:
        log.error(str(exc))
        return 1

    message = build_message(price)
    log.info("Parsed price: %s", message.replace("\n", " | "))

    send_whatsapp_callmebot(message)
    send_telegram(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
