"""Telegram bot application entry point.

Sets up the bot with:
- Command handlers (/start, /setup, /match, /preferences, /help)
- Message handler for the setup flow
- Callback handler for inline buttons (like/pass/regenerate)
- Scheduled daily push job
"""

from __future__ import annotations

import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from findit.bot.handlers import (
    cmd_help,
    cmd_match,
    cmd_preferences,
    cmd_setup,
    cmd_start,
    handle_callback,
    handle_message,
)
from findit.bot.scheduler import schedule_daily_push
from findit.config import settings

logger = logging.getLogger(__name__)


def create_app() -> Application:
    """Build and configure the Telegram bot application."""
    app = Application.builder().token(settings.telegram_bot_token).build()

    # Command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("setup", cmd_setup))
    app.add_handler(CommandHandler("match", cmd_match))
    app.add_handler(CommandHandler("preferences", cmd_preferences))

    # Callback query handler for inline buttons
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Text message handler (setup flow + fallback)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return app


def main() -> None:
    """Start the Telegram bot with polling."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    logger.info("Starting FindIt Telegram bot")

    app = create_app()

    # Schedule daily push
    schedule_daily_push(app)

    # Run with polling
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
