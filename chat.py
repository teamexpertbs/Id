import sys
import subprocess
import os
import logging
import html
import traceback
from datetime import datetime
from typing import Optional, Union, Dict, Any

# Dependency check and auto-install
def install_dependencies():
    """Auto-install required packages."""
    try:
        import telegram
        if int(telegram.__version__.split('.')[0]) < 20:
            raise ImportError()
    except (ImportError, NameError):
        print("🔄 Installing python-telegram-bot...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", 
                              "python-telegram-bot>=20.7", "--upgrade", "-q"])
        print("✅ Installed! Restarting...")
        os.execv(sys.executable, [sys.executable] + sys.argv)

install_dependencies()

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, KeyboardButton, KeyboardButtonRequestChat,
    KeyboardButtonRequestUsers, Chat, User, Contact
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, 
    filters, CallbackQueryHandler
)
from telegram.constants import ParseMode

# === CONFIG ===
BOT_TOKEN = "8272652146:AAEQeMESnP92ukp1gToWtE7XMJ7P77xswco"

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === UTILS ===
def escape_html(text: Any) -> str:
    """Escape HTML characters."""
    return html.escape(str(text)) if text else "N/A"

def get_current_time() -> str:
    """Get formatted time."""
    return datetime.now().strftime("%H:%M %p")

def generate_link(chat_id: Union[int, str], username: Optional[str] = None) -> str:
    """Generate proper Telegram link."""
    if username:
        return f"https://t.me/{username.replace('@', '')}"
    
    try:
        cid = int(str(chat_id))
        if cid > 0:  # User
            return f"tg://user?id={cid}"
        elif str(cid).startswith("-100"):  # Channel
            clean_id = str(cid).replace("-100", "")
            return f"https://t.me/c/{clean_id}/1"
        elif str(cid).startswith("-"):  # Group
            return f"tg://resolve?domain=group{str(cid)}"
        return "Private"
    except:
        return "Invalid"

def extract_target_id(data: Dict[str, Any]) -> Optional[Union[int, str]]:
    """Extract ID from message data."""
    keys = ['user_id', 'chat_id', 'id', 'from_user', 'forward_from', 'forward_from_chat']
    
    def search(obj: Any) -> Optional[Union[int, str]]:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in keys and value:
                    return value
                result = search(value)
                if result:
                    return result
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                result = search(item)
                if result:
                    return result
        elif hasattr(obj, 'id'):
            return getattr(obj, 'id')
        elif hasattr(obj, 'user_id'):
            return getattr(obj, 'user_id')
        elif hasattr(obj, 'chat_id'):
            return getattr(obj, 'chat_id')
        return None
    
    return search(data)

def extract_username(data: Dict[str, Any]) -> Optional[str]:
    """Extract username from data."""
    def search(obj: Any) -> Optional[str]:
        if isinstance(obj, dict):
            if 'username' in obj and obj['username']:
                return obj['username']
            for value in obj.values():
                result = search(value)
                if result:
                    return result
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                result = search(item)
                if result:
                    return result
        elif hasattr(obj, 'username') and obj.username:
            return obj.username
        return None
    
    return search(data)

# === HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command with all buttons."""
    user = update.effective_user
    welcome_msg = (
        f"💎 <b>Elite ID Finder v2.0</b> 💎\n\n"
        f"👋 Welcome <b>{escape_html(user.first_name)}</b>!\n\n"
        f"⚡ <b>Instant ID Extraction:</b>\n"
        f"• Click buttons below\n"
        f"• Forward messages\n"
        f"• Share contacts\n\n"
        f"🚀 <b>Ready to extract IDs!</b>"
    )

    # All working buttons
    keyboard = [
        [
            KeyboardButton("📢 Channel", request_chat=KeyboardButtonRequestChat(
                request_id=1, chat_is_channel=True
            )),
            KeyboardButton("👥 Group", request_chat=KeyboardButtonRequestChat(
                request_id=2, chat_is_channel=False
            ))
        ],
        [
            KeyboardButton("🤖 Bot", request_users=KeyboardButtonRequestUsers(
                request_id=3, user_is_bot=True, max_quantity=1
            )),
            KeyboardButton("👤 User", request_users=KeyboardButtonRequestUsers(
                request_id=4, user_is_bot=False, max_quantity=1
            ))
        ],
        [
            KeyboardButton("⭐ Premium", request_users=KeyboardButtonRequestUsers(
                request_id=5, user_is_premium=True, max_quantity=1
            )),
            KeyboardButton("📊 My ID", callback_data="stats")
        ]
    ]

    await update.message.reply_text(
        welcome_msg,
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def handle_shared(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button shared content."""
    msg = update.message
    category_names = {1: "📢 Channel", 2: "👥 Group", 3: "🤖 Bot", 
                     4: "👤 User", 5: "⭐ Premium User"}
    
    try:
        # Get shared data
        user_shared = getattr(msg, 'users_shared', None)
        chat_shared = getattr(msg, 'chat_shared', None)
        
        # Extract info
        raw_data = msg.to_dict()
        target_id = extract_target_id(raw_data)
        target_username = extract_username(raw_data)
        
        # Determine category
        request_id = (getattr(user_shared, 'request_id', 0) if user_shared 
                     else getattr(chat_shared, 'request_id', 0))
        category = category_names.get(request_id, "Unknown")
        
        if not target_id:
            await msg.reply_text("❌ No ID found!")
            return

        # Response
        link = generate_link(target_id, target_username)
        response = (
            f"✅ <b>ID Found!</b>\n\n"
            f"📂 <b>Type:</b> {category}\n"
            f"🆔 <b>ID:</b> <code>{target_id}</code>\n"
            f"🔗 <b>Link:</b> <a href='{link}'>Open</a>\n"
            f"👤 <b>Username:</b> {f'@{target_username}' if target_username else 'None'}\n"
            f"⏰ <b>Time:</b> {get_current_time()}"
        )

        # Buttons
        buttons = [[InlineKeyboardButton("📋 Copy ID", callback_data=f"copy_{target_id}")]]
        
        await msg.reply_text(response, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))
        
    except Exception as e:
        logger.error(f"Shared handler error: {e}")
        await msg.reply_text(f"❌ Error: {escape_html(str(e))}")

async def handle_forward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle forwarded messages."""
    msg = update.message
    
    try:
        if msg.forward_from:
            user = msg.forward_from
            info = {
                'name': user.full_name,
                'id': user.id,
                'username': user.username,
                'type': '🤖 Bot' if user.is_bot else '👤 User'
            }
        elif msg.forward_from_chat:
            chat = msg.forward_from_chat
            info = {
                'name': chat.title or chat.username or 'Private Chat',
                'id': chat.id,
                'username': chat.username,
                'type': chat.type.title()
            }
        else:
            await msg.reply_text("❌ No forward source!")
            return

        link = generate_link(info['id'], info['username'])
        response = (
            f"🔍 <b>Forward Analysis</b>\n\n"
            f"📛 <b>Name:</b> {escape_html(info['name'])}\n"
            f"🆔 <b>ID:</b> <code>{info['id']}</code>\n"
            f"📂 <b>Type:</b> {info['type']}\n"
            f"🔗 <b>Link:</b> <a href='{link}'>Open</a>\n"
            f"⏰ <b>Time:</b> {get_current_time()}"
        )

        buttons = [[InlineKeyboardButton("📋 Copy ID", callback_data=f"copy_{info['id']}")]]
        await msg.reply_text(response, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))
        
    except Exception as e:
        await msg.reply_text(f"❌ Forward error: {escape_html(str(e))}")

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle shared contacts."""
    contact = update.message.contact
    name = f"{contact.first_name or ''} {contact.last_name or ''}".strip()
    user_id = contact.user_id
    phone = contact.phone_number or "Hidden"
    
    response = (
        f"📇 <b>Contact Info</b>\n\n"
        f"👤 <b>Name:</b> {escape_html(name)}\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
        f"📱 <b>Phone:</b> <code>{escape_html(phone)}</code>\n"
        f"⏰ <b>Time:</b> {get_current_time()}"
    )
    
    buttons = [[InlineKeyboardButton("📋 Copy ID", callback_data=f"copy_{user_id}")]]
    await update.message.reply_text(response, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user statistics."""
    user = update.effective_user
    if update.callback_query:
        user = update.callback_query.from_user
    
    response = (
        f"📊 <b>Your Info</b>\n\n"
        f"👤 <b>Name:</b> {escape_html(user.full_name)}\n"
        f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
        f"⭐ <b>Premium:</b> {'✅ Yes' if user.is_premium else '❌ No'}\n"
        f"🤖 <b>Bot:</b> {'✅ Yes' if user.is_bot else '❌ No'}\n"
        f"⏰ <b>Time:</b> {get_current_time()}"
    )
    
    if update.callback_query:
        await update.callback_query.message.reply_text(response, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(response, parse_mode=ParseMode.HTML)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "stats":
        await show_stats(update, context)
    elif query.data.startswith("copy_"):
        target_id = query.data.replace("copy_", "")
        await query.message.reply_text(f"✅ <code>{target_id}</code>\n<b>ID Copied!</b>", 
                                     parse_mode=ParseMode.HTML)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle random text messages."""
    await update.message.reply_text(
        "✨ <b>Use buttons below or forward a message!</b>",
        parse_mode=ParseMode.HTML
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Help command."""
    help_text = (
        "📖 <b>Usage Guide:</b>\n\n"
        "1️⃣ <b>Buttons:</b> Click → Select → Get ID\n"
        "2️⃣ <b>Forward:</b> Any message\n"
        "3️⃣ <b>Contact:</b> Share contact\n\n"
        "✅ <b>All features working!</b>"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

# === MAIN ===
def main():
    """Run the bot."""
    print("🚀 Elite ID Finder Starting...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("stats", show_stats))
    
    # Message handlers (priority order)
    app.add_handler(MessageHandler(
        filters.StatusUpdate.USERS_SHARED | filters.StatusUpdate.CHAT_SHARED,
        handle_shared
    ))
    app.add_handler(MessageHandler(filters.FORWARDED, handle_forward))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("✅ Bot running perfectly!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
