import asyncio
import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils import executor
from tinydb import TinyDB, Query

# Твой токен от BotFather
TOKEN = "ТОКЕН_СЮДА"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

db = TinyDB("stats.json")
users_table = db.table("users")

# Для ограничения команды /калл
last_call_time = {}

# Добавление пользователя
async def add_user(user_id, username):
    if not users_table.contains(Query().user_id == user_id):
        users_table.insert({"user_id": user_id, "username": username, "messages": 0})

# Удаление пользователя
async def remove_user(user_id):
    users_table.remove(Query().user_id == user_id)

# Подсчёт сообщений
@dp.message_handler()
async def count_messages(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name
    await add_user(user_id, username)
    users_table.update_increment("messages", Query().user_id == user_id)

# Команда статистики
@dp.message_handler(commands=["статистика"])
async def show_stats(message: types.Message):
    users = sorted(users_table.all(), key=lambda x: x["messages"], reverse=True)
    if not users:
        await message.reply("Пока нет данных о сообщениях 😶")
        return

    text = "🏆 <b>Топ по сообщениям:</b>\n\n"
    for i, u in enumerate(users, start=1):
        text += f"{i}. @{u['username']} — {u['messages']} сообщений\n"

    await message.reply(text, parse_mode="HTML")

# Команда /калл
@dp.message_handler(lambda message: message.text.lower().startswith("калл"))
async def call_all(message: types.Message):
    global last_call_time
    chat_id = message.chat.id
    user_id = message.from_user.id
    now = datetime.datetime.now()

    if user_id in last_call_time and (now - last_call_time[user_id]).total_seconds() < 30:
        await message.reply("⏳ Подожди 30 секунд перед следующим вызовом.")
        return

    last_call_time[user_id] = now
    members = [u["username"] for u in users_table.all() if u["username"]]
    if not members:
        await message.reply("Нет зарегистрированных участников 😅")
        return

    call_text = message.text[4:].strip() or "всем сюда!"
    text = f"📢 <b>{call_text}</b>\n\n" + " ".join([f"@{m}" for m in members])
    await message.reply(text, parse_mode="HTML")

# Автоматический сброс статистики каждый понедельник
async def reset_stats():
    while True:
        now = datetime.datetime.now()
        if now.weekday() == 0 and now.hour == 0 and now.minute == 0:
            users_table.update({"messages": 0})
            await asyncio.sleep(60)
        await asyncio.sleep(30)

# Реакция на выход и вход пользователей
@dp.chat_member_handler()
async def track_members(update: types.ChatMemberUpdated):
    if update.new_chat_member.status == "member":
        await add_user(update.new_chat_member.user.id, update.new_chat_member.user.username)
    elif update.new_chat_member.status in ["left", "kicked"]:
        await remove_user(update.new_chat_member.user.id)

# Запуск
async def on_startup(_):
    asyncio.create_task(reset_stats())
    print("✅ Бот запущен!")

if __name__ == "__main__":
    from aiogram import executor
    executor.start_polling(dp, on_startup=on_startup)
