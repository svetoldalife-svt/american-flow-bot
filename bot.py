import logging, json, os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import BOT_TOKEN, CHANNELS, ADMIN_ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

IMAGE_PATH = "11image.jpg"
MIRO_LINK = "https://miro.com/app/board/uXjVHTRkXwU=/"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user.id, user.first_name, user.username)

    channels_text = "\n".join(
        [f"👉 <a href='{ch['link']}'>{ch['link']}</a>" for ch in CHANNELS]
    )

    text = (
        f"🎁 <b>БЕЗКОШТОВНА РОЗСИЛКА</b>\n\n"
        f"Підпишись на канал:\n\n"
        f"{channels_text}\n\n"
        f"Після підписки натисни кнопку нижче 👇"
    )

    keyboard = [[InlineKeyboardButton("✅ Готово!", callback_data="check_sub")]]

    with open(IMAGE_PATH, "rb") as photo:
        await update.message.reply_photo(
            photo=photo,
            caption=text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    # Перевіряємо підписку на кожен канал
    not_subscribed = []
    for ch in CHANNELS:
        try:
            username = ch["link"].replace("https://t.me/", "@")
            member = await context.bot.get_chat_member(chat_id=username, user_id=user.id)
            if member.status in [ChatMember.LEFT, ChatMember.BANNED]:
                not_subscribed.append(ch)
        except Exception as e:
            logger.warning(f"Помилка перевірки {ch['name']}: {e}")

    if not_subscribed:
        # Людина не підписана — показуємо на які канали ще треба
        channels_text = "\n".join(
            [f"❌ <a href='{ch['link']}'>{ch['link']}</a>" for ch in not_subscribed]
        )
        keyboard = [[InlineKeyboardButton("🔄 Перевірити ще раз", callback_data="check_sub")]]
        await query.edit_message_caption(
            caption=(
                f"😔 Ти ще не підписана на:\n\n"
                f"{channels_text}\n\n"
                f"Підпишись і натисни кнопку нижче 👇"
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # Все добре — людина підписана!
        mark_subscribed(user.id)
        await context.bot.send_message(
            chat_id=user.id,
            text=(
                f"🎉 Чудово, підписка підтверджена!\n\n"
                f"Тримай свій безкоштовний урок 🎓\n\n"
                f"👇 Відкрий дошку Miro:\n"
                f"{MIRO_LINK}"
            )
        )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Використання: /broadcast Текст")
        return
    message_text = " ".join(context.args)
    subscribers = load_subscribers()
    sent, failed = 0, 0
    for uid in subscribers:
        try:
            await context.bot.send_message(chat_id=int(uid), text=message_text, parse_mode="HTML")
            sent += 1
        except:
            failed += 1
    await update.message.reply_text(f"✅ Надіслано: {sent}, помилок: {failed}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(
        f"📊 Запустили бот: <b>{len(load_all_users())}</b>\n"
        f"✅ Підтвердили підписку: <b>{len(load_subscribers())}</b>",
        parse_mode="HTML"
    )

# ─── База ─────────────────────────────────────────────────────────────────────

USERS_FILE = "users.json"

def load_db():
    if not os.path.exists(USERS_FILE): return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f: return json.load(f)

def save_db(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

def save_user(user_id, first_name, username):
    db = load_db()
    uid = str(user_id)
    if uid not in db:
        db[uid] = {"first_name": first_name, "username": username or "", "subscribed": False, "joined_at": datetime.now().isoformat()}
        save_db(db)

def mark_subscribed(user_id):
    db = load_db()
    uid = str(user_id)
    if uid in db:
        db[uid]["subscribed"] = True
        save_db(db)

def load_subscribers(): return [uid for uid, d in load_db().items() if d.get("subscribed")]
def load_all_users(): return load_db()

# ─── Запуск ───────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_subscription, pattern="^check_sub$"))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("stats", stats))
    logger.info("✅ Бот запущено!")
    app.run_polling()

if __name__ == "__main__":
    main()
