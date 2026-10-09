# Telegram Meet Bot

Бот за групи: всеки пише `/meet` → получава Google Meet линк в чата.

## Локално (първи път)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # сложи TELEGRAM_BOT_TOKEN
# сложи credentials.json (OAuth Desktop от Google Cloud)
python bot.py          # браузър → Allow → създава token.json
```

## Telegram (BotFather)

1. `/newbot` → token → `.env`
2. `/setprivacy` → **Disable** (задължително за групи)
3. `/setcommands`:
   ```
   meet - Create a Google Meet link
   start - Help
   ```
4. Добави бота в групата

## Google Cloud

1. Enable **Google Calendar API**
2. OAuth consent → External → Test user = твоя Gmail
3. OAuth Client ID → **Desktop** → download → `credentials.json`

## Railway (24/7)

1. `railway login`
2. `railway init` / link project
3. Variables:
   - `TELEGRAM_BOT_TOKEN`
   - `GOOGLE_CREDENTIALS_JSON` (цялото съдържание на credentials.json)
   - `GOOGLE_TOKEN_JSON` (цялото съдържание на token.json)
4. Start command: `python bot.py`
5. **Serverless OFF**
6. `railway up` или deploy от GitHub

## Команди

| Команда | Действие |
|---------|----------|
| `/start` | Помощ |
| `/meet`  | Нов Google Meet линк (рандом забавни съобщения) |
| `/msg` | Редакция на рандом съобщенията (list / add / del) |

Съобщенията са в [`messages.json`](messages.json). `{user}` се заменя с `@username` при ready текстовете.

**Забележка:** `/msg` записва във файла на сървъра. Без Railway Volume промените се губят при нов deploy — тогава редактирай `messages.json` в repo и redeploy.
