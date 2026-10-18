# deals-watcher

Daily deal digest for Al Ri. Runs on GitHub Actions (free), fetches r/deals,
filters with Groq's free tier against her interests and her bar ("only something
good, with a deadline"), and delivers by Telegram. Most days: silence.

- Schedule: 17:00 UTC (10am PDT / 9am PST)
- Secrets required: GROQ_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
- keepalive.yml commits monthly so GitHub never disables the schedule
