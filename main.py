import asyncio
import time
import sys
from google_sheets_utils.buid import GoogleSheets
from attention_sender.collector import Collector
from attention_sender.telegram_bot import dp, Bot
from attention_sender.utils import read_json
from attention_sender.inspections import Inspect
from googleapiclient.errors import HttpError
from google.auth.exceptions import TransportError

sys.stdout.reconfigure(encoding='utf-8')


async def start_bot():
    token = read_json('./creds/telegram.json').get('token')
    bot = Bot(token)
    await dp.start_polling(bot)


async def retry_request(coro, retries=3, delay=2):
    for attempt in range(retries):
        try:
            result = coro()
            if asyncio.iscoroutine(result):
                return await result
            return result
        except (HttpError, TransportError, TimeoutError) as e:
            print(f"Ошибка запроса: {e}. Попытка {attempt + 1}/{retries}")
            if attempt < retries - 1:
                await asyncio.sleep(delay * (2 ** attempt))  # Экспоненциальная задержка
            else:
                raise


async def sheet_look(inspector: Inspect, google: GoogleSheets, table_inf, worksheet,
                     ch_problem, ch_attention, shop_name) -> None:
    table_id = table_inf.get('table_id')
    columns = table_inf.get('columns')
    d_from_sheet = await retry_request(lambda: google.get_all_info_from_sheet(table_id, worksheet))
    try:
        indices = google.get_columns_indices(d_from_sheet, columns)
        d_by_indices = inspector.filter_data_by_indices(d_from_sheet, indices)
    except (KeyError, IndexError):
        return
    await inspector.check_problems(d_by_indices, ch_problem, shop_name, worksheet)
    await inspector.check_attentions(d_by_indices, ch_attention, shop_name, worksheet)


async def look_table(g_creds_ph: str, chat_data: dict, shop_name: str, table_inf: dict, staff_ph: str):
    shop_name = shop_name.capitalize()
    collector = Collector()
    g_api = GoogleSheets(g_creds_ph)
    inspector = Inspect(staff_ph)

    table_id = table_inf.get('table_id')

    sheets = await retry_request(lambda: g_api.get_sheets_name(table_id))
    now_m, prev_m = await collector.define_months()
    chat_problems = chat_data.get('chat_w_problems')
    chat_attention = chat_data.get('chat_w_attentions')

    insp = await inspector.now_m_in_sheet(shop_name, chat_problems, sheets, now_m)
    if insp:
        for sheet in [now_m, prev_m, f'azat_{now_m}', f'azat_{prev_m}', f'bro_{now_m}', f'bro_{prev_m}']:
            if str(sheet) in sheets:
                await sheet_look(inspector, g_api, table_inf, sheet, chat_problems, chat_attention, shop_name)
                break


async def process(staff_ph: str, spreadsheets_ph: str, chat_data_ph: str, google_creds_ph: str):
    spreadsheets = read_json(spreadsheets_ph)
    chat_data = read_json(chat_data_ph)

    while True:
        start_t = time.time()
        for shop_name, table_info in spreadsheets.items():
            print(f'Обрабатываю: {shop_name}')
            try:
                await retry_request(lambda: look_table(google_creds_ph, chat_data, shop_name, table_info, staff_ph))
            except Exception as e:
                print(f'Ошибка при обработке {shop_name}: {e}')
            await asyncio.sleep(5)
        print(f'Цикл занял {time.time() - start_t} секунд')


async def main(staff_ph: str, spreadsheets_ph: str, chat_data_ph: str, google_creds_ph: str):
    task_look = asyncio.create_task(process(staff_ph, spreadsheets_ph, chat_data_ph, google_creds_ph))
    print('Запуск бота и программы')
    task_bot = asyncio.create_task(start_bot())
    await asyncio.gather(task_bot, task_look)


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main(
            './db/staff.json',
            './db/spreadsheets.json',
            './db/chat_data.json',
            './creds/google_creds.json'
        ))
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
