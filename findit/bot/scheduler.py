"""Scheduled jobs for the Telegram bot (daily match push)."""

from __future__ import annotations

import logging
from datetime import time

from telegram.ext import Application

from findit.bot import messages as msg
from findit.bot.handlers import _format_match_card, _match_keyboard, _get_db, _get_engine
from findit.config import settings

logger = logging.getLogger(__name__)


async def _daily_push_job(context) -> None:
    """Push daily matches to all active users."""
    db = _get_db()
    engine = _get_engine()

    with db._conn() as conn:
        rows = conn.execute(
            "SELECT * FROM users WHERE setup_complete = 1"
        ).fetchall()

    users = [dict(r) for r in rows]
    logger.info("Daily push: processing %d users", len(users))

    for user in users:
        try:
            matches = engine.process_pipeline_for_user(user)
            telegram_id = int(user["telegram_id"])

            if not matches:
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=msg.NO_MATCHES,
                )
                continue

            # Send header
            await context.bot.send_message(
                chat_id=telegram_id,
                text=f"🌟 今日为你精选了 {len(matches)} 个匹配！",
            )

            for i, match in enumerate(matches, 1):
                card = _format_match_card(match, i, len(matches))
                keyboard = _match_keyboard(match["id"])
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=card,
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
                db.mark_match_pushed(match["id"])

            logger.info("Pushed %d matches to user %s", len(matches), user["telegram_id"])

        except Exception:
            logger.exception("Failed to push matches to user %s", user.get("telegram_id"))


def schedule_daily_push(app: Application) -> None:
    """Register the daily push job on the bot's job queue."""
    push_time = time(
        hour=settings.push_hour,
        minute=settings.push_minute,
    )
    app.job_queue.run_daily(
        _daily_push_job,
        time=push_time,
        name="daily_match_push",
    )
    logger.info("Scheduled daily push at %02d:%02d", settings.push_hour, settings.push_minute)
