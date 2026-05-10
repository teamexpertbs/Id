import sys
import subprocess
import shutil

def install_dependencies():
    """Check and install missing or incorrect dependencies."""
    required_package = "python-telegram-bot>=20.0"
    
    # Check if correct version/package is installed
    try:
        from telegram import KeyboardButtonRequestUsers
        # If we reach here, the correct package is likely installed
        return
    except (ImportError, AttributeError):
        print("--- Updating dependencies for compatibility... ---")
        
    print(f"--- Installing {required_package}... Please wait. ---")
    try:
        # 1. First, uninstall the legacy 'telegram' package if it exists (common conflict)
        subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "telegram"], stderr=subprocess.DEVNULL)
        
        # 2. Install/Upgrade python-telegram-bot
        subprocess.check_call([sys.executable, "-m", "pip", "install", required_package])
        print("--- Installation successful! ---")
        
        # 3. Force restart of the script to use new packages
        print("--- Restarting script... ---")
        os.execv(sys.executable, ['python'] + sys.argv)
    except Exception as e:
        print(f"--- Fatal Error: Could not install dependencies automatically. ---")
        print(f"--- Error details: {e} ---")
        print(f"--- Please run: pip install {required_package} ---")
        sys.exit(1)

# Run installation before imports
import os
install_dependencies()


import logging

import html
import traceback
from datetime import datetime
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    KeyboardButtonRequestChat, 
    KeyboardButtonRequestUsers
)
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from telegram.constants import ParseMode

# --- CONFIGURATION ---
BOT_TOKEN = "8272652146:AAG449XogIJfKQmRq_ty9t16CY2zsT6fu-A"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- UTILS ---
def escape(text):
    return html.escape(str(text)) if text else ""

def get_now():
    return datetime.now().strftime("%I:%M %p")

def get_open_chat_button(target_id, username=None):
    """Generate an 'Open Chat' button based on the ID type or username."""
    if username:
        return InlineKeyboardButton("↗️ Open Chat", url=f"https://t.me/{username.replace('@', '')}")
        
    if not target_id or str(target_id) == "Hidden":
        return None
        
    try:
        t_id = int(target_id)
        # Channels and Groups with -100 prefix
        if str(t_id).startswith("-100"):
            clean_id = str(t_id).replace("-100", "")
            return InlineKeyboardButton("↗️ Open Chat", url=f"https://t.me/c/{clean_id}/1")
        # Standard Groups
        elif str(t_id).startswith("-"):
            return InlineKeyboardButton("↗️ Open Chat", url=f"tg://openmessage?chat_id={t_id}")
        
        # Use tg://openmessage?user_id= for users without usernames
        if t_id > 0:
            return InlineKeyboardButton("↗️ Open Chat", url=f"tg://openmessage?user_id={t_id}")
            
        return None
    except:
        return None

def find_any_username(data):
    """Deep search for any username field."""
    if isinstance(data, dict):
        if 'username' in data and data['username']:
            return data['username']
        for v in data.values():
            res = find_any_username(v)
            if res: return res
    elif isinstance(data, (list, tuple)):
        for item in data:
            res = find_any_username(item)
            if res: return res
    return None

def find_any_id(data):
    """Deep search for anything that looks like a User or Chat ID."""
    if isinstance(data, dict):
        # Priority keys
        for key in ['user_id', 'chat_id', 'user_ids', 'userId', 'chatId']:
            if key in data and data[key]:
                val = data[key]
                return val[0] if isinstance(val, (list, tuple)) else val
        
        # In case it's inside 'users' list
        if 'users' in data and isinstance(data['users'], list) and data['users']:
            res = find_any_id(data['users'][0])
            if res: return res

        # Recursive search for other keys
        for v in data.values():
            res = find_any_id(v)
            if res: return res
            
    elif isinstance(data, (list, tuple)):
        for item in data:
            res = find_any_id(item)
            if res: return res
    return None

# --- CORE HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message and unique request buttons."""
    user = update.effective_user
    
    welcome_text = (
        f"💠 <b>Elite ID Terminal</b> 💠\n\n"
        f"Hi {escape(user.first_name)}! Select a category below to instantly extract any ID.\n\n"
        f"⚡️ <b>Direct Access Mode:</b> Enabled"
    )

    # Inline buttons for extra info
    inline_kb = [
        [InlineKeyboardButton("📊 My Stats", callback_data="my_id_check")],
        [InlineKeyboardButton("🛠 Help", callback_data="help_page")]
    ]
    
    # Reply keyboard as per the screenshot
    reply_kb = [
        [
            KeyboardButton("Channel", request_chat=KeyboardButtonRequestChat(request_id=1, chat_is_channel=True)),
            KeyboardButton("Group", request_chat=KeyboardButtonRequestChat(request_id=2, chat_is_channel=False))
        ],
        [
            KeyboardButton("Bot", request_users=KeyboardButtonRequestUsers(request_id=3, user_is_bot=True, max_quantity=1, request_username=True)),
            KeyboardButton("User", request_users=KeyboardButtonRequestUsers(request_id=4, user_is_bot=False, max_quantity=1, request_username=True))
        ],
        [
            KeyboardButton("Premium Users", request_users=KeyboardButtonRequestUsers(request_id=5, user_is_premium=True, max_quantity=1, request_username=True))
        ]
    ]

    await update.message.reply_text(
        text=welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardMarkup(reply_kb, resize_keyboard=True, is_persistent=True)
    )
    
    await update.message.reply_text(
        text="<i>Aap categories use karein ya koi message forward karein!</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_kb)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "📖 <b>How to use:</b>\n\n"
        "1️⃣ <b>Buttons:</b> Click any button at the bottom (User, Group, etc.), then select the target. The bot will instantly return the ID.\n\n"
        "2️⃣ <b>Forward:</b> Forward any message from a chat to get its ID.\n\n"
        "3️⃣ <b>Contacts:</b> Share a contact to get their specific User ID."
    )
    
    # Privacy Policy Button
    inline_kb = [[InlineKeyboardButton("📄 Privacy Policy", url="https://telegra.ph/Elite-ID---Privacy-Policy-02-07")]]
    reply_markup = InlineKeyboardMarkup(inline_kb)

    if update.callback_query:
        await update.callback_query.message.reply_text(
            help_text, 
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            help_text, 
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

async def handle_shared_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Robust Shared Content Handler with detailed debugging."""
    msg = update.message
    target_id = "Hidden"
    target_user = None
    type_str = "Entity"
    type_map = {1: "Channel", 2: "Group", 3: "Bot", 4: "User", 5: "Premium User"}

    try:
        # Detect Shared Object
        shared = msg.users_shared or msg.chat_shared or getattr(msg, 'user_shared', None)
        raw_dict = msg.to_dict()

        # 1. Direct Attribute Check (Priority)
        if hasattr(shared, 'users') and shared.users:
            target_id = shared.users[0].user_id
            target_user = getattr(shared.users[0], 'username', None)
        elif hasattr(shared, 'user_id'):
            target_id = shared.user_id
        elif hasattr(shared, 'chat_id'):
            target_id = shared.chat_id
            target_user = getattr(shared, 'username', None) # Inline username if requested
        
        # 2. Recursive Search (Failsafe)
        if target_id == "Hidden":
            target_id = find_any_id(raw_dict) or "Hidden"
        if not target_user:
            target_user = find_any_username(raw_dict)
        
        # 3. Request Category
        if shared:
            type_str = type_map.get(getattr(shared, 'request_id', 0), "Entity")

        if target_id == "Hidden":
            raise Exception("ID not found in update.")

        # link generation logic
        profile_link = f"<a href=\"tg://openmessage?user_id={target_id}\">Profile Link</a>"
        if str(target_id).startswith("-100"):
            clean_id = str(target_id).replace("-100", "")
            profile_link = f"<a href=\"https://t.me/c/{clean_id}/1\">Chat Link</a>"
        elif str(target_id).startswith("-"):
            profile_link = f"<i>Group/Channel (No direct deep link possible)</i>"

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
        if open_btn: btns.append([open_btn])
        
        # FAILSAFE SENDING: Try with link, then without
        try:
            await msg.reply_text(res_with_link, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btns))
        except Exception as send_err:
            logger.warning(f"Failed to send with link: {send_err}. Falling back to plain text.")
            await msg.reply_text(res_no_link, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup([[btns[0][0]]]))

    except Exception as e:
        logger.error(f"FATAL EXTRACTION: {e}")
        logger.error(traceback.format_exc())
        error_msg = f"❌ <b>Error:</b> ID extraction failed.\n\n<code>{escape(str(e))[:200]}</code>"
        await msg.reply_text(error_msg, parse_mode=ParseMode.HTML)

async def handle_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Primary handler for all messages."""
    msg = update.message
    if not msg: return

    # NUCLEAR LOGGING: Print full update to terminal
    logger.info(f"RECVD: {update.to_json()}")

    # Check for Shared Content first (from buttons)
    if msg.users_shared or msg.chat_shared:
        logger.info("Shared content detected in handle_update")
        await handle_shared_content(update, context)
        return

    # Forwarded Logic
    if any([msg.forward_from, msg.forward_from_chat, msg.forward_sender_name]):
        await process_extraction(update)
    
    # Contact Logic
    elif msg.contact:
        await process_contact_extraction(update)
    
    # Simple Text
    elif msg.text and not msg.text.startswith('/'):
        await msg.reply_text("✨ <i>Select a category below or forward a message.</i>", parse_mode=ParseMode.HTML)

async def process_extraction(update: Update):
    msg = update.message
    title = "Unknown"
    target_id = "Hidden"
    type_str = "Forwarded Source"
    
    try:
        if msg.forward_from:
            user = msg.forward_from
            title = user.full_name
            target_id = user.id
            type_str = "Robot 🤖" if user.is_bot else "User 👤"
        elif msg.forward_from_chat:
            chat = msg.forward_from_chat
            title = chat.title or chat.username or "Private Chat"
            target_id = chat.id
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
        
        btns = []
        if isinstance(target_id, int):
            btns.append([InlineKeyboardButton("📋 Copy ID", callback_data=f"copy_{target_id}")])
            open_btn = get_open_chat_button(target_id)
            if open_btn:
                btns.append([open_btn])
            
        await msg.reply_text(res, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btns) if btns else None)
    except Exception as e:
        logger.error(f"Error: {e}")

async def process_contact_extraction(update: Update):
    contact = update.message.contact
    name = f"{contact.first_name} {contact.last_name or ''}".strip()
    c_id = contact.user_id or "Not Registered"
    
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
            
    await update.message.reply_text(res, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btns))

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user statistics and ID."""
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

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    
    # Master handler for IDs (Forwards, Contacts, Shared Buttons)
    app.add_handler(MessageHandler(
        filters.FORWARDED | filters.CONTACT | filters.StatusUpdate.USERS_SHARED | filters.StatusUpdate.CHAT_SHARED | (filters.TEXT & ~filters.COMMAND),
        handle_update
    ))
    
    app.add_handler(CallbackQueryHandler(callback_gate))

    print(f"--- Elite ID Bot with Request Buttons Started ---")
    app.run_polling()

if __name__ == "__main__":
    main()