import asyncio
from datetime import datetime, timezone
from typing import Union

from aiogram import Bot as AiogramBot, Dispatcher, types, exceptions
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from attention_sender import MESSAGE_LIFETIME
from attention_sender.utils import read_json
from attention_sender.db import DataBase


token = read_json("./creds/telegram.json").get("token")

bot = AiogramBot(token)
dp = Dispatcher()


async def do_bot_action_w_except(method_name: str, **kwargs) -> types.Message:
    """
    Универсальная обёртка над методами Bot с ретраями.

    method_name: имя метода бота, например "send_message", "delete_message".
    kwargs: аргументы, которые передаются в метод бота.
    """
    method = getattr(bot, method_name)
    delay = 1

    for attempt in range(5):
        try:
            return await method(**kwargs)
        except exceptions.RetryAfter as e:
            timeout = getattr(e, "timeout", delay)
            await asyncio.sleep(timeout)
        except exceptions.NetworkError:
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30)
        except exceptions.TelegramAPIError as e:
            print(f"Telegram API error in {method_name}: {e}")
            raise

    raise RuntimeError(f"Failed to perform bot action '{method_name}' after multiple attempts")


def _build_inline_keyboard(button_text: str, callback_data: str) -> InlineKeyboardMarkup:
    """
    Собираем простую inline-клавиатуру с одной кнопкой.
    """
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text=button_text, callback_data=callback_data))
    return keyboard


async def send_message_w_button(
    chat_id: int,
    message: str,
    btn_txt: str,
    shop_name: str,
    mes_type: str,
    order: Union[str, None],
) -> None:
    """
    Отправка сообщения с inline-кнопкой + сохранение в БД, если такого ещё не было.

    Обычно используется для «действуемых» сообщений (формула, фи, forbidden и т.п.),
    где юзер может нажать «Исправил».
    """
    order_id = order if order is not None else mes_type

    async with DataBase() as db:
        already_exists = await db.check_values_in_columns(
            shop_name=shop_name, message_type=mes_type, order_id=order_id
        )
        if already_exists:
            return

        callback_data = f"resolve:{shop_name}:{mes_type}:{order_id}"
        keyboard = _build_inline_keyboard(btn_txt, callback_data)

        mes = await do_bot_action_w_except(
            "send_message",
            chat_id=chat_id,
            text=message,
            reply_markup=keyboard,
            request_timeout=120,
        )
        await db.sent_mes_save(mes, shop_name, order_id, mes_type)


async def send_message(
    chat_id: int,
    message: str,
    shop_name: str,
    mes_type: str,
    order: str,
) -> None:
    """
    Отправка простого текстового сообщения + сохранение в БД,
    если такого ещё не отправляли (по shop_name + mes_type + order).
    """
    async with DataBase() as db:
        already_exists = await db.check_values_in_columns(
            shop_name=shop_name, message_type=mes_type, order_id=order
        )
        if already_exists:
            return

        mes = await do_bot_action_w_except(
            "send_message",
            chat_id=chat_id,
            text=message,
            request_timeout=120,
        )
        await db.sent_mes_save(mes, shop_name, order, mes_type)


async def delete_or_update_message(
    chat_id: int,
    message_id: int,
    message_date: Union[str, datetime],
) -> None:
    """
    Удаляет сообщение, если оно моложе MESSAGE_LIFETIME,
    иначе – правит текст на «Сообщение удалено».

    Используется:
    - когда проблема сама решилась в таблице (через Inspect._mes_deleter);
    - когда юзер нажимает на кнопку в самом Telegram.
    """
    if isinstance(message_date, str):
        dt = None
        try:
            dt = datetime.fromisoformat(message_date)
        except ValueError:
            pass

        if dt is None:
            try:
                dt = datetime.strptime(message_date, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                dt = datetime.utcnow()

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = message_date
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

    age = datetime.now(timezone.utc) - dt

    if age < MESSAGE_LIFETIME:
        try:
            await do_bot_action_w_except(
                "delete_message",
                chat_id=chat_id,
                message_id=message_id,
                request_timeout=120,
            )
        except exceptions.MessageToDeleteNotFound:
            pass
    else:
        try:
            await do_bot_action_w_except(
                "edit_message_text",
                chat_id=chat_id,
                message_id=message_id,
                text="Сообщение удалено",
                request_timeout=120,
            )
        except exceptions.MessageCantBeEdited:
            pass


@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message) -> None:
    """
    Простейший /start – полезно, когда смотришь бота отдельно.
    """
    await message.answer(
        "👋 Привет! Я бот-ассистент для мониторинга таблиц в Google Sheets.\n"
        "Сообщения здесь появляются автоматически, когда в таблицах находят проблемы."
    )


@dp.callback_query_handler(lambda c: c.data and c.data.startswith("resolve:"))
async def process_resolve_callback(callback: types.CallbackQuery) -> None:
    """
    Обработчик нажатия на inline-кнопки, созданные send_message_w_button.

    Формат callback_data:
        resolve:<shop_name>:<mes_type>:<order_id>
    """
    try:
        _, shop_name, mes_type, order_id = callback.data.split(":", 3)
    except ValueError:
        await callback.answer("Некорректные данные кнопки", show_alert=False)
        return

    await delete_or_update_message(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        message_date=callback.message.date,
    )

    async with DataBase() as db:
        try:
            await db.delete_message(
                message_id=callback.message.message_id,
                chat_id=callback.message.chat.id,
            )
        except Exception as e:
            print(f"Failed to delete DB record for resolved message: {e}")

    await callback.answer("Отмечено как исправлено ✅")


Bot = AiogramBot
