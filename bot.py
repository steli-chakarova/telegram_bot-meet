"""Telegram bot: /meet creates a Google Meet link for the chat."""

from __future__ import annotations

import asyncio
import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from access import (
    allow_chat,
    allow_user,
    deny_chat,
    deny_user,
    is_admin,
    is_allowed,
    load_access,
    set_enabled,
)
from google_meet import create_meet_link
from messages import add_message, delete_message, load_messages, pick_pending, pick_ready

load_dotenv()

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

MSG_HELP = (
    "Редакция на рандом съобщенията:\n"
    "/msg list — всички\n"
    "/msg list pending — докато се генерира\n"
    "/msg list ready — с линка ({user} = @username)\n"
    "/msg add pending ТЕКСТ\n"
    "/msg add ready ТЕКСТ\n"
    "/msg del pending N\n"
    "/msg del ready N\n\n"
    "При ready можеш да пишеш с {user}, напр:\n"
    "/msg add ready {user} свиква седянка:\n"
    "Ако няма {user}, се добавя автоматично отпред."
)

ACCESS_HELP = (
    "Достъп (само админ):\n"
    "/access — статус\n"
    "/access on | off — включи/изключи ограничението\n"
    "/allow here — разреши този чат/група\n"
    "/deny here — махни този чат\n"
    "/allow me — разреши твоя личен чат (user id)\n"
    "/deny me — махни user id\n"
    "/myid — покажи user id и chat id"
)

HELP_PUBLIC = (
    "Команди:\n"
    "/meet — създава Google Meet линк\n"
    "/help — този списък\n"
    "/start — кратко представяне\n"
    "/myid — твой user id и chat id\n\n"
    "Админ командите (/msg, /access, /allow, /deny) "
    "работят само за собственика на бота — другите не могат да правят промени."
)

HELP_ADMIN = (
    "Команди (админ):\n"
    "/meet — Google Meet линк\n"
    "/help — този списък\n"
    "/start — кратко представяне\n"
    "/myid — user id и chat id\n"
    "/msg — редакция на рандом съобщенията\n"
    "/access — статус / on / off за ограничението\n"
    "/allow here|me — разреши чат или себе си\n"
    "/deny here|me — махни чат или себе си"
)

DENIED = "Нямаш достъп до този бот в този чат."


async def _require_admin(update: Update) -> bool:
    user = update.effective_user
    if user and is_admin(user.id):
        return True
    if update.message:
        await update.message.reply_text(
            "Само админ може да ползва тази команда. "
            "Не можеш да променяш настройките на бота."
        )
    return False


async def _require_allowed(update: Update) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    chat_id = chat.id if chat else None
    user_id = user.id if user else None
    if is_allowed(chat_id, user_id):
        return True
    if update.message:
        await update.message.reply_text(DENIED)
    return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        "Какво не разбра бе, пич? Напиши /meet за Google Meet линк.\n"
        "За всичко останало използвай /help."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    if is_admin(update.effective_user.id):
        await update.message.reply_text(HELP_ADMIN)
    else:
        await update.message.reply_text(HELP_PUBLIC)


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat or not update.effective_user:
        return
    chat = update.effective_chat
    user = update.effective_user
    await update.message.reply_text(
        f"user id: `{user.id}`\n"
        f"chat id: `{chat.id}`\n"
        f"chat type: {chat.type}\n\n"
        "Админ: сложи user id в Railway → Variables → "
        "ADMIN_TELEGRAM_IDS\n"
        "После в групата: /allow here",
        parse_mode="Markdown",
    )


async def meet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    if not await _require_allowed(update):
        return

    user = update.effective_user
    who = f"@{user.username}" if user.username else user.first_name or "някой"

    await update.message.reply_text(pick_pending())

    try:
        link = await asyncio.to_thread(
            create_meet_link, f"Telegram Meet ({who})"
        )
    except Exception:
        logger.exception("Failed to create Meet link")
        await update.message.reply_text(
            "Не успях да създам Meet линк. Провери Google credentials/token "
            "и опитай пак."
        )
        return

    await update.message.reply_text(f"{pick_ready(who)}\n{link}")


async def msg_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    if not await _require_admin(update):
        return

    args = context.args or []
    if not args:
        await update.message.reply_text(MSG_HELP)
        return

    action = args[0].lower()

    if action == "list":
        kind = args[1].lower() if len(args) > 1 else "all"
        data = load_messages()
        parts: list[str] = []
        kinds = ("pending", "ready") if kind == "all" else (kind,)
        if kind not in ("all", "pending", "ready"):
            await update.message.reply_text(
                "Ползвай: /msg list | /msg list pending | /msg list ready"
            )
            return
        for k in kinds:
            lines = [f"— {k} ({len(data[k])}) —"]
            for i, text in enumerate(data[k], start=1):
                lines.append(f"{i}. {text}")
            parts.append("\n".join(lines))
        text = "\n\n".join(parts)
        if len(text) > 4000:
            for chunk_start in range(0, len(text), 3500):
                await update.message.reply_text(
                    text[chunk_start : chunk_start + 3500]
                )
        else:
            await update.message.reply_text(text)
        return

    if action == "add":
        if len(args) < 3:
            await update.message.reply_text("Пример: /msg add pending Момент...")
            return
        kind = args[1].lower()
        body = " ".join(args[2:]).strip()
        try:
            n = add_message(kind, body)
        except ValueError as exc:
            await update.message.reply_text(str(exc))
            return
        await update.message.reply_text(f"Добавено към {kind}. Общо: {n}")
        return

    if action in ("del", "delete", "rm", "remove"):
        if len(args) < 3:
            await update.message.reply_text("Пример: /msg del pending 3")
            return
        kind = args[1].lower()
        try:
            index = int(args[2])
            removed = delete_message(kind, index)
        except ValueError as exc:
            await update.message.reply_text(str(exc))
            return
        except IndexError as exc:
            await update.message.reply_text(str(exc))
            return
        await update.message.reply_text(f"Махнато от {kind}:\n{removed}")
        return

    await update.message.reply_text(MSG_HELP)


async def access_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    if not await _require_admin(update):
        return

    args = context.args or []
    if not args:
        data = load_access()
        status = "ВКЛЮЧЕН" if data["enabled"] else "ИЗКЛЮЧЕН (всеки може)"
        await update.message.reply_text(
            f"Ограничение: {status}\n"
            f"Чатове: {data['chats'] or '—'}\n"
            f"Users: {data['users'] or '—'}\n\n"
            f"{ACCESS_HELP}"
        )
        return

    action = args[0].lower()
    if action == "on":
        set_enabled(True)
        await update.message.reply_text(
            "Ограничението е ВКЛЮЧЕНО. Само allowlist + админ."
        )
        return
    if action == "off":
        set_enabled(False)
        await update.message.reply_text(
            "Ограничението е ИЗКЛЮЧЕНО. Всеки може /meet."
        )
        return
    await update.message.reply_text(ACCESS_HELP)


async def allow_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat or not update.effective_user:
        return
    if not await _require_admin(update):
        return

    args = context.args or []
    if not args or args[0].lower() == "here":
        chat_id = update.effective_chat.id
        added = allow_chat(chat_id)
        msg = (
            f"Чат `{chat_id}` е разрешен."
            if added
            else f"Чат `{chat_id}` вече беше разрешен."
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    if args[0].lower() == "me":
        uid = update.effective_user.id
        added = allow_user(uid)
        msg = (
            f"User `{uid}` е разрешен."
            if added
            else f"User `{uid}` вече беше разрешен."
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    await update.message.reply_text("Ползвай: /allow here   или   /allow me")


async def deny_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat or not update.effective_user:
        return
    if not await _require_admin(update):
        return

    args = context.args or []
    if not args or args[0].lower() == "here":
        chat_id = update.effective_chat.id
        removed = deny_chat(chat_id)
        msg = (
            f"Чат `{chat_id}` е махнат."
            if removed
            else f"Чат `{chat_id}` не беше в списъка."
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    if args[0].lower() == "me":
        uid = update.effective_user.id
        removed = deny_user(uid)
        msg = (
            f"User `{uid}` е махнат."
            if removed
            else f"User `{uid}` не беше в списъка."
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    await update.message.reply_text("Ползвай: /deny here   или   /deny me")


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in .env or environment.")

    admins = os.getenv("ADMIN_TELEGRAM_IDS", "").strip()
    if not admins:
        logger.warning(
            "ADMIN_TELEGRAM_IDS is empty — /allow /msg /access won't work "
            "until you set your Telegram user id."
        )

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("meet", meet))
    app.add_handler(CommandHandler("msg", msg_cmd))
    app.add_handler(CommandHandler("access", access_cmd))
    app.add_handler(CommandHandler("allow", allow_cmd))
    app.add_handler(CommandHandler("deny", deny_cmd))

    logger.info("Bot starting (polling)…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
