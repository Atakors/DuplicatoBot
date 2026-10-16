"""Telegram bot wiring: handlers, per-user session state and rendering."""

from __future__ import annotations

import asyncio
import io
import logging
from dataclasses import dataclass, field
from typing import Optional

from PIL import Image, UnidentifiedImageError
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from . import __version__
from .config import Settings
from .imaging import ORIENTATION_AUTO, RenderOptions, build_pattern, describe
from .keyboards import (
    ACTION_CALLBACK,
    ACTION_RENDER,
    ACTION_RESET,
    OPTION_CALLBACK,
    build_keyboard,
    parse_callback,
)

LOGGER = logging.getLogger(__name__)

#: Display name and @handle of the bot as registered with @BotFather.
BOT_NAME = "Duplicayoredz"
BOT_USERNAME = "@Duplicayoredz_bot"

#: Command menu pushed to Telegram on startup.
BOT_COMMANDS = [
    ("start", "Welcome message and the control panel"),
    ("help", "Explain every pattern option"),
    ("settings", "Re-open the control panel for the stored image"),
    ("reset", "Restore default options"),
    ("cancel", "Forget the stored image"),
]

WELCOME = (
    f"*{BOT_NAME}* ({BOT_USERNAME})\n"
    "Send me a photo and I will duplicate it into a 2, 4, 6 or 8 pattern.\n\n"
    "Steps:\n"
    "1. Send a photo (as a photo or a file).\n"
    "2. Pick the pattern, rotation, resize and landscape/portrait mode.\n"
    "3. Tap *Render* to get the result.\n\n"
    "Commands: /start /help /settings /reset /cancel"
)

HELP = (
    f"*{BOT_NAME}* \u2014 how it works\n"
    "\u2022 Pattern: how many copies of your image are placed in the grid "
    "(2, 4, 6 or 8).\n"
    "\u2022 Rotation: rotates the finished collage clockwise by 0, 90, 180 or 270 "
    "degrees.\n"
    "\u2022 Resize: controls the pixel size of the long edge of the output.\n"
    "\u2022 Mode: *Landscape* or *Portrait* letterboxes the collage into a "
    "4:3 or 3:4 frame, *Auto* keeps the pattern's native shape.\n"
    "\u2022 Tiles are centre-cropped squares, so your image is never stretched.\n\n"
    "Use /settings to change the options without re-sending an image."
)


@dataclass
class Session:
    """Per-user state held in ``context.user_data``."""

    count: int = 4
    orientation: str = ORIENTATION_AUTO
    rotation: int = 0
    resize: str = "medium"
    background: str = "FFFFFF"
    source: Optional[Image.Image] = field(default=None, repr=False)
    source_label: str = ""

    def options(self) -> RenderOptions:
        return RenderOptions(
            count=self.count,
            orientation=self.orientation,
            rotation=self.rotation,
            resize=self.resize,
            background=self.background,
        )

    def summary(self) -> str:
        return describe(self.options())


SESSION_KEY = "session"


def get_session(context: ContextTypes.DEFAULT_TYPE) -> Session:
    session = context.user_data.get(SESSION_KEY) if context.user_data is not None else None
    if not isinstance(session, Session):
        session = Session()
        if context.user_data is not None:
            context.user_data[SESSION_KEY] = session
    return session


def _is_allowed(settings: Settings, update: Update) -> bool:
    user = update.effective_user
    return settings.is_user_allowed(user.id if user else None)


async def _deny(update: Update) -> None:
    message = update.effective_message
    if message is not None:
        await message.reply_text("You are not authorised to use this bot.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.application.bot_data["settings"]
    if not _is_allowed(settings, update):
        await _deny(update)
        return

    session = get_session(context)
    await update.effective_message.reply_text(
        WELCOME + "\n\nCurrent settings:\n" + session.summary(),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=build_keyboard(_state(context)),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.application.bot_data["settings"]
    if not _is_allowed(settings, update):
        await _deny(update)
        return
    await update.effective_message.reply_text(HELP, parse_mode=ParseMode.MARKDOWN)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.application.bot_data["settings"]
    if not _is_allowed(settings, update):
        await _deny(update)
        return

    session = get_session(context)
    has_source = "with your last image" if session.source is not None else "after you send a photo"
    await update.effective_message.reply_text(
        session.summary() + f"\n\nChanges apply {has_source}.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=build_keyboard(_state(context)),
    )


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.application.bot_data["settings"]
    if not _is_allowed(settings, update):
        await _deny(update)
        return

    session = get_session(context)
    fresh = Session()
    session.count = fresh.count
    session.orientation = fresh.orientation
    session.rotation = fresh.rotation
    session.resize = fresh.resize
    await update.effective_message.reply_text(
        "Settings reset.\n\n" + session.summary(),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=build_keyboard(_state(context)),
    )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = get_session(context)
    session.source = None
    session.source_label = ""
    await update.effective_message.reply_text("Cleared the stored image. Send a new photo to continue.")


def _state(context: ContextTypes.DEFAULT_TYPE) -> dict:
    session = get_session(context)
    return {
        "count": session.count,
        "rotation": session.rotation,
        "orientation": session.orientation,
        "resize": session.resize,
    }


async def _load_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download whatever the user just sent and store it in the session."""

    message = update.effective_message
    if message is None:
        return

    settings: Settings = context.application.bot_data["settings"]
    if not _is_allowed(settings, update):
        await _deny(update)
        return

    if message.photo:
        attachment = message.photo[-1]
        label = "photo"
    elif message.document is not None:
        attachment = message.document
        label = message.document.file_name or "document"
    else:
        await message.reply_text("Please send an image as a photo or a file.")
        return

    if getattr(attachment, "file_size", None) and attachment.file_size > 20 * 1024 * 1024:
        await message.reply_text("That file is too large. Telegram bots can download up to 20 MB.")
        return

    status = await message.reply_text("Downloading image\u2026")

    try:
        telegram_file = await context.bot.get_file(attachment.file_id)
        payload = await telegram_file.download_as_bytearray()
        image = Image.open(io.BytesIO(bytes(payload)))
        image.load()
    except (UnidentifiedImageError, OSError):
        await status.edit_text("That file is not a supported image. Try a JPG, PNG or WEBP file.")
        return
    except TelegramError as error:
        LOGGER.warning("Download failed: %s", error)
        await status.edit_text("I could not download that file. Please try again.")
        return

    session = get_session(context)
    session.source = image
    session.source_label = label

    await status.edit_text(
        f"Image received ({image.width}\u00d7{image.height}).\n\n"
        + session.summary()
        + "\n\nTap *Render* when you are ready.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=build_keyboard(_state(context)),
    )


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return

    settings: Settings = context.application.bot_data["settings"]
    if not _is_allowed(settings, update):
        await query.answer("You are not authorised to use this bot.", show_alert=True)
        return

    namespace, key, value = parse_callback(query.data or "")
    session = get_session(context)

    if namespace == OPTION_CALLBACK:
        if key == "count" and value.isdigit():
            session.count = int(value)
        elif key == "rotation" and value.isdigit():
            session.rotation = int(value)
        elif key == "orientation":
            session.orientation = value
        elif key == "resize":
            session.resize = value
        else:
            await query.answer("Unsupported option.")
            return

        await query.answer("Updated")
        try:
            await query.edit_message_text(
                _caption_with_hint(session),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=build_keyboard(_state(context)),
            )
        except TelegramError:
            # Message not modified or too old: silently ignore.
            pass
        return

    if namespace == ACTION_CALLBACK:
        if value == ACTION_RESET or key == ACTION_RESET:
            fresh = Session()
            session.count = fresh.count
            session.orientation = fresh.orientation
            session.rotation = fresh.rotation
            session.resize = fresh.resize
            await query.answer("Reset")
            try:
                await query.edit_message_text(
                    _caption_with_hint(session),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=build_keyboard(_state(context)),
                )
            except TelegramError:
                pass
            return

        if value == ACTION_RENDER or key == ACTION_RENDER:
            await _render(update, context, session, query)
            return

    await query.answer()


def _caption_with_hint(session: Session) -> str:
    if session.source is None:
        return "Send a photo to begin.\n\n" + session.summary()
    return session.summary() + "\n\nTap *Render* to generate the pattern."


async def _render(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    session: Session,
    query,
) -> None:
    if session.source is None:
        await query.answer("Send a photo first.", show_alert=True)
        return

    await query.answer("Rendering\u2026")
    chat = update.effective_chat
    if chat is not None:
        try:
            await context.bot.send_chat_action(chat.id, ChatAction.UPLOAD_PHOTO)
        except TelegramError:
            pass

    settings: Settings = context.application.bot_data["settings"]

    try:
        output = await asyncio.to_thread(
            build_pattern,
            session.source.copy(),
            session.options(),
            settings.max_output_edge,
        )
    except Exception:  # pragma: no cover - defensive: never crash the handler
        LOGGER.exception("Rendering failed")
        await query.message.reply_text("Something went wrong while rendering. Please try another image.")
        return

    buffer = io.BytesIO()
    output.save(buffer, format="JPEG", quality=92, optimize=True)
    buffer.seek(0)

    caption = session.summary()
    if chat is not None:
        try:
            await context.bot.send_photo(
                chat_id=chat.id,
                photo=buffer,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        except TelegramError as error:
            LOGGER.warning("send_photo failed, falling back to document: %s", error)

        buffer.seek(0)
        await context.bot.send_document(
            chat_id=chat.id,
            document=buffer,
            filename=f"duplicator_{session.count}x_{session.rotation}deg.jpg",
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
        )


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    LOGGER.error("Unhandled exception", exc_info=context.error)


async def _post_init(application: Application) -> None:
    """Publish the command menu that Telegram shows next to the input box."""

    try:
        from telegram import BotCommand

        await application.bot.set_my_commands(
            [BotCommand(command, description) for command, description in BOT_COMMANDS]
        )
    except TelegramError as error:  # pragma: no cover - non fatal convenience
        LOGGER.warning("Could not register the command menu: %s", error)


def create_application(settings: Settings) -> Application:
    """Build the Telegram application with all handlers registered."""

    if not settings.token:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN is not set. Copy .env.example to .env and add your token."
        )

    application = ApplicationBuilder().token(settings.token).post_init(_post_init).build()
    application.bot_data["settings"] = settings

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler(["help", "h"], help_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CallbackQueryHandler(on_callback))
    application.add_handler(
        MessageHandler(filters.PHOTO | filters.Document.IMAGE, _load_upload)
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, _text_fallback)
    )
    application.add_error_handler(on_error)

    return application


async def _text_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    session = get_session(context)
    if session.source is None:
        await update.effective_message.reply_text(WELCOME, parse_mode=ParseMode.MARKDOWN)
        return
    await update.effective_message.reply_text(
        session.summary() + "\n\nTap *Render*, or send another photo.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=build_keyboard(_state(context)),
    )


def run(settings: Settings) -> None:
    """Start long polling (blocking)."""

    application = create_application(settings)
    LOGGER.info("DuplicatorBot %s starting", __version__)
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )
