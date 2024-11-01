import asyncio
import random
from datetime import datetime
from attention_sender import MESSAGE_LIFETIME
from attention_sender.utils import read_json
from attention_sender.db import DataBase
from aiogram import Bot, Dispatcher, types, exceptions
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


token = read_json('./creds/telegram.json').get('token')
bot = Bot(token)
dp = Dispatcher()


async def do_bot_action_w_except(method_name: str, retries: int = 10, **kwargs):
    for attempt in range(retries):
        try:
            method = getattr(bot, method_name)
            result = await method(**kwargs)
            return result
        except exceptions.TelegramNetworkError as err:
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt + random.uniform(0, 1))
            else:
                print(f"Exceeded retries for {method_name}: {err}")
                raise err


async def delete_or_update_message(chat_id: int, message_id: int, message_date: datetime) -> None:
    if datetime.now() - message_date < MESSAGE_LIFETIME:
        try:
            await do_bot_action_w_except('delete_message', chat_id=chat_id, message_id=message_id, request_timeout=120)
        except exceptions.TelegramBadRequest as error:
            if 'message to delete not found' in str(error):
                pass
    else:
        try:
            await do_bot_action_w_except('edit_message_text', chat_id=chat_id, message_id=message_id,
                                         text="Сообщение удалено", request_timeout=120)
        except exceptions.TelegramBadRequest as error:
            if 'message can\'t be edited' in str(error):
                pass
    # Удаляем запись из базы данных
    async with DataBase() as db:
        await db.delete_message(chat_id=chat_id, message_id=message_id)


@dp.callback_query(lambda c: c.data == 'button_click_del')
async def callback_button_delete(callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.message_id
    message_date = callback_query.message.date

    await delete_or_update_message(chat_id, message_id, message_date)


async def send_message_w_button(
        chat_id: int, message: str, button_text: str, shop_name: str, mes_type: str, order: str | None
) -> None:
    async with DataBase() as db:
        if not await db.check_values_in_columns(shop_name=shop_name, message_type=mes_type):
            button = InlineKeyboardButton(text=button_text, callback_data='button_click_del')
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])
            mes = await do_bot_action_w_except(
                'send_message', chat_id=chat_id, text=message, reply_markup=keyboard, request_timeout=120)
            await db.sent_mes_save(mes, shop_name, order, mes_type)


async def send_message(
        chat_id: int, message: str, shop_name: str, mes_type: str, order: str
) -> None:
    async with DataBase() as db:
        if not await db.check_values_in_columns(shop_name=shop_name, message_type=mes_type, order_id=order):
            mes = await do_bot_action_w_except(
                'send_message', chat_id=chat_id, text=message, request_timeout=120
            )
            await db.sent_mes_save(mes, shop_name, order, mes_type)
