import os
import sys
import html
import logging
import traceback
from datetime import datetime

# DEBUG: Check BOT_TOKEN
print(f"DEBUG: BOT_TOKEN is set: {bool(os.environ.get('BOT_TOKEN'))}")
print(f"DEBUG: BOT_TOKEN value: {os.environ.get('BOT_TOKEN', 'NOT SET')[:20]}...")

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    KeyboardButtonRequestChat,
    KeyboardButtonRequestUsers,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler,
)
from telegram.constants import ParseMode

# ─── CONFIG ───────────────────────────────────────────────────────────[...]
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    print("FATAL: BOT_TOKEN environment variable not set.")
    sys.exit(1)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# ─── UTILS ───────────────────────────────────────────────────────────…[...]
def escape(text):
    return html.escape(str(text)) if text is not None else ""


def get_now():
    return datetime.now().strftime("%I:%M %p")


def get_open_chat_button(target_id, username=None):
    if username:
        clean = str(username).replace("@", "")
        return InlineKeyboardButton("↗️ Open Chat", url=f"[t.me](https://t.me/{clean})")

    if not target_id or str(target_id) in ("Hidden", "Privacy Protected", "Not Registered"):
        return None

    try:
        t_id = int(target_id)
        s = str(t_id)
        if s.startswith("-100"):
            clean_id = s.replace("-100", "")
            return InlineKeyboardButton("↗️ Open Chat", url=f"[t.me](https://t.me/c/{clean_id}/1)")
        elif s.startswith("-"):
            return InlineKeyboardButton("↗️ Open Chat", url=f"tg://openmessage?chat_id={t_id}")
        if t_id > 0:
            return InlineKeyboardButton("↗️ Open Chat", url=f"tg://openmessage?user_id={t_id}")
    except (ValueError, TypeError):
        pass
    return None


def find_any_username(data):
    if isinstance(data, dict):
        if data.get("username"):
            return data["username"]
        for v in data.values():
            res = find_any_username(v)
            if res:
                return res
    elif isinstance(data, (list, tuple)):
        for item in data:
            res = find_any_username(item)
            if res:
                return res
    return None


def find_any_id(data):
    if isinstance(data, dict):
        for key in ("user_id", "chat_id", "user_ids", "userId", "chatId"):
            if key in data and data[key]:
                val = data[key]
                return val[0] if isinstance(val, (list, tuple)) else val
        if "users" in data and isinstance(data["users"], list) and data["users"]:
            res = find_any_id(data["users"][0])
            if res:
                return res
        for v in data.values():
            res = find_any_id(v)
            if res:
                return res
    elif isinstance(data, (list, tuple)):
        for item in data:
            res = find_any_id(item)
            if res:
                return res
    return None


# ─── REQUEST BUTTON BUILDERS ─────────────────────────────────────────────────
def build_request_keyboard():
    """Native Telegram request buttons that pop up a chooser."""
    user_btn = KeyboardButton(
        text="👤 User",
        request_users=KeyboardButtonRequestUsers(request_id=4, user_is_bot=False, max_quantity=1),
    )
    premium_btn = KeyboardButton(
        text="🌟 Premium User",
        request_users=KeyboardButtonRequestUsers(
            request_id=5, user_is_bot=False, user_is_premium=True, max_quantity=1
        ),
    )
    bot_btn = KeyboardButton(
        text="🤖 Bot",
        request_users=KeyboardButtonRequestUsers(request_id=3, user_is_bot=True, max_quantity=1),
    )
    group_btn = KeyboardButton(
        text="👥 Group",
        request_chat=KeyboardButtonRequestChat(request_id=2, chat_is_channel=False),
    )
    channel_btn = KeyboardButton(
        text="📢 Channel",
        request_chat=KeyboardButtonRequestChat(request_id=1, chat_is_channel=True),
    )
    contact_btn = KeyboardButton(text="📇 Share Contact", request_contact=True)

    layout = [
        [user_btn, premium_btn],
        [bot_btn, contact_btn],
        [group_btn, channel_btn],
    ]
    return ReplyKeyboardMarkup(layout, resize_keyboard=True)


# ─── HANDLERS ──────────────────────────────────────────────────────────[...]
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user

    welcome_text = (
        f"💠 <b>Elite ID Terminal</b> 💠\n\n"
        f"Hi {escape(user.first_name)}! Select a category below to instantly extract any ID.\n\n"
        f"⚡️ <b>Direct Access Mode:</b> Enabled"
    )

    await update.message.reply_text(
        text="Choose a category 👇",
        reply_markup=build_request_keyboard(),
    )

    main_inline_kb = [
        [InlineKeyboardButton("📊 My Stats", callback_data="my_id_check")],
        [InlineKeyboardButton("🛠 Help", callback_data="help_page")],
    ]
    await update.message.reply_text(
        text=welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(main_inline_kb),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "📖 <b>How to use:</b>\n\n"
        "1️⃣ <b>Buttons:</b> Click any button at the bottom (User, Group, etc.), then select the target. The bot will instantly return the ID.\n\n"
        "2️⃣ <b>Forward:</b> Forward any message from a chat to get its ID.\n\n"
        "3️⃣ <b>Contacts:</b> Share a contact to get their specific User ID."
    )
    inline_kb = [[InlineKeyboardButton("📄 Privacy Policy", url="[telegra.ph](https://telegra.ph/Elite-ID---Privacy-Policy-02-07)")]]
    reply_markup = InlineKeyboardMarkup(inline_kb)

    target = update.callback_query.message if update.callback_query else update.message
    await target.reply_text(help_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)


async def handle_shared_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    target_id = "Hidden"
    target_user = None
    type_str = "Entity"
    type_map = {1: "Channel", 2: "Group", 3: "Bot", 4: "User", 5: "Premium User"}

    try:
        shared = (
            getattr(msg, "users_shared", None)
            or getattr(msg, "chat_shared", None)
            or getattr(msg, "user_shared", None)
        )
        raw_dict = msg.to_dict()

        if hasattr(shared, "users") and shared.users:
            target_id = shared.users[0].user_id
            target_user = getattr(shared.users[0], "username", None)
        elif hasattr(shared, "user_id"):
            target_id = shared.user_id
        elif hasattr(shared, "chat_id"):
            target_id = shared.chat_id
            target_user = getattr(shared, "username", None)

        if target_id == "Hidden":
            target_id = find_any_id(raw_dict) or "Hidden"
        if not target_user:
            target_user = find_any_username(raw_dict)

        if shared:
            type_str = type_map.get(getattr(shared, "request_id", 0), "Entity")

        if target_id == "Hidden":
            raise ValueError("ID not found in update.")

        profile_link = f'<a href="tg://openmessage?user_id={target_id}">Profile Link</a>'
        if str(target_id).startswith("-100"):
            clean_id = str(target_id).replace("-100", "")
            profile_link = f'<a href="[t.me](https://t.me/c/{clean_id}/1)">Chat Link</a>'
        elif str(target_id).startswith("-"):
            profile_link = "<i>Group/Channel (No direct deep link possible)</i>"

        res_with_link = (
            f"✅ <b>Request Successful</b>\n\n"
            f"💠 <b>Category:</b> {type_str}\n"
            f"🆔 <b>Target ID:</b> <code>{target_id}</code>\n"
            f"🔗 <b>Link:</b> {profile_link}\n"
            f"🕒 <b>Sync:</b> {get_now()}"
        )
        if target_user:
            res_with_link += f"\n👤 <b>User:</b> @{target_user}"

        res_no_link = (
            f"✅ <b>Request Successful</b>\n\n"
            f"💠 <b>Category:</b> {type_str}\n"
            f"🆔 <b>Target ID:</b> <code>{target_id}</code>\n"
            f"🕒 <b>Sync:</b> {get_now()}"
        )
        if target_user:
            res_no_link += f"\n👤 <b>User:</b> @{target_user}"

        btns = [[InlineKeyboardButton("📋 Copy ID", callback_data=f"copy_{target_id}")]]
        open_btn = get_open_chat_button(target_id, target_user)
        if open_btn:
            btns.append([open_btn])

        try:
            await msg.reply_text(
                res_with_link,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(btns),
                disable_web_page_preview=True,
            )
        except Exception as send_err:
            logger.warning(f"Failed to send with link: {send_err}. Falling back.")
            await msg.reply_text(
                res_no_link,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[btns[0][0]]]),
            )

    except Exception as e:
        logger.error(f"FATAL EXTRACTION: {e}")
        logger.error(traceback.format_exc())
        await msg.reply_text(
            f"❌ <b>Error:</b> ID extraction failed.\n\n<code>{escape(str(e))[:200]}</code>",
            parse_mode=ParseMode.HTML,
        )


async def handle_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if not msg:
        return

    logger.info(f"RECVD update id: {update.update_id}")

    if getattr(msg, "users_shared", None) or getattr(msg, "chat_shared", None):
        await handle_shared_content(update, context)
        return

    is_forward = (
        getattr(msg, "forward_origin", None)
        or getattr(msg, "forward_from", None)
        or getattr(msg, "forward_from_chat", None)
        or getattr(msg, "forward_sender_name", None)
    )
    if is_forward:
        await process_extraction(update)
        return

    if msg.contact:
        await process_contact_extraction(update)
        return

    if msg.text and not msg.text.startswith("/"):
        await msg.reply_text(
            "✨ <i>Select a category below or forward a message.</i>",
            parse_mode=ParseMode.HTML,
        )


async def process_extraction(update: Update):
    msg = update.message
    title = "Unknown"
    target_id = "Hidden"
    type_str = "Forwarded Source"
    username = None

    try:
        origin = getattr(msg, "forward_origin", None)

        # PTB v20+ forward_origin path
        if origin is not None:
            otype = getattr(origin, "type", "")
            if otype == "user":
                user = origin.sender_user
                title = user.full_name
                target_id = user.id
                username = user.username
                type_str = "Robot 🤖" if user.is_bot else "User 👤"
            elif otype == "hidden_user":
                title = origin.sender_user_name
                type_str = "User (Hidden 🔒)"
                target_id = "Privacy Protected"
            elif otype == "chat":
                chat = origin.sender_chat
                title = chat.title or chat.username or "Private Chat"
                target_id = chat.id
                username = chat.username
                type_str = chat.type.capitalize()
            elif otype == "channel":
                chat = origin.chat
                title = chat.title or chat.username or "Channel"
                target_id = chat.id
                username = chat.username
                type_str = "Channel"
        # Legacy fallback
        elif msg.forward_from:
            user = msg.forward_from
            title = user.full_name
            target_id = user.id
            username = user.username
            type_str = "Robot 🤖" if user.is_bot else "User 👤"
        elif msg.forward_from_chat:
            chat = msg.forward_from_chat
            title = chat.title or chat.username or "Private Chat"
            target_id = chat.id
            username = chat.username
            type_str = chat.type.capitalize()
        elif msg.forward_sender_name:
            title = msg.forward_sender_name
            type_str = "User (Hidden 🔒)"
            target_id = "Privacy Protected"

        res = (
            f"🔍 <b>Extraction Result</b>\n\n"
            f"📛 <b>Name:</b> {escape(title)}\n"
            f"🆔 <b>ID:</b> <code>{target_id}</code>\n"
            f"📂 <b>Category:</b> {type_str}"
        )
        if username:
            res += f"\n👤 <b>Username:</b> @{escape(username)}"

        btns = []
        if isinstance(target_id, int):
            btns.append([InlineKeyboardButton("📋 Copy ID", callback_data=f"copy_{target_id}")])
            open_btn = get_open_chat_button(target_id, username)
            if open_btn:
                btns.append([open_btn])

        await msg.reply_text(
            res,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(btns) if btns else None,
        )
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        logger.error(traceback.format_exc())
        await msg.reply_text(
            f"❌ <b>Error:</b> {escape(str(e))[:200]}",
            parse_mode=ParseMode.HTML,
        )


async def process_contact_extraction(update: Update):
    contact = update.message.contact
    name = f"{contact.first_name} {contact.last_name or ''}".strip()
    c_id = contact.user_id if contact.user_id else "Not Registered"

    res = (
        f"📇 <b>Contact Information</b>\n\n"
        f"👤 <b>Name:</b> {escape(name)}\n"
        f"🆔 <b>User ID:</b> <code>{c_id}</code>\n"
        f"📞 <b>Phone:</b> <code>{escape(contact.phone_number)}</code>"
    )

    btns = [[InlineKeyboardButton("📋 Copy ID", callback_data=f"copy_{c_id}")]]
    if isinstance(c_id, int):
        open_btn = get_open_chat_button(c_id)
        if open_btn:
            btns.append([open_btn])

    await update.message.reply_text(
        res, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btns)
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    res = (
        f"📊 <b>Your Statistics</b>\n\n"
        f"👤 <b>Name:</b> {escape(user.full_name)}\n"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
        f"🌟 <b>Premium:</b> {'Yes' if user.is_premium else 'No'}\n"
        f"🕒 <b>Sync Time:</b> {get_now()}"
    )
    await update.message.reply_text(res, parse_mode=ParseMode.HTML)


async def callback_gate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == "help_page":
        await help_command(update, context)
    elif data == "my_id_check":
        user = update.effective_user
        res = (
            f"📊 <b>Your Statistics</b>\n\n"
            f"👤 <b>Name:</b> {escape(user.full_name)}\n"
            f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
            f"🕒 <b>Sync:</b> {get_now()}"
        )
        await query.message.reply_text(res, parse_mode=ParseMode.HTML)
    elif data.startswith("copy_"):
        val = data.replace("copy_", "")
        await query.message.reply_text(f"✅ <code>{val}</code>", parse_mode=ParseMode.HTML)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling update:", exc_info=context.error)
    tb = "".join(traceback.format_exception(None, context.error, context.error.__traceback__))
    logger.error(tb)


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))

    # Use safer filter combination compatible with PTB 20+
    shared_filter = filters.StatusUpdate.USERS_SHARED | filters.StatusUpdate.CHAT_SHARED

    app.add_handler(
        MessageHandler(
            filters.FORWARDED
            | filters.CONTACT
            | shared_filter
            | (filters.TEXT & ~filters.COMMAND),
            handle_update,
        )
    )

    app.add_handler(CallbackQueryHandler(callback_gate))
    app.add_error_handler(error_handler)

    print("--- Elite ID Bot Started ---")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
