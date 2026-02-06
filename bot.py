import asyncio
import random
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties

from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage


BOT_TOKEN = "8361802125:AAEyQ91fL1D9lrgXqSLwINiRtk0IOLKdVrM"
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

# готовые описания услуг
PLAN_DESCRIPTIONS = {
    "Starter": "Web-site layout\nClean responsive markup",
    "Business": "Multi-page\nSEO\n+ Starter"
}


bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

dp = Dispatcher(storage=MemoryStorage())


class OrderState(StatesGroup):
    waiting_for_text = State()
    waiting_for_payment = State()
    waiting_for_proof = State()


orders = {}   # текущие заказы
user_orders = {}  # список заказов пользователя


# старт
@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Starter — 49$", callback_data="plan_Starter")],
        [InlineKeyboardButton(text="Business — 79$", callback_data="plan_Business")],
        [InlineKeyboardButton(text="Premium — from 99$", callback_data="plan_Premium")],
    ])

    await state.clear()
    await message.answer(
        "Выберите тариф:\n\n"
        "Команда /orders — мои заказы",
        reply_markup=kb
    )


# мои заказы
@dp.message(Command("orders"))
async def my_orders(message: Message):
    user_id = message.from_user.id

    if user_id not in user_orders or not user_orders[user_id]:
        await message.answer("У вас пока нет заказов.")
        return

    text = "<b>Ваши заказы:</b>\n\n"
    for order in user_orders[user_id]:
        text += f"№ {order['id']} — {order['plan']}\n"

    await message.answer(text)


# выбор тарифа
@dp.callback_query(F.data.startswith("plan_"))
async def choose_plan(callback: CallbackQuery, state: FSMContext):
    plan = callback.data.split("_")[1]
    price = PRICES.get(plan, "")

    orders[callback.from_user.id] = {
        "plan": plan,
        "text": None
    }

    # если тариф с готовым описанием
    if plan in PLAN_DESCRIPTIONS:
        orders[callback.from_user.id]["text"] = PLAN_DESCRIPTIONS[plan]
        await send_payment_info(callback.message, callback.from_user.id, state)
    else:
        await state.set_state(OrderState.waiting_for_text)
        await callback.message.answer(
            f"Тариф: <b>{plan}</b>\n"
            f"Цена: <b>{price}</b>\n\n"
            "Напишите, что вам нужно."
        )

    await callback.answer()


async def send_payment_info(message, user_id, state):
    plan = orders[user_id]["plan"]
    price = PRICES.get(plan, "")
    description = orders[user_id]["text"]

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Я оплатил", callback_data="paid")]
    ])

    await message.answer(
        f"Тариф: <b>{plan}</b>\n"
        f"{description}\n\n"
        f"💰 К оплате: <b>{price}</b>\n\n"
        f"{CARD_INFO}\n\n"
        "После оплаты нажмите кнопку и пришлите скрин.",
        reply_markup=kb
    )

    await state.set_state(OrderState.waiting_for_payment)


# пользователь пишет задачу (только Premium)
@dp.message(OrderState.waiting_for_text, F.text)
async def user_text(message: Message, state: FSMContext):
    user_id = message.from_user.id
    orders[user_id]["text"] = message.text
    await send_payment_info(message, user_id, state)


# нажал оплатил
@dp.callback_query(F.data == "paid", OrderState.waiting_for_payment)
async def paid(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Пришлите скрин оплаты.")
    await state.set_state(OrderState.waiting_for_proof)
    await callback.answer()


# пришёл скрин
@dp.message(OrderState.waiting_for_proof, F.photo)
async def payment_proof(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id not in orders:
        return

    order_id = f"KLKV-{random.randint(1000,9999)}"
    orders[user_id]["order_id"] = order_id

    # сохраняем в список заказов пользователя
    user_orders.setdefault(user_id, []).append({
        "id": order_id,
        "plan": orders[user_id]["plan"]
    })

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Работа сделана",
            callback_data=f"done_{user_id}"
        )]
    ])

    caption = (
        f"🧾 Новый заказ #{order_id}\n\n"
        f"Тариф: {orders[user_id]['plan']}\n"
        f"Цена: {PRICES.get(orders[user_id]['plan'])}\n\n"
        f"Описание:\n{orders[user_id]['text']}"
    )

    await bot.send_photo(
        ADMIN_ID,
        message.photo[-1].file_id,
        caption=caption,
        reply_markup=kb
    )

    await message.answer(
        f"✅ Скрин получен!\n"
        f"Ваш номер заказа: <b>{order_id}</b>\n"
        f"Ожидайте подтверждения."
    )

    await state.clear()


# админ завершил заказ
@dp.callback_query(F.data.startswith("done_"))
async def done_order(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])

    await bot.send_message(
        user_id,
        "🎉 Работа готова!\nЕсли нужны правки — напишите сюда."
    )

    await callback.message.edit_caption(
        callback.message.caption + "\n\n✅ Работа завершена"
    )

    await callback.answer("Клиенту отправлено уведомление")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
