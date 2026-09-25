import os
import random
import logging
from threading import Thread
from flask import Flask

from telegram import Update, LabeledPrice
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
    ContextTypes,
)

import database as db

# ---------- НАСТРОЙКИ ----------
TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))  # твой Telegram ID

# ---------- ЛОГИ ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- РЕЖИМЫ ----------
chaos_mode = False
learn_mode = False

# ---------- МАТЕРШИННИК ----------
MATY = [
    "блядь, ну ты и долбоёб",
    "хуйня какая-то, честно",
    "иди нахуй, я устал",
    "пиздец, опять ты",
    "заебал, отвали",
    "ну и хуй с тобой",
    "ебаный в рот, что ты несёшь",
    "соси хуй, умник",
    "ты че, ебнулся?",
    "пошёл нахуй, я не в настроении",
]

# ---------- ФЕЙКОВЫЙ ВЕБ-СЕРВЕР ДЛЯ RENDER ----------
app = Flask(__name__)

@app.route("/")
def health():
    return "bot is alive"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ---------- ВСПОМОГАТЕЛЬНОЕ ----------
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

# ---------- КОМАНДЫ АДМИНА ----------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        text = (
            "👑 Ты админ. Команды:\n"
            "/new_prize Название Цена_в_Stars — создать приз\n"
            "/prizes — список активных призов\n"
            "/close_prize ID — закрыть приз\n"
            "/draw ID — провести розыгрыш\n"
            "/chaos_on /chaos_off — режим чуши\n"
            "/learn_on /learn_off — режим обучения"
        )
    else:
        text = (
            "🤖 Я бот для розыгрышей.\n"
            "Пиши /join ID_приза чтобы участвовать (платно).\n"
            "Список призов: /prizes"
        )
    await update.message.reply_text(text)

async def cmd_new_prize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создать приз: /new_prize iPhone 100"""
    if not is_admin(update.effective_user.id):
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Формат: /new_prize Название Цена_в_Stars")
        return
    
    # Последний аргумент — цена, остальное — название
    try:
        price = int(args[-1])
    except ValueError:
        await update.message.reply_text("Цена должна быть числом.")
        return
    
    title = " ".join(args[:-1])
    prize_id = db.create_prize(title, price)
    
    await update.message.reply_text(
        f"✅ Приз создан!\n"
        f"ID: {prize_id}\n"
        f"Название: {title}\n"
        f"Цена: {price} Stars"
    )

async def cmd_prizes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список активных призов."""
    prizes = db.get_active_prizes()
    if not prizes:
        await update.message.reply_text("Нет активных призов.")
        return
    
    text = "🎁 Активные призы:\n\n"
    for p in prizes:
        text += f"#{p['id']} — {p['title']} ({p['price_stars']} Stars)\n"
    
    await update.message.reply_text(text)

async def cmd_close_prize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Закрыть приз: /close_prize 1"""
    if not is_admin(update.effective_user.id):
        return
    
    if not context.args:
        await update.message.reply_text("Формат: /close_prize ID")
        return
    
    try:
        prize_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID должен быть числом.")
        return
    
    db.deactivate_prize(prize_id)
    await update.message.reply_text(f"Приз #{prize_id} закрыт.")

async def cmd_draw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Розыгрыш: /draw 1"""
    if not is_admin(update.effective_user.id):
        return
    
    if not context.args:
        await update.message.reply_text("Формат: /draw ID_приза")
        return
    
    try:
        prize_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID должен быть числом.")
        return
    
    prize = db.get_prize_by_id(prize_id)
    if not prize:
        await update.message.reply_text("Приз не найден.")
        return
    
    participants = db.get_participants(prize_id)
    if not participants:
        await update.message.reply_text("Нет участников.")
        return
    
    winner = random.choice(participants)
    mention = f"@{winner['username']}" if winner['username'] else winner['first_name']
    
    await update.message.reply_text(
        f"🎉 Розыгрыш: {prize['title']}\n"
        f"👥 Участников: {len(participants)}\n"
        f"🏆 Победитель: {mention} (ID: {winner['user_id']})"
    )
    
    # Закрываем приз после розыгрыша
    db.deactivate_prize(prize_id)

# ---------- РЕЖИМЫ ЧУШИ ----------
async def cmd_chaos_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global chaos_mode
    if not is_admin(update.effective_user.id):
        return
    chaos_mode = True
    await update.message.reply_text("Режим чуши ВКЛЮЧЁН.")

async def cmd_chaos_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global chaos_mode
    if not is_admin(update.effective_user.id):
        return
    chaos_mode = False
    await update.message.reply_text("Режим чуши ВЫКЛЮЧЕН.")

async def cmd_learn_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global learn_mode
    if not is_admin(update.effective_user.id):
        return
    learn_mode = True
    await update.message.reply_text("Режим обучения ВКЛЮЧЁН.")

async def cmd_learn_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global learn_mode
    if not is_admin(update.effective_user.id):
        return
    learn_mode = False
    await update.message.reply_text("Режим обучения ВЫКЛЮЧЕН.")

# ---------- УЧАСТИЕ В РОЗЫГРЫШЕ (ПЛАТНОЕ) ----------
async def cmd_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Участие: /join 1"""
    if not context.args:
        await update.message.reply_text("Формат: /join ID_приза")
        return
    
    try:
        prize_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID должен быть числом.")
        return
    
    prize = db.get_prize_by_id(prize_id)
    if not prize or not prize["is_active"]:
        await update.message.reply_text("Приз не найден или закрыт.")
        return
    
    user = update.effective_user
    
    # Отправляем счёт на оплату Stars
    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title=prize["title"],
        description=f"Участие в розыгрыше: {prize['title']}",
        payload=f"prize_{prize_id}_user_{user.id}",
        provider_token="",  # Для Stars оставляем пустым
        currency="XTR",
        prices=[LabeledPrice(label=prize["title"], amount=prize["price_stars"])],
    )

# ---------- ОБРАБОТКА ПЛАТЕЖЕЙ ----------
async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение перед оплатой. Обязательно ответить в течение 10 секунд."""
    query = update.pre_checkout_query
    # Всегда подтверждаем (можно добавить проверки)
    await query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Успешная оплата — добавляем в участники."""
    payment = update.message.successful_payment
    user = update.effective_user
    
    # Парсим payload: prize_1_user_123
    payload = payment.invoice_payload
    parts = payload.split("_")
    prize_id = int(parts[1])
    
    # Добавляем участника
    added = db.add_participant(
        prize_id=prize_id,
        user_id=user.id,
        username=user.username or "",
        first_name=user.first_name or "",
        charge_id=payment.telegram_payment_charge_id
    )
    
    prize = db.get_prize_by_id(prize_id)
    title = prize["title"] if prize else "приз"
    
    if added:
        await update.message.reply_text(
            f"✅ Ты участвуешь в розыгрыше: {title}!\n"
            f"Удачи! 🍀"
        )
    else:
        await update.message.reply_text("Ты уже участвуешь в этом розыгрыше.")

# ---------- ОБРАБОТКА СООБЩЕНИЙ (ЧУШЬ + ОБУЧЕНИЕ) ----------
async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global learn_mode, chaos_mode
    text = update.message.text
    if not text:
        return
    
    # Обучение
    if learn_mode:
        db.add_learned_phrase(text)
        return
    
    # Режим чуши
    if chaos_mode:
        # 10% — выученная фраза
        if random.random() < 0.1:
            phrase = db.get_random_learned_phrase()
            if phrase:
                await update.message.reply_text(phrase)
                return
        
        # 70% — мат
        if random.random() < 0.7:
            await update.message.reply_text(random.choice(MATY))
            return
        
        # 20% — выученная фраза или мат
        phrase = db.get_random_learned_phrase()
        if phrase:
            await update.message.reply_text(phrase)
        else:
            await update.message.reply_text(random.choice(MATY))

# ---------- ЗАПУСК ----------
def main():
    db.init_db()
    
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Команды админа
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("new_prize", cmd_new_prize))
    application.add_handler(CommandHandler("prizes", cmd_prizes))
    application.add_handler(CommandHandler("close_prize", cmd_close_prize))
    application.add_handler(CommandHandler("draw", cmd_draw))
    application.add_handler(CommandHandler("chaos_on", cmd_chaos_on))
    application.add_handler(CommandHandler("chaos_off", cmd_chaos_off))
    application.add_handler(CommandHandler("learn_on", cmd_learn_on))
    application.add_handler(CommandHandler("learn_off", cmd_learn_off))
    
    # Участие
    application.add_handler(CommandHandler("join", cmd_join))
    
    # Платежи
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    
    # Сообщения (чушь + обучение)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    
    # Фейковый веб-сервер для Render
    Thread(target=run_flask, daemon=True).start()
    
    logger.info("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()