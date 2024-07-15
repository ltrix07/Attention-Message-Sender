import asyncio
from attention_sender.inspections import Inspect
from attention_sender.telegram_bot import Telegram
from attention_sender.utils import read_json


async def test_now_m_in_sheet():
    inspect = Inspect(r'C:\Users\Владимир\PycharmProjects\Attention-Message-Sender\db\staff.json')
    bot = Telegram(r'C:\Users\Владимир\PycharmProjects\Attention-Message-Sender\creds\telegram.json')
    chat_data = read_json(r'C:\Users\Владимир\PycharmProjects\Attention-Message-Sender\db\chat_data.json')
    chat_id = chat_data.get('chat_w_problems')
    await inspect.now_m_in_sheet(bot, 'test', chat_id, ['lost', 'top'], 7)

asyncio.run(test_now_m_in_sheet())
