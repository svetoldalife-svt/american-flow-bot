import logging, json, os
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import BOT_TOKEN, CHANNELS, ADMIN_ID
 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
IMAGE_PATH = "grammar_collage.jpg"
MIRO_LINK = "https://miro.com/app/board/uXjVEQ6tfM8=/?share_link_id=10124994743"
 
async def start(update, context):
    user = update.effective_user
    save_user(user.id, user.first_name, user.username)
 
    channels_text = "\n".join([
        f"  {i+1}. <a href='{ch['link']}'>{ch['link']}</a>"
        for i, ch in enumerate(CHANNELS)
    ])
 
    text = (
        "🎓 <b>Отримайте 8 безкоштовних уроків на тему GRAMMAR</b>\n\n"
        f"Підпишіться на усіх 8 авторів:\n\n{channels_text}\n\n"
        "Натисни <b>Готово</b> — я перевірю твої підписки 🫶"
    )
 
    keyboard = [[InlineKeyboardButton("Готово ☑️", callback_data="check_sub")]]
 
    try:
        with open(IMAGE_PATH, "rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except FileNotFoundError:
        await update.message.reply_text(
            text=text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
 
async def check_subscription(update, context):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    save_user(user.id, user.first_name, user.username)
 
    not_subscribed = []
    for ch in CHANNELS:
        username = ch.get("username")
        if not username:
            continue
        try:
            member = await context.bot.get_chat_member(chat_id=username, user_id=user.id)
            if member.status in ("left", "kicked", "banned"):
                not_subscribed.append(ch["link"])
        except Exception as e:
            logger.warning(f"Не вдалось перевірити {username}: {e}")
            continue
 
    if not_subscribed:
        channels_list = "\n".join([f"• {link}" for link in not_subscribed])
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                "Упс, ви не підписані на всі канали — перевірте підписку 🙈\n\n"
                f"Ви ще не підписані на:\n{channels_list}\n\n"
                "Підпишіться і натисніть <b>Готово ☑️</b> ще раз ✅"
            ),
            parse_mode="HTML"
        )
    else:
        mark_subscribed(user.id)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                "🎉 Дякую за підписку!\n\n"
                "💸 Вже <b>16 листопада о 18:00</b> буде доставка ваших "
                "безкоштовних grammar уроків 📚\n\n"
                "Залишайся на зв'язку 🤖✨"
            ),
            parse_mode="HTML"
        )
 
async def send_miro(context):
    subscribers = load_subscribers()
    for uid in subscribers:
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=(
                    "📦 <b>Доставочка ваших уроків!</b>\n\n"
                    f"📚 Відкривай дошку Miro з усіма матеріалами:\n{MIRO_LINK}\n\n"
                    "Дякую за участь! 🫶"
                ),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Не вдалось надіслати {uid}: {e}")
 
async def broadcast(update, context):
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
 
async def stats(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(
        f"📊 Запустили бот: <b>{len(load_all_users())}</b>\n"
        f"✅ Перевірили підписку: <b>{len(load_subscribers())}</b>",
        parse_mode="HTML"
    )
 
USERS_FILE = "users.json"
 
def load_db():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
 
def save_db(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
 
def save_user(user_id, first_name, username):
    db = load_db()
    uid = str(user_id)
    if uid not in db:
        db[uid] = {
            "first_name": first_name,
            "username": username or "",
            "subscribed": False,
            "joined_at": datetime.now().isoformat()
        }
        save_db(db)
 
def mark_subscribed(user_id):
    db = load_db()
    uid = str(user_id)
    if uid in db:
        db[uid]["subscribed"] = True
        save_db(db)
 
def load_subscribers():
    return [uid for uid, d in load_db().items() if d.get("subscribed")]
 
def load_all_users():
    return load_db()
 
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_subscription, pattern="^check_sub$"))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("stats", stats))
 
    # Київ UTC+2 в листопаді
    kyiv_tz = timezone(timedelta(hours=2))
    send_time = datetime(2026, 11, 16, 18, 0, 0, tzinfo=kyiv_tz)
 
    now = datetime.now(tz=kyiv_tz)
    if now < send_time:
        delay = (send_time - now).total_seconds()
        app.job_queue.run_once(send_miro, when=delay)
        logger.info(f"⏰ Розсилка запланована через {delay/3600:.1f} годин")
    else:
        logger.warning("⚠️ Час розсилки вже минув!")
 
    logger.info("✅ Бот запущено!")
    app.run_polling()
 
if __name__ == "__main__":
    main()
