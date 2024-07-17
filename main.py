import asyncio
import time
from google_sheets_utils.buid import GoogleSheets
from attention_sender.collector import Collector
from attention_sender.telegram_bot import dp, Bot
from attention_sender.utils import read_json
from attention_sender.inspections import Inspect


async def start_bot():
    token = read_json('./creds/telegram.json').get('token')
    bot = Bot(token)
    await dp.start_polling(bot)


async def sheet_look(
        inspector: Inspect, google: GoogleSheets, table_inf, worksheet, ch_problem, ch_attention, shop_name
) -> None:
    table_id = table_inf.get('table_id')
    columns = table_inf.get('columns')
    d_from_sheet: list | dict = google.get_all_info_from_sheet(table_id, worksheet)
    try:
        indices = google.get_columns_indices(d_from_sheet, columns)
        d_by_indices = await inspector.filter_data_by_indices(d_from_sheet, indices)
    except KeyError:
        return
    except IndexError:
        return
    await inspector.check_problems(d_by_indices, ch_problem, shop_name, worksheet)
    await inspector.check_attentions(d_by_indices, ch_attention, shop_name, worksheet)


async def look_table(g_creds_ph: str, chat_data: dict, shop_name: str, table_inf: dict, staff_ph: str):
    shop_name = shop_name.capitalize()
    collector = Collector()
    g_api = GoogleSheets(g_creds_ph)
    inspector = Inspect(staff_ph)

    table_id = table_inf.get('table_id')

    sheets = g_api.get_sheets_name(table_id)
    now_m, prev_m = collector.define_months()
    chat_problems = chat_data.get('chat_w_problems')
    chat_attention = chat_data.get('chat_w_attentions')

    insp = await inspector.now_m_in_sheet(shop_name, chat_problems, sheets, now_m)
    if insp:
        if str(now_m) in sheets:
            await sheet_look(inspector, g_api, table_inf, now_m, chat_problems, chat_attention, shop_name)
        elif str(prev_m) in sheets:
            await sheet_look(inspector, g_api, table_inf, prev_m, chat_problems, chat_attention, shop_name)
        elif f'azat_{now_m}' in sheets:
            await sheet_look(inspector, g_api, table_inf, f'azat_{now_m}', chat_problems, chat_attention, shop_name)
        elif f'azat_{prev_m}' in sheets:
            await sheet_look(inspector, g_api, table_inf, f'azat_{prev_m}', chat_problems, chat_attention, shop_name)
        elif f'bro_{now_m}' in sheets:
            await sheet_look(inspector, g_api, table_inf, f'bro_{now_m}', chat_problems, chat_attention, shop_name)
        elif f'bro_{prev_m}' in sheets:
            await sheet_look(inspector, g_api, table_inf, f'bro_{prev_m}', chat_problems, chat_attention, shop_name)


async def process(
        staff_ph: str, spreadsheets_ph: str, chat_data_ph: str, google_creds_ph: str
):
    spreadsheets = read_json(spreadsheets_ph)
    chat_data = read_json(chat_data_ph)

    while True:
        start_t = time.time()
        for shop_name, table_info in spreadsheets.items():
            await look_table(
                google_creds_ph, chat_data, shop_name, table_info, staff_ph
            )
            await asyncio.sleep(5)
        end_t = time.time()
        print(end_t - start_t)


async def main(
        staff_ph: str, spreadsheets_ph: str, chat_data_ph: str,
        google_creds_ph: str
):
    task_look = asyncio.create_task(process(
        staff_ph, spreadsheets_ph, chat_data_ph, google_creds_ph
    ))
    print('Запуск бота и программы')
    task_bot = asyncio.create_task(start_bot())
    await asyncio.gather(task_bot, task_look)


if __name__ == '__main__':
    asyncio.run(main(
        './db/staff.json',
        './db/spreadsheets.json',
        './db/chat_data.json',
        './creds/google_creds.json'
    ))
