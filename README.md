# Elite ID Telegram Bot

Telegram bot for extracting and displaying user IDs from various Telegram entities.

## Setup

### 1. Environment Variables
Create a `.env` file (copy from `.env.example`):
```
BOT_TOKEN=your_actual_bot_token_here
```

### 2. Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Bot
```bash
python chatt.py
```

### 4. Deploy on Render/Heroku/Railway
Set the `BOT_TOKEN` environment variable in your hosting platform's settings.

## Features
- 👤 Extract user IDs
- 🤖 Bot identification
- 📢 Channel/Group ID extraction
- 📇 Contact information retrieval
- 🔗 Deep linking to chats

## Security
- **Never commit your BOT_TOKEN** to the repository
- Always use environment variables for sensitive data
- The `.env` file should be in `.gitignore`
