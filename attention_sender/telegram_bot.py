import asyncio
import random
from datetime import datetime, timezone
from typing import Union

from aiogram import Bot, Dispatcher, types, exceptions
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from attention_sender import MESSAGE_LIFETIME
from attention_sender.config import settings
from attention_sender.utils import read_json
from attention_sender.db import DataBase


_token_data = read_json(settings.paths.telegram_creds.as_posix())
TOKEN = _token_data.get("token")

bot = Bot(TOKEN)
dp = Dispatcher()


async def do_bot_action_w_except(method_name: str, **kwargs) -> types.Message:
    """
    Wrapper around bot methods with retry logic for common Telegram errors.
    method_name: e.g. 'send_message', 'edit_message_text', 'delete_message'
    """
    method = getattr(bot, method_name)

    delay = 1
    for attempt in range(5):
        try:
            return await method(**kwargs)
        except exceptions.RetryAfter as e:
            # flood control
            retry_after = getattr(e, "timeout", delay)
            await asyncio.sleep(retry_after)
        except exceptions.NetworkError:
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30)
        except exceptions.TelegramAPIError as e:
            print(f"Telegram API error in {method_name}: {e}")
            raise
    raise RuntimeError(f"Failed to perform {method_name} after multiple attempts")


def _build_inline_keyboard(button_text: str, callback_data: str) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text=button_text, callback_data=callback_data))
    return keyboard


async def send_message_w_button(
    chat_id: int,
    message: str,
    shop_name: str,
    mes_type: str,
    order: str,
    button_text: str,
    callback_data: str,
) -> None:
    """
    Send message with inline button and save it in DB if not sent before.
    """
    async with DataBase() as db:
        already_exists = await db.check_values_in_columns(
            shop_name=shop_name, message_type=mes_type, order_id=order
        )
        if already_exists:
            return

        keyboard = _build_inline_keyboard(button_text, callback_data)
        mes = await do_bot_action_w_except(
            "send_message",
            chat_id=chat_id,
            text=message,
            reply_markup=keyboard,
            request_timeout=120,
        )
        await db.sent_mes_save(mes, shop_name, order, mes_type)


async def send_message(
    chat_id: int, message: str, shop_name: str, mes_type: str, order: str
) -> None:
    """
    Send plain message and save it in DB if not sent before.
    """
    async with DataBase() as db:
        already_exists = await db.check_values_in_columns(
            shop_name=shop_name, message_type=mes_type, order_id=order
        )
        if already_exists:
            return

        mes = await do_bot_action_w_except(
            "send_message", chat_id=chat_id, text=message, request_timeout=120
        )
        await db.sent_mes_save(mes, shop_name, order, mes_type)


async def delete_or_update_message(
    message_id: int,
    chat_id: int,
    message_date: Union[str, datetime],
) -> None:
    """
    Delete message if it's younger than MESSAGE_LIFETIME,
    otherwise update its text to 'Сообщение удалено'.
    """
    if not isinstance(message_date, datetime):
        message_date = datetime.strptime(message_date, "%Y-%m-%d %H:%M:%S%z")

    age = datetime.now(timezone.utc) - message_date

    if age < MESSAGE_LIFETIME:
        try:
            await do_bot_action_w_except(
                "delete_message",
                chat_id=chat_id,
                message_id=message_id,
                request_timeout=120,
            )
        except exceptions.TelegramBadRequest as error:
            if "message to delete not found" in str(error):
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
        except exceptions.TelegramBadRequest:
            # message might be already modified or deleted
            pass
