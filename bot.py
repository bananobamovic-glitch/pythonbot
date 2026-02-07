import asyncio
import json
import os
import random

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties

BOT_TOKEN = os.getenv("8361802125:AAEyQ91fL1D9lrgXqSLwINiRtk0IOLKdVrM")
ADMIN_ID = 8291430081

CARD_INFO = """
💳 <b>Monobank</b>
<code>5375 4115 9110 2551</code>

💳 <b>Oschadbank</b>
<code>5167 8032 9963 7046</code>
"""

PRICES = {
    "Starter": "49$",
    "Business": "79$",
    "Premium": "from 99$"
}

PLAN_DESCRIPTIONS = {
    "Starter": "Clean responsive markup",
    "Business": "Multi-page + SEO + Starter"
}

ORDERS_FILE = "orders.json"

def load_orders():
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_orders():
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, indent=4, ensure_ascii=False)

orders = load_orders()

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

dp = Dispatcher()


# СТАРТ
@dp.message(Command("start"))
async def start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Starter — 49$", callback_data="plan_Starter")],
        [InlineKeyboardButton(text="Business — 79$", callback_data="plan_Business")],
        [InlineKeyboardButton(text="Premium — from 99$", callback_data="plan_Premium")],
    ])

    await message.answer(
        "Выберите тариф:\n\n"
        "/orders — мои заказы",
        reply_markup=kb
    )


# МОИ ЗАКАЗЫ
@dp.message(Command("orders"))
async def my_orders(message: Message):
    user_id = str(message.from_user.id)

    user_orders = [o for o in orders.values() if o["user_id"] == user_id]

    if not user_orders:
        await message.answer("У вас пока нет заказов.")
        return

    text = "<b>Ваши заказы:</b>\n\n"

    for order in user_orders:
        text += f"№ {order['id']} | {order['plan']} | {order['status']}\n"

    await message.answer(text)


# ВЫБОР ТАРИФА
@dp.callback_query(F.data.startswith("plan_"))
async def choose_plan(callback: CallbackQuery):
    plan = callback.data.split("_")[1]

    order_id = f"KLKV-{random.randint(1000,9999)}"

    description = PLAN_DESCRIPTIONS.get(plan, "Пользователь напишет описание")

    orders[order_id] = {
        "id": order_id,
        "user_id": str(callback.from_user.id),
        "plan": plan,
        "description": description,
        "status": "Ожидает оплаты"
    }

    save_orders()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Я оплатил", callback_data=f"paid_{order_id}")]
    ])

    await callback.message.answer(
        f"Заказ № <b>{order_id}</b>\n"
        f"Тариф: <b>{plan}</b>\n"
        f"Цена: <b>{PRICES.get(plan)}</b>\n\n"
        f"{CARD_INFO}\n\n"
        "После оплаты нажмите кнопку и пришлите скрин.",
        reply_markup=kb
    )

    await callback.answer()


# ОПЛАТИЛ
@dp.callback_query(F.data.startswith("paid_"))
async def paid(callback: CallbackQuery):
    order_id = callback.data.split("_")[1]

    await callback.message.answer(
        f"Пришлите скрин оплаты для заказа {order_id}"
    )
    await callback.answer()


# СКРИН
@dp.message(F.photo)
async def payment_proof(message: Message):

    # ищем последний заказ пользователя
    user_id = str(message.from_user.id)

    user_orders = [o for o in orders.values() if o["user_id"] == user_id]

    if not user_orders:
        return

    order = user_orders[-1]
    order["status"] = "Оплачен"
    save_orders()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛠 В работу", callback_data=f"work_{order['id']}")],
        [InlineKeyboardButton(text="✅ Готово", callback_data=f"done_{order['id']}")]
    ])

    caption = (
        f"🧾 Новый заказ {order['id']}\n\n"
        f"Тариф: {order['plan']}\n"
        f"Статус: {order['status']}\n"
        f"Описание: {order['description']}"
    )

    await bot.send_photo(
        ADMIN_ID,
        message.photo[-1].file_id,
        caption=caption,
        reply_markup=kb
    )

    await message.answer(
        f"✅ Оплата принята\n"
        f"Номер заказа: {order['id']}\n"
        f"Ожидайте начала работы."
    )


# В РАБОТУ
@dp.callback_query(F.data.startswith("work_"))
async def work_order(callback: CallbackQuery):
    order_id = callback.data.split("_")[1]

    orders[order_id]["status"] = "В работе"
    save_orders()

    user_id = int(orders[order_id]["user_id"])

    await bot.send_message(user_id, f"🛠 Заказ {order_id} взят в работу")
    await callback.answer("Статус обновлён")


# ГОТОВО
@dp.callback_query(F.data.startswith("done_"))
async def done_order(callback: CallbackQuery):
    order_id = callback.data.split("_")[1]

    orders[order_id]["status"] = "Готов"
    save_orders()

    user_id = int(orders[order_id]["user_id"])

    await bot.send_message(user_id, f"🎉 Заказ {order_id} готов!")
    await callback.answer("Готово")


# СТАТИСТИКА
@dp.message(Command("stats"))
async def stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    total = len(orders)
    ready = sum(1 for o in orders.values() if o["status"] == "Готов")

    await message.answer(
        f"📊 Статистика\n\n"
        f"Всего заказов: {total}\n"
        f"Готово: {ready}"
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
