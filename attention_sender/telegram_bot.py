import aiogram.exceptions

from attention_sender.utils import read_json
from attention_sender.db import DataBase
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


db = DataBase('./cech/messages.db')
token = read_json('./creds/telegram.json').get('token')
bot = Bot(token)
dp = Dispatcher()


@dp.callback_query(lambda c: c.data == 'button_click_del')
async def callback_button_delete(callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.message_id
    await bot.delete_message(chat_id, message_id)
    db.delete_message(chat_id=chat_id, message_id=message_id)


async def send_message_w_button(
        chat_id: int, message: str, button_text: str, shop_name: str, mes_type: str, order: str | None
) -> None:
    if not db.check_values_in_columns(shop_name=shop_name, message_type=mes_type):
        button = InlineKeyboardButton(text=button_text, callback_data='button_click_del')
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])
        mes = await bot.send_message(chat_id, message, reply_markup=keyboard)
        db.sent_mes_save(mes, shop_name, order, mes_type)


async def send_message(
        chat_id: int, message: str, shop_name: str, mes_type: str, order: str
) -> None:
    if not db.check_values_in_columns(shop_name=shop_name, message_type=mes_type, order_id=order):
        mes = await bot.send_message(chat_id, message)
        db.sent_mes_save(mes, shop_name, order, mes_type)


async def delete_message(chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id, message_id)
    except aiogram.exceptions.TelegramBadRequest as error:
        if 'message to delete not found' in str(error):
            pass
    db.delete_message(chat_id=chat_id, message_id=message_id)
