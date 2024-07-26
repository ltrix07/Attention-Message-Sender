import asyncio

from attention_sender.utils import read_json
from attention_sender.db import DataBase
from aiogram import Bot, Dispatcher, types, exceptions
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


db = DataBase('./cech/messages.db')
token = read_json('./creds/telegram.json').get('token')
bot = Bot(token)
dp = Dispatcher()


async def do_bot_action_w_except(bot: Bot, method_name: str, retries: int = 5, **kwargs):
    for attempt in range(retries):
        try:
            method = getattr(bot, method_name)
            result = await method(**kwargs)
            return result
        except exceptions.TelegramNetworkError as err:
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
            else:
                raise err


@dp.callback_query(lambda c: c.data == 'button_click_del')
async def callback_button_delete(callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.message_id
    await do_bot_action_w_except(
        bot, 'delete_message', chat_id=chat_id, message_id=message_id, request_timeout=120)
    db.delete_message(chat_id=chat_id, message_id=message_id)


async def send_message_w_button(
        chat_id: int, message: str, button_text: str, shop_name: str, mes_type: str, order: str | None
) -> None:
    if not db.check_values_in_columns(shop_name=shop_name, message_type=mes_type):
        button = InlineKeyboardButton(text=button_text, callback_data='button_click_del')
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])
        mes = await do_bot_action_w_except(
            bot, 'send_message', chat_id=chat_id, text=message, reply_markup=keyboard, request_timeout=120)
        db.sent_mes_save(mes, shop_name, order, mes_type)


async def send_message(
        chat_id: int, message: str, shop_name: str, mes_type: str, order: str
) -> None:
    if not db.check_values_in_columns(shop_name=shop_name, message_type=mes_type, order_id=order):
        mes = await do_bot_action_w_except(
            bot, 'send_message', chat_id=chat_id, text=message, request_timeout=120
        )
        db.sent_mes_save(mes, shop_name, order, mes_type)


async def delete_message(chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id, message_id, request_timeout=120)
    except exceptions.TelegramBadRequest as error:
        if 'message to delete not found' in str(error):
            pass
    db.delete_message(chat_id=chat_id, message_id=message_id)
