"""Telegram bot command and callback handlers."""

from __future__ import annotations

import json
import logging
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from findit.ai.opener import OpenerGenerator
from findit.bot import messages as msg
from findit.config import settings
from findit.db import Database
from findit.services.matching_service import MatchingService

logger = logging.getLogger(__name__)

# Setup flow step definitions
SETUP_STEPS = [
    ("age", msg.SETUP_AGE),
    ("height", msg.SETUP_HEIGHT),
    ("education", msg.SETUP_EDUCATION),
    ("school", msg.SETUP_SCHOOL),
    ("occupation", msg.SETUP_OCCUPATION),
    ("income_range", msg.SETUP_INCOME),
    ("city", msg.SETUP_CITY),
    ("hobbies", msg.SETUP_HOBBIES),
    ("highlights", msg.SETUP_HIGHLIGHTS),
]

STEP_NAMES = [s[0] for s in SETUP_STEPS]


def _get_db() -> Database:
    return Database(settings.db_path)


def _get_matching_service() -> MatchingService:
    return MatchingService(_get_db())


# ── Command handlers ────────────────────────────────────────────────────


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    db = _get_db()
    db.get_or_create_user(str(update.effective_user.id))
    await update.message.reply_text(msg.WELCOME)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await update.message.reply_text(msg.HELP_TEXT)


async def cmd_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /setup command - start profile setup flow."""
    db = _get_db()
    db.get_or_create_user(str(update.effective_user.id))
    db.update_user(str(update.effective_user.id), setup_step="age", setup_complete=0)
    await update.message.reply_text(msg.SETUP_AGE)


async def cmd_match(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /match command - get daily matches."""
    db = _get_db()
    user = db.get_user_by_telegram(str(update.effective_user.id))

    if not user or not user.get("setup_complete"):
        await update.message.reply_text(msg.ERROR_NOT_SETUP)
        return

    await update.message.reply_text("🔍 正在为你寻找匹配，请稍候...")

    try:
        matching = _get_matching_service()
        matches = matching.generate_matches(user)

        if not matches:
            await update.message.reply_text(msg.NO_MATCHES)
            return

        for i, match in enumerate(matches, 1):
            card = _format_match_card(match, i, len(matches))
            keyboard = _match_keyboard(match["id"])
            await update.message.reply_text(
                card,
                reply_markup=keyboard,
                parse_mode="Markdown",
            )
            # Mark as pushed
            db.mark_match_pushed(match["id"])

    except Exception:
        logger.exception("Error generating matches")
        await update.message.reply_text(msg.ERROR_GENERIC)


async def cmd_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /preferences command."""
    db = _get_db()
    user = db.get_user_by_telegram(str(update.effective_user.id))
    if not user:
        await update.message.reply_text(msg.ERROR_NOT_SETUP)
        return

    # Set flag so next message is treated as preferences input
    db.update_user(str(update.effective_user.id), setup_step="preferences")
    await update.message.reply_text(msg.PREFERENCES_PROMPT)


# ── Message handler (for setup flow) ───────────────────────────────────


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages - primarily for the setup flow."""
    db = _get_db()
    telegram_id = str(update.effective_user.id)
    user = db.get_user_by_telegram(telegram_id)

    if not user:
        await update.message.reply_text(msg.WELCOME)
        return

    current_step = user.get("setup_step", "")
    text = update.message.text.strip()

    # Handle preferences input
    if current_step == "preferences":
        await _handle_preferences_input(update, db, telegram_id, text)
        return

    # Handle setup flow
    if current_step in STEP_NAMES:
        await _handle_setup_step(update, db, telegram_id, user, current_step, text)
        return

    # Default: suggest commands
    await update.message.reply_text(
        "输入 /match 获取今日推荐，或 /help 查看所有命令。"
    )


async def _handle_setup_step(
    update: Update,
    db: Database,
    telegram_id: str,
    user: dict,
    step: str,
    text: str,
) -> None:
    """Process a single setup step and advance to next."""
    # Validate and save
    value: Any = text

    if step == "age":
        try:
            value = int(text)
            if not 18 <= value <= 60:
                await update.message.reply_text("请输入18-60之间的年龄")
                return
        except ValueError:
            await update.message.reply_text("请输入数字")
            return

    elif step == "height":
        try:
            value = int(text)
            if not 150 <= value <= 220:
                await update.message.reply_text("请输入150-220之间的身高(cm)")
                return
        except ValueError:
            await update.message.reply_text("请输入数字")
            return

    elif step == "education":
        valid = ["高中", "大专", "本科", "硕士", "博士"]
        if text not in valid:
            await update.message.reply_text(f"请选择：{'/ '.join(valid)}")
            return

    elif step == "school":
        if text == "跳过":
            value = ""

    elif step == "income_range":
        valid = ["1万以下", "1-2万", "2-3万", "3-5万", "5万以上"]
        if text not in valid:
            await update.message.reply_text(f"请选择：{'/ '.join(valid)}")
            return

    elif step == "hobbies":
        value = [h.strip() for h in text.replace("，", ",").split(",") if h.strip()]

    elif step == "highlights":
        if text == "跳过":
            value = []
        else:
            value = [h.strip() for h in text.replace("，", ",").split(",") if h.strip()]

    # Save the field
    db.update_user(telegram_id, **{step: value})

    # Advance to next step
    step_idx = STEP_NAMES.index(step)
    if step_idx + 1 < len(SETUP_STEPS):
        next_step = SETUP_STEPS[step_idx + 1]
        db.update_user(telegram_id, setup_step=next_step[0])
        await update.message.reply_text(next_step[1])
    else:
        # Setup complete
        db.update_user(telegram_id, setup_complete=1, setup_step="done")
        user = db.get_user_by_telegram(telegram_id)

        hobbies = user.get("hobbies", "[]")
        if isinstance(hobbies, str):
            try:
                hobbies = json.loads(hobbies)
            except (json.JSONDecodeError, TypeError):
                hobbies = []

        highlights = user.get("highlights", "[]")
        if isinstance(highlights, str):
            try:
                highlights = json.loads(highlights)
            except (json.JSONDecodeError, TypeError):
                highlights = []

        await update.message.reply_text(
            msg.SETUP_COMPLETE.format(
                age=user.get("age", ""),
                height=user.get("height", ""),
                education=user.get("education", ""),
                school=user.get("school") or "未填",
                occupation=user.get("occupation", ""),
                income_range=user.get("income_range", ""),
                city=user.get("city", ""),
                hobbies=", ".join(hobbies) if hobbies else "未填",
                highlights=", ".join(highlights) if highlights else "无",
            )
        )


async def _handle_preferences_input(
    update: Update, db: Database, telegram_id: str, text: str
) -> None:
    """Parse and save user preferences."""
    try:
        parts = text.replace("，", ",").split()
        prefs: dict[str, Any] = {}

        if len(parts) >= 1:
            age_range = parts[0]
            if "-" in age_range:
                lo, hi = age_range.split("-", 1)
                prefs["age_min"] = int(lo)
                prefs["age_max"] = int(hi)

        if len(parts) >= 2:
            prefs["allow_remote"] = parts[1] in ("是", "yes", "true")

        db.update_user(telegram_id, preferences=prefs, setup_step="done")
        await update.message.reply_text(msg.PREFERENCES_SAVED)
    except Exception:
        await update.message.reply_text("格式不对，请按示例输入：22-28 否")


# ── Callback query handler (inline buttons) ────────────────────────────


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard button presses."""
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    db = _get_db()
    telegram_id = str(update.effective_user.id)

    if data.startswith("like_"):
        match_id = int(data.split("_")[1])
        db.update_match_action(match_id, "liked")
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(msg.ACTION_LIKED)

    elif data.startswith("pass_"):
        match_id = int(data.split("_")[1])
        db.update_match_action(match_id, "passed")
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(msg.ACTION_PASSED)

    elif data.startswith("regen_"):
        match_id = int(data.split("_")[1])
        await query.message.reply_text(msg.ACTION_REGENERATE)

        match = db.get_match_by_id(match_id)
        if match:
            user = db.get_user_by_telegram(telegram_id)
            author = db.get_author(match["author_id"])
            if user and author:
                opener_gen = OpenerGenerator()
                new_opener = opener_gen.regenerate_single(
                    {"content": match.get("post_content", "")},
                    author,
                    user,
                    match.get("generated_opener", ""),
                )
                if new_opener:
                    db.update_match_opener(match_id, new_opener)
                    await query.message.reply_text(
                        msg.ACTION_REGENERATED.format(opener=new_opener),
                        parse_mode="Markdown",
                    )
                    return

        await query.message.reply_text(msg.ERROR_GENERIC)


# ── Helpers ─────────────────────────────────────────────────────────────


def _format_match_card(match: dict, index: int, total: int) -> str:
    """Format a match record into a display card."""
    bio = match.get("bio") or "暂无简介"
    if len(bio) > 60:
        bio = bio[:57] + "..."

    opener = match.get("generated_opener") or "暂无话术"
    post_url = match.get("post_url") or "#"

    return (
        msg.MATCH_HEADER.format(index=index, total=total)
        + msg.MATCH_CARD.format(
            nickname=match.get("nickname") or "匿名用户",
            location=match.get("ip_location") or "未知",
            age_tag=match.get("age_tag") or "",
            bio_short=bio,
            match_score=int(match.get("match_score") or 0),
            match_analysis=match.get("match_analysis") or "",
            opener=opener,
            post_url=post_url,
        )
    )


def _match_keyboard(match_id: int) -> InlineKeyboardMarkup:
    """Build inline keyboard for a match card."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👍 感兴趣", callback_data=f"like_{match_id}"),
            InlineKeyboardButton("👎 不感兴趣", callback_data=f"pass_{match_id}"),
            InlineKeyboardButton("🔄 换话术", callback_data=f"regen_{match_id}"),
        ]
    ])
