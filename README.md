# Gold price alert (India, free end-to-end)

Scrapes today's gold price per 10 grams (India) from Goodreturns and sends
you a WhatsApp message (via CallMeBot, free) and/or a Telegram message
(free, no limits), on a daily schedule via GitHub Actions (free).

Everything in this stack has a free tier suitable for one personal daily
alert. No server of your own needs to run 24/7.

## 1. Get the code running

```bash
pip install -r requirements.txt
python gold_price_alert.py
```

If neither WhatsApp nor Telegram env vars are set yet, it will just fetch
and log the price so you can confirm scraping works before wiring up alerts.

## 2. Set up free WhatsApp alerts (CallMeBot)

1. Save this contact in your phone: `+34 644 51 95 23` (CallMeBot's number).
2. On WhatsApp, message that contact exactly: `I allow callmebot to send me messages`
3. Wait for a reply containing your personal API key.
4. Note down your WhatsApp number (with country code, no `+` or spaces,
   e.g. `91XXXXXXXXXX`) and the API key — you'll add these as secrets, not
   in the code.

CallMeBot is a free, unofficial, best-effort service with light rate
limits — fine for one alert a day, not for high-volume messaging.

## 3. Set up free Telegram alerts (recommended as a reliable backup)

1. In Telegram, message `@BotFather`, send `/newbot`, follow the prompts.
   You'll get a bot token like `123456:ABC-DEF...`.
2. Send your new bot any message (e.g. "hi").
3. Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser
   and find your numeric `chat.id` in the JSON response.
4. Keep the bot token and chat id handy for the next step.

Telegram is completely free with no practical rate limit for personal use,
so it's a good backup if CallMeBot is ever down or rate-limited.

## 4. Store credentials as secrets (never in code)

Push this project to a GitHub repo, then go to:
**Repo → Settings → Secrets and variables → Actions → New repository secret**

Add whichever of these you're using:

| Secret name | Value |
|---|---|
| `CALLMEBOT_PHONE` | your WhatsApp number, e.g. `91XXXXXXXXXX` |
| `CALLMEBOT_APIKEY` | the key CallMeBot messaged you |
| `TELEGRAM_BOT_TOKEN` | your bot token from BotFather |
| `TELEGRAM_CHAT_ID` | your numeric chat id |

Your phone number and chat id are personal data — this is exactly why they
live in encrypted GitHub Secrets and are pulled in only as environment
variables at run time, never committed to the repository.

## 5. Scheduling (free, no server needed)

The included `.github/workflows/gold-price-alert.yml` runs automatically
every day at 09:00 IST using GitHub Actions' free scheduled workflows.
Change the `cron` line to adjust the time (cron times are always UTC).

To test immediately without waiting for the schedule: go to your repo's
**Actions** tab → **Gold price alert** → **Run workflow**.

### Alternative: run it yourself instead of GitHub Actions
- **Linux/Mac**: add a line to `crontab -e`, e.g.
  `30 3 * * * cd /path/to/project && /usr/bin/python3 gold_price_alert.py`
- **Windows**: use Task Scheduler to run the script daily.
- Either way, set the same environment variables locally (e.g. via a
  `.env` file loaded with `python-dotenv`, or your OS's secret manager) —
  don't hardcode them into the script.

## Notes and limits

- The scraper parses a specific sentence pattern from Goodreturns' page.
  If they redesign the page and the wording changes, `fetch_gold_price()`
  will raise a clear error rather than send a wrong price — update the
  regex in `gold_price_alert.py` if that happens.
- This pulls a *displayed* price for personal reference/alerting only.
  Don't resell, redistribute, or scrape at high frequency — once a day is
  plenty for a price that updates daily, and is kinder to the source site.
- CallMeBot is an unofficial free service with no uptime guarantee;
  Telegram is included as a free, more reliable fallback channel.
