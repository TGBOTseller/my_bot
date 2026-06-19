from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
import asyncio
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import requests
import json
import os
from datetime import datetime

API_TOKEN = '8847770817:AAEvb1wu9D3eFESfNKNkZB-IKdvLC-edGZo'
OPENAI_API_KEY = 'sk-0f1BAqfKVomDNTYyzVaoPVYcQ7ciRDSr'
ADMIN_ID = 823834143

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

DATA_FILE = 'data.json'
ORDERS_FILE = 'orders.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "menu": [
            {"name": "Шаурма с курицей", "price": 250},
            {"name": "Шаурма с говядиной", "price": 290},
            {"name": "Картошка фри", "price": 120},
            {"name": "Напитки", "price": 80}
        ],
        "address": "ул. Пушкина, д. 10",
        "phone": "+7 (999) 123-45-67",
        "schedule": "Пн-Вс 10:00 – 23:00",
        "delivery": "Бесплатно от 800 руб., время 45 минут."
    }

def load_orders():
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_orders(orders):
    with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)

data = load_data()
orders = load_orders()
user_data = {}
chat_history = {}

# --- Клавиатуры ---

def get_main_keyboard():
    keyboard = [
        [KeyboardButton(text="📜 Меню"), KeyboardButton(text="📍 Адрес")],
        [KeyboardButton(text="🛒 Сделать заказ"), KeyboardButton(text="📞 Позвонить нам")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_order_keyboard():
    keyboard = []
    for item in data["menu"]:
        keyboard.append([KeyboardButton(text=f"{item['name']} ({item['price']}₽)")])
    keyboard.append([KeyboardButton(text="❌ Очистить корзину"), KeyboardButton(text="✅ Готово")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_cancel_keyboard():
    keyboard = [
        [KeyboardButton(text="❌ Отмена"), KeyboardButton(text="⏭️ Пропустить")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_confirm_keyboard():
    keyboard = [
        [KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет, выбрать другое")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_admin_keyboard():
    keyboard = [
        [KeyboardButton(text="📝 Изменить меню")],
        [KeyboardButton(text="📍 Изменить адрес"), KeyboardButton(text="📞 Изменить телефон")],
        [KeyboardButton(text="🕒 Изменить график"), KeyboardButton(text="🚚 Изменить доставку")],
        [KeyboardButton(text="📊 Посмотреть заказы"), KeyboardButton(text="📈 Статистика")],
        [KeyboardButton(text="📤 Экспорт заказов"), KeyboardButton(text="🔄 Сбросить все данные")],
        [KeyboardButton(text="◀️ Выйти из админки")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_menu_edit_keyboard():
    keyboard = [
        [KeyboardButton(text="➕ Добавить блюдо")],
        [KeyboardButton(text="✏️ Редактировать блюдо"), KeyboardButton(text="❌ Удалить блюдо")],
        [KeyboardButton(text="🔙 Назад в админку")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# --- Команды ---

@dp.message(Command('start'))
async def start(message: Message):
    chat_id = message.chat.id
    user_data[chat_id] = {"stage": "main", "cart": [], "total": 0}
    chat_history[chat_id] = [
        {"role": "system", "content": f"Ты помощник шаурмичной. Отвечай кратко по базе:\n"
                                      f"Адрес: {data['address']}\n"
                                      f"Телефон: {data['phone']}\n"
                                      f"График: {data['schedule']}\n"
                                      f"Доставка: {data['delivery']}\n"
                                      f"Меню: {', '.join([f'{item['name']} - {item['price']}₽' for item in data['menu']])}"}
    ]
    await message.answer(
        "🥙 Привет! Я бот 'Вкусный Восток'.\nВыбери действие на клавиатуре:",
        reply_markup=get_main_keyboard()
    )

@dp.message(Command('admin'))
async def admin_panel(message: Message):
    chat_id = message.chat.id
    if chat_id != ADMIN_ID:
        await message.answer("⛔ Доступ запрещён. Вы не являетесь администратором.")
        return
    user_data[chat_id] = {"stage": "admin"}
    await message.answer(
        "🔐 Админ-панель\n\nВыберите действие:",
        reply_markup=get_admin_keyboard()
    )

# --- Обработчик ---

@dp.message()
async def handle_buttons(message: Message):
    text = message.text
    chat_id = message.chat.id

    # === АДМИНКА ===
    if chat_id == ADMIN_ID and user_data.get(chat_id, {}).get("stage") == "admin":
        if text == "📝 Изменить меню":
            user_data[chat_id]["stage"] = "admin_menu_edit"
            await show_menu_edit(message)
            return
        
        if text == "📍 Изменить адрес":
            user_data[chat_id]["stage"] = "admin_edit_address"
            await message.answer(f"📍 Текущий адрес: {data['address']}\n\nВведите новый адрес:", reply_markup=get_cancel_keyboard())
            return
        
        if text == "📞 Изменить телефон":
            user_data[chat_id]["stage"] = "admin_edit_phone"
            await message.answer(f"📞 Текущий телефон: {data['phone']}\n\nВведите новый телефон:", reply_markup=get_cancel_keyboard())
            return
        
        if text == "🕒 Изменить график":
            user_data[chat_id]["stage"] = "admin_edit_schedule"
            await message.answer(f"🕒 Текущий график: {data['schedule']}\n\nВведите новый график:", reply_markup=get_cancel_keyboard())
            return
        
        if text == "🚚 Изменить доставку":
            user_data[chat_id]["stage"] = "admin_edit_delivery"
            await message.answer(f"🚚 Текущие условия доставки: {data['delivery']}\n\nВведите новые условия:", reply_markup=get_cancel_keyboard())
            return

        if text == "📊 Посмотреть заказы":
            if not orders:
                await message.answer("📭 Заказов пока нет.")
            else:
                last_orders = orders[-10:][::-1]
                text_orders = "📋 Последние заказы:\n\n"
                for order in last_orders:
                    text_orders += f"🆕 {order['date']}\n📦 {order['details']}\n💰 {order['total']}₽\n📞 {order['phone']}\n📍 {order['address']}\n\n"
                await message.answer(text_orders)
            return

        if text == "📈 Статистика":
            if not orders:
                await message.answer("📭 Заказов пока нет. Статистика пуста.")
                return
            today = datetime.now().date()
            today_orders = [o for o in orders if datetime.strptime(o['date'], '%Y-%m-%d %H:%M:%S').date() == today]
            week_orders = [o for o in orders if (datetime.now() - datetime.strptime(o['date'], '%Y-%m-%d %H:%M:%S')).days < 7]
            await message.answer(
                f"📈 СТАТИСТИКА\n\n📅 Сегодня: {len(today_orders)} заказов\n💰 Выручка сегодня: {sum(o['total'] for o in today_orders)}₽\n\n📆 За неделю: {len(week_orders)} заказов\n💰 Выручка за неделю: {sum(o['total'] for o in week_orders)}₽\n\n📊 Всего заказов: {len(orders)}"
            )
            return

        if text == "📤 Экспорт заказов":
            if not orders:
                await message.answer("📭 Нет заказов для экспорта.")
                return
            export_text = "📋 ВСЕ ЗАКАЗЫ\n\n"
            for order in orders:
                export_text += f"🆕 {order['date']}\n📦 {order['details']}\n💰 {order['total']}₽\n📞 {order['phone']}\n📍 {order['address']}\n\n"
            with open('orders_export.txt', 'w', encoding='utf-8') as f:
                f.write(export_text)
            with open('orders_export.txt', 'rb') as f:
                await message.answer_document(types.BufferedInputFile(f.read(), filename='orders_export.txt'), caption="📤 Экспорт заказов выполнен.")
            return

        if text == "🔄 Сбросить все данные":
            user_data[chat_id]["stage"] = "admin_confirm_reset"
            await message.answer("⚠️ ВНИМАНИЕ! Вы собираетесь удалить ВСЕ заказы и сбросить настройки.\nЭто действие НЕЛЬЗЯ отменить.\n\nДля подтверждения введите: ДА, СБРОСИТЬ", reply_markup=get_cancel_keyboard())
            return
        
        if text == "◀️ Выйти из админки":
            user_data[chat_id] = {"stage": "main"}
            await message.answer("Выход из админ-панели.", reply_markup=get_main_keyboard())
            return

    # === РЕДАКТИРОВАНИЕ МЕНЮ ===
    if chat_id == ADMIN_ID and user_data.get(chat_id, {}).get("stage") == "admin_menu_edit":
        if text == "➕ Добавить блюдо":
            user_data[chat_id]["stage"] = "admin_add_item_name"
            await message.answer("Введите название нового блюда:", reply_markup=get_cancel_keyboard())
            return
        
        if text == "✏️ Редактировать блюдо":
            user_data[chat_id]["stage"] = "admin_edit_item_select"
            await show_menu_edit(message)
            await message.answer("Введите номер блюда, которое хотите отредактировать:", reply_markup=get_cancel_keyboard())
            return
        
        if text == "❌ Удалить блюдо":
            user_data[chat_id]["stage"] = "admin_delete_item_select"
            await show_menu_edit(message)
            await message.answer("Введите номер блюда, которое хотите удалить:", reply_markup=get_cancel_keyboard())
            return
        
        if text == "🔙 Назад в админку":
            user_data[chat_id] = {"stage": "admin"}
            await message.answer("Возврат в админ-панель.", reply_markup=get_admin_keyboard())
            return

    # --- ДОБАВЛЕНИЕ ---
    if chat_id == ADMIN_ID and user_data.get(chat_id, {}).get("stage") == "admin_add_item_name":
        if text == "❌ Отмена":
            user_data[chat_id] = {"stage": "admin_menu_edit"}
            await message.answer("Отмена.", reply_markup=get_menu_edit_keyboard())
            return
        user_data[chat_id]["new_item_name"] = text
        user_data[chat_id]["stage"] = "admin_add_item_price"
        await message.answer(f"Введите цену для блюда '{text}':", reply_markup=get_cancel_keyboard())
        return

    if chat_id == ADMIN_ID and user_data.get(chat_id, {}).get("stage") == "admin_add_item_price":
        if text == "❌ Отмена":
            user_data[chat_id] = {"stage": "admin_menu_edit"}
            await message.answer("Отмена.", reply_markup=get_menu_edit_keyboard())
            return
        try:
            price = int(text.strip())
            name = user_data[chat_id].get("new_item_name")
            data["menu"].append({"name": name, "price": price})
            save_data(data)
            user_data[chat_id] = {"stage": "admin_menu_edit"}
            await message.answer(f"✅ Блюдо '{name}' добавлено с ценой {price}₽.", reply_markup=get_menu_edit_keyboard())
            await show_menu_edit(message)
        except ValueError:
            await message.answer("❌ Ошибка! Цена должна быть числом. Попробуйте снова.")

    # --- ВЫБОР БЛЮДА ДЛЯ РЕДАКТИРОВАНИЯ ---
    if chat_id == ADMIN_ID and user_data.get(chat_id, {}).get("stage") == "admin_edit_item_select":
        if text == "❌ Отмена":
            user_data[chat_id] = {"stage": "admin_menu_edit"}
            await message.answer("Отмена. Возврат к редактированию меню.", reply_markup=get_menu_edit_keyboard())
            return
        try:
            idx = int(text.strip()) - 1
            if 0 <= idx < len(data["menu"]):
                user_data[chat_id]["edit_idx"] = idx
                user_data[chat_id]["stage"] = "admin_edit_item_confirm"
                await message.answer(
                    f"Вы выбрали блюдо **{data['menu'][idx]['name']}** ({data['menu'][idx]['price']}₽).\n"
                    f"Подтвердите выбор:",
                    reply_markup=get_confirm_keyboard()
                )
            else:
                await message.answer("❌ Неверный номер. Попробуйте снова.")
        except ValueError:
            await message.answer("❌ Введите число.")

    # --- ПОДТВЕРЖДЕНИЕ ВЫБОРА БЛЮДА ---
    if chat_id == ADMIN_ID and user_data.get(chat_id, {}).get("stage") == "admin_edit_item_confirm":
        if text == "✅ Да":
            idx = user_data[chat_id].get("edit_idx")
            user_data[chat_id]["stage"] = "admin_edit_item_name"
            await message.answer(
                f"Текущее название: {data['menu'][idx]['name']}\n"
                f"Текущая цена: {data['menu'][idx]['price']}₽\n\n"
                f"Введите **новое название** (или нажмите 'Пропустить', чтобы оставить текущее):",
                reply_markup=get_cancel_keyboard()
            )
        elif text == "❌ Нет, выбрать другое":
            user_data[chat_id]["stage"] = "admin_edit_item_select"
            await message.answer("Введите номер блюда заново:", reply_markup=get_cancel_keyboard())
        else:
            await message.answer("Пожалуйста, нажмите 'Да' или 'Нет'.")
        return

    # --- ВВОД НОВОГО НАЗВАНИЯ ---
    if chat_id == ADMIN_ID and user_data.get(chat_id, {}).get("stage") == "admin_edit_item_name":
        if text == "❌ Отмена":
            user_data[chat_id] = {"stage": "admin_menu_edit"}
            await message.answer("Отмена. Возврат к редактированию меню.", reply_markup=get_menu_edit_keyboard())
            return
        
        if text == "⏭️ Пропустить":
            await message.answer("⏭️ Название оставлено без изменений.")
        else:
            idx = user_data[chat_id].get("edit_idx")
            data["menu"][idx]["name"] = text.strip()
            save_data(data)
            await message.answer("✅ Название обновлено.")
        
        user_data[chat_id]["stage"] = "admin_edit_item_price"
        await message.answer(
            f"Введите **новую цену** (или нажмите 'Пропустить', чтобы оставить текущую):",
            reply_markup=get_cancel_keyboard()
        )
        return

    # --- ВВОД НОВОЙ ЦЕНЫ ---
    if chat_id == ADMIN_ID and user_data.get(chat_id, {}).get("stage") == "admin_edit_item_price":
        if text == "❌ Отмена":
            user_data[chat_id] = {"stage": "admin_menu_edit"}
            await message.answer("Отмена. Возврат к редактированию меню.", reply_markup=get_menu_edit_keyboard())
            return
        
        if text == "⏭️ Пропустить":
            await message.answer("⏭️ Цена оставлена без изменений.")
        else:
            try:
                price = int(text.strip())
                idx = user_data[chat_id].get("edit_idx")
                data["menu"][idx]["price"] = price
                save_data(data)
                await message.answer("✅ Цена обновлена.")
            except ValueError:
                await message.answer("❌ Ошибка! Цена должна быть числом. Попробуйте снова.")
                return
        
        user_data[chat_id] = {"stage": "admin_menu_edit"}
        await message.answer("✅ Блюдо обновлено.", reply_markup=get_menu_edit_keyboard())
        await show_menu_edit(message)
        return

    # --- УДАЛЕНИЕ ---
    if chat_id == ADMIN_ID and user_data.get(chat_id, {}).get("stage") == "admin_delete_item_select":
        if text == "❌ Отмена":
            user_data[chat_id] = {"stage": "admin_menu_edit"}
            await message.answer("Отмена.", reply_markup=get_menu_edit_keyboard())
            return
        try:
            idx = int(text.strip()) - 1
            if 0 <= idx < len(data["menu"]):
                deleted = data["menu"].pop(idx)
                save_data(data)
                user_data[chat_id] = {"stage": "admin_menu_edit"}
                await message.answer(f"✅ Блюдо '{deleted['name']}' удалено.", reply_markup=get_menu_edit_keyboard())
                await show_menu_edit(message)
            else:
                await message.answer("❌ Неверный номер.")
        except ValueError:
            await message.answer("❌ Введите число.")

    # --- ОСТАЛЬНЫЕ РЕДАКТИРОВАНИЯ ---
    if chat_id == ADMIN_ID and user_data.get(chat_id, {}).get("stage") in ["admin_edit_address", "admin_edit_phone", "admin_edit_schedule", "admin_edit_delivery", "admin_confirm_reset"]:
        if text == "❌ Отмена":
            user_data[chat_id] = {"stage": "admin"}
            await message.answer("Отмена.", reply_markup=get_admin_keyboard())
            return

        stage = user_data[chat_id]["stage"]

        if stage == "admin_edit_address":
            data["address"] = text.strip()
            save_data(data)
            user_data[chat_id] = {"stage": "admin"}
            await message.answer(f"✅ Адрес обновлён: {data['address']}", reply_markup=get_admin_keyboard())
            return

        if stage == "admin_edit_phone":
            data["phone"] = text.strip()
            save_data(data)
            user_data[chat_id] = {"stage": "admin"}
            await message.answer(f"✅ Телефон обновлён: {data['phone']}", reply_markup=get_admin_keyboard())
            return

        if stage == "admin_edit_schedule":
            data["schedule"] = text.strip()
            save_data(data)
            user_data[chat_id] = {"stage": "admin"}
            await message.answer(f"✅ График обновлён: {data['schedule']}", reply_markup=get_admin_keyboard())
            return

        if stage == "admin_edit_delivery":
            data["delivery"] = text.strip()
            save_data(data)
            user_data[chat_id] = {"stage": "admin"}
            await message.answer(f"✅ Условия доставки обновлены: {data['delivery']}", reply_markup=get_admin_keyboard())
            return

        if stage == "admin_confirm_reset":
            if text.strip() == "ДА, СБРОСИТЬ":
                orders.clear()
                save_orders(orders)
                data["menu"] = [
                    {"name": "Шаурма с курицей", "price": 250},
                    {"name": "Шаурма с говядиной", "price": 290},
                    {"name": "Картошка фри", "price": 120},
                    {"name": "Напитки", "price": 80}
                ]
                data["address"] = "ул. Пушкина, д. 10"
                data["phone"] = "+7 (999) 123-45-67"
                data["schedule"] = "Пн-Вс 10:00 – 23:00"
                data["delivery"] = "Бесплатно от 800 руб., время 45 минут."
                save_data(data)
                user_data[chat_id] = {"stage": "admin"}
                await message.answer("✅ Все данные сброшены к стандартным настройкам.", reply_markup=get_admin_keyboard())
            else:
                await message.answer("❌ Неверная команда. Сброс отменён.")
                user_data[chat_id] = {"stage": "admin"}
                await message.answer("Возврат в админ-панель.", reply_markup=get_admin_keyboard())
            return

    # --- ОСНОВНЫЕ КНОПКИ ---
    if text == "📜 Меню":
        await show_menu(message)
        return

    if text == "📍 Адрес":
        await message.answer(f"📍 Мы находимся: {data['address']}\n🕒 График: {data['schedule']}\n📞 Телефон: {data['phone']}", reply_markup=get_main_keyboard())
        return

    if text == "📞 Позвонить нам":
        await message.answer(f"Наш номер для связи: {data['phone']}\nЗвоните, если у вас есть вопросы!", reply_markup=get_main_keyboard())
        return

    if text == "🛒 Сделать заказ":
        user_data[chat_id] = {"stage": "ordering", "cart": [], "total": 0}
        await message.answer("🛍️ Выберите блюда из меню:\n\nТекущая корзина: пусто\nИтог: 0 ₽", reply_markup=get_order_keyboard())
        return

    # --- КОРЗИНА ---
    if chat_id in user_data and user_data[chat_id].get("stage") == "ordering":
        cart = user_data[chat_id]["cart"]
        total = user_data[chat_id]["total"]

        for item in data["menu"]:
            if text == f"{item['name']} ({item['price']}₽)":
                cart.append(item['name'])
                total += item['price']
                break

        if text == "❌ Очистить корзину":
            cart = []
            total = 0
            user_data[chat_id]["cart"] = cart
            user_data[chat_id]["total"] = total
            await message.answer("🗑️ Корзина очищена.\n\nТекущая корзина: пусто\nИтог: 0 ₽", reply_markup=get_order_keyboard())
            return

        if text == "✅ Готово":
            if not cart:
                await message.answer("❌ Корзина пуста! Добавьте хотя бы одно блюдо.", reply_markup=get_order_keyboard())
                return
            user_data[chat_id]["stage"] = "waiting_phone"
            await message.answer(
                f"📦 Ваш заказ:\n" + "\n".join(f"• {item}" for item in cart) +
                f"\n\n💰 Итог: {total} ₽\n\n📞 Укажите ваш номер телефона (в формате 89991234567):",
                reply_markup=get_cancel_keyboard()
            )
            return

        user_data[chat_id]["cart"] = cart
        user_data[chat_id]["total"] = total
        cart_text = "пусто" if not cart else "\n".join(f"• {item}" for item in cart)
        await message.answer(f"✅ Добавлено!\n\nТекущая корзина:\n{cart_text}\nИтог: {total} ₽", reply_markup=get_order_keyboard())
        return

    # --- ОТМЕНА ---
    if text == "❌ Отмена":
        if user_data.get(chat_id, {}).get("stage") in ["admin_edit_item_name", "admin_edit_item_price", "admin_add_item_name", "admin_add_item_price", "admin_delete_item_select"]:
            user_data[chat_id] = {"stage": "admin_menu_edit"}
            await message.answer("Отмена. Возврат к редактированию меню.", reply_markup=get_menu_edit_keyboard())
        else:
            user_data[chat_id] = {"stage": "main"}
            await message.answer("Возвращаемся в главное меню.", reply_markup=get_main_keyboard())
        return

    # --- ТЕЛЕФОН ---
    if chat_id in user_data and user_data[chat_id].get("stage") == "waiting_phone":
        if text.isdigit() and len(text) == 11:
            user_data[chat_id]["phone"] = text
            user_data[chat_id]["stage"] = "waiting_address"
            await message.answer("📍 Теперь укажите адрес доставки:", reply_markup=get_cancel_keyboard())
        else:
            await message.answer("❌ Неверный формат. Введите 11 цифр (например, 89991234567)")
        return

    # --- АДРЕС (ФИНАЛ) ---
    if chat_id in user_data and user_data[chat_id].get("stage") == "waiting_address":
        address = text
        phone = user_data[chat_id].get("phone", "Не указан")
        cart = user_data[chat_id].get("cart", [])
        total = user_data[chat_id].get("total", 0)
        order_details = "\n".join(f"• {item}" for item in cart)

        order = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "details": order_details,
            "total": total,
            "phone": phone,
            "address": address
        }
        orders.append(order)
        save_orders(orders)

        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🆕 НОВЫЙ ЗАКАЗ!\n📦 Состав:\n{order_details}\n💰 Сумма: {total} ₽\n📞 Телефон: {phone}\n📍 Адрес: {address}"
        )

        user_data[chat_id] = {"stage": "main"}
        await message.answer("✅ Заказ принят! Наш оператор свяжется с вами для подтверждения.", reply_markup=get_main_keyboard())
        return

    # --- ChatGPT ---
    await chat_gpt(message)

# --- Вспомогательные функции ---

async def show_menu_edit(message: Message):
    menu_text = "\n".join([f"{i+1}. {item['name']} — {item['price']}₽" for i, item in enumerate(data["menu"])])
    await message.answer(f"📝 Текущее меню:\n{menu_text}\n\nВыберите действие:", reply_markup=get_menu_edit_keyboard())

async def show_menu(message: Message):
    menu_text = "\n".join([f"{item['name']} — {item['price']} руб." for item in data["menu"]])
    await message.answer(f"{menu_text}\n\n🚚 Доставка: {data['delivery']}", reply_markup=get_main_keyboard())

async def chat_gpt(message: Message):
    user_text = message.text
    chat_id = message.chat.id

    if chat_id not in chat_history:
        chat_history[chat_id] = [
            {"role": "system", "content": f"Ты помощник шаурмичной. Отвечай кратко по базе:\n"
                                          f"Адрес: {data['address']}\n"
                                          f"Телефон: {data['phone']}\n"
                                          f"График: {data['schedule']}\n"
                                          f"Доставка: {data['delivery']}\n"
                                          f"Меню: {', '.join([f'{item['name']} - {item['price']}₽' for item in data['menu']])}"}
        ]

    chat_history[chat_id].append({"role": "user", "content": user_text})

    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json',
    }
    data_payload = {
        'model': 'gpt-3.5-turbo',
        'messages': chat_history[chat_id],
        'max_tokens': 500
    }

    try:
        response = requests.post('https://api.proxyapi.ru/openai/v1/chat/completions', headers=headers, json=data_payload)
        response_json = response.json()
        bot_reply = response_json['choices'][0]['message']['content']
        chat_history[chat_id].append({"role": "assistant", "content": bot_reply})
        await message.answer(bot_reply, reply_markup=get_main_keyboard())
    except Exception as e:
        print(e)
        await message.answer("Извините, произошла заминка. Напишите нашему менеджеру @psi_blade", reply_markup=get_main_keyboard())

# --- ЗАПУСК ---

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())