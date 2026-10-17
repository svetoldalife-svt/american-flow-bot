import logging, json, os
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import BOT_TOKEN, CHANNELS, ADMIN_ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

IMAGE_PATH = "money_talks.jpg"
MIRO_LINK = "https://miro.com/app/board/uXjVEaRaVZ0=/?share_link_id=926291280845"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user.id, user.first_name, user.username)

    channels_text = "\n".join(
        [f"  {i+1}. <a href='{ch['link']}'>{ch['link']}</a>"
         for i, ch in enumerate(CHANNELS)]
    )

    text = (
        f"💰 <b>Отримайте безкоштовний пак уроків</b>\n"
        f"<b>MONEY TALKS | Career English</b>\n\n"
        f"📅 Уроки надійдуть <b>26 жовтня</b>\n\n"
        f"Підпишіться на всіх 7 авторів:\n\n"
        f"{channels_text}\n\n"
        f"Натисни <b>Готово ☑️</b> та я перевірю твої підписки 🤖"
    )

    keyboard = [[InlineKeyboardButton("Готово ☑️", callback_data="check_sub")]]

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
    save_user(user.id, user.first_name, user.username)
    mark_subscribed(user.id)

    try:
        await query.message.reply_text(
            text=(
                "🎉 Дякую за підписку!\n\n"
                "💸 Я повернусь з вашими матеріалами <b>26 жовтня</b>!\n\n"
                "Залишайся на зв'язку 🤖✨"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Помилка відповіді: {e}")

async def send_miro(context):
    subscribers = load_subscribers()
    sent, failed = 0, 0
    for uid in subscribers:
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=(
                    f"🎁 <b>Ваші матеріали MONEY TALKS вже тут!</b> 💰\n\n"
                    f"📚 Відкривай дошку Miro з усіма уроками:\n"
                    f"{MIRO_LINK}\n\n"
                    f"Гарного навчання! 🚀🤖"
                ),
                parse_mode="HTML"
            )
            sent += 1
        except:
            failed += 1
    logger.info(f"Автоматична розсилка: надіслано {sent}, помилок {failed}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Використання: /broadcast Текст")
        return
    message_text = " ".join(context.args)
    subscribers = load_subscribers()
    await update.message.reply_text(f"⏳ Розсилаю для {len(subscribers)} учасників...")
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
        f"✅ Натиснули Готово: <b>{len(load_subscribers())}</b>",
        parse_mode="HTML"
    )

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

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_subscription, pattern="^check_sub$"))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("stats", stats))

    kyiv_tz = timezone(timedelta(hours=3))
    send_time = datetime(2026, 10, 26, 17, 0, 0, tzinfo=kyiv_tz)
    app.job_queue.run_once(send_miro, when=send_time)

    logger.info("✅ Бот запущено!")
    app.run_polling()

if __name__ == "__main__":
    main()
