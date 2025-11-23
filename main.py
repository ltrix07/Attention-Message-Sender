# main.py
import asyncio
import time
import sys
from typing import Callable, Awaitable

from google_sheets_utils.buid import GoogleSheets
from googleapiclient.errors import HttpError
from google.auth.exceptions import TransportError

from attention_sender.collector import Collector
from attention_sender.telegram_bot import dp, Bot
from attention_sender.utils import read_json
from attention_sender.inspections import Inspect
from attention_sender.config import settings

sys.stdout.reconfigure(encoding="utf-8")


async def start_bot() -> None:
    """
    Starts Telegram bot polling using token from credentials.
    """
    token = read_json(settings.paths.telegram_creds.as_posix()).get("token")
    bot = Bot(token)
    await dp.start_polling(bot)


async def retry_request(
    func: Callable[[], Awaitable],
    retries: int = 3,
    delay: int = 2,
):
    """
    Wrapper for retrying async Google API calls with exponential backoff.
    """
    for attempt in range(retries):
        try:
            result = func()
            if asyncio.iscoroutine(result):
                return await result
            return result
        except (HttpError, TransportError, TimeoutError) as e:
            print(f"Ошибка запроса: {e}. Попытка {attempt + 1}/{retries}")
            if attempt < retries - 1:
                await asyncio.sleep(delay * (2**attempt))
            else:
                raise


async def sheet_look(
    inspector: Inspect,
    google: GoogleSheets,
    table_inf: dict,
    worksheet: str,
    ch_problem: int,
    ch_attention: int,
    shop_name: str,
) -> None:
    """
    Fetches sheet data, filters columns and runs inspections/attentions.
    """
    table_id = table_inf.get("table_id")
    columns = table_inf.get("columns")

    d_from_sheet = await retry_request(
        lambda: google.get_all_info_from_sheet(table_id, worksheet)
    )
    try:
        indices = google.get_columns_indices(d_from_sheet, columns)
        d_by_indices = inspector.filter_data_by_indices(d_from_sheet, indices)
    except (KeyError, IndexError):
        return

    await inspector.check_problems(d_by_indices, ch_problem, shop_name, worksheet)
    await inspector.check_attentions(d_by_indices, ch_attention, shop_name, worksheet)


async def look_table(
    g_creds_ph: str,
    chat_data: dict,
    shop_name: str,
    table_inf: dict,
    staff_ph: str,
) -> None:
    shop_name_cap = shop_name.capitalize()
    collector = Collector()
    g_api = GoogleSheets(g_creds_ph)
    inspector = Inspect(staff_ph)

    table_id = table_inf.get("table_id")
    sheets = await retry_request(lambda: g_api.get_sheets_name(table_id))

    now_m, prev_m = await collector.define_months()
    chat_problems = chat_data.get("chat_w_problems")
    chat_attention = chat_data.get("chat_w_attentions")

    has_current_month = await inspector.now_m_in_sheet(
        shop_name_cap, chat_problems, sheets, now_m
    )
    if not has_current_month:
        return

    # порядок листов: текущий, предыдущий и спец-префиксы
    candidate_sheets = [
        now_m,
        prev_m,
        f"azat_{now_m}",
        f"azat_{prev_m}",
        f"bro_{now_m}",
        f"bro_{prev_m}",
    ]

    for sheet in candidate_sheets:
        if str(sheet) in sheets:
            await sheet_look(
                inspector,
                g_api,
                table_inf,
                worksheet=str(sheet),
                ch_problem=chat_problems,
                ch_attention=chat_attention,
                shop_name=shop_name_cap,
            )
            break


async def process_loop() -> None:
    """
    Main loop: iterates over shops and processes their sheets in cycles.
    """
    spreadsheets = read_json(settings.paths.spreadsheets.as_posix())
    chat_data = read_json(settings.paths.chat_data.as_posix())
    g_creds_ph = settings.paths.google_creds.as_posix()
    staff_ph = settings.paths.staff.as_posix()

    while True:
        start_t = time.time()
        for shop_name, table_info in spreadsheets.items():
            print(f"Обрабатываю: {shop_name}")
            try:
                await retry_request(
                    lambda: look_table(
                        g_creds_ph=g_creds_ph,
                        chat_data=chat_data,
                        shop_name=shop_name,
                        table_inf=table_info,
                        staff_ph=staff_ph,
                    )
                )
            except Exception as e:
                print(f"Ошибка при обработке {shop_name}: {e}")
            await asyncio.sleep(5)
        print(f"Цикл занял {time.time() - start_t:.2f} секунд")


async def main() -> None:
    """
    Entry point: runs Telegram bot and processing loop in parallel.
    """
    print("Запуск бота и программы")
    task_bot = asyncio.create_task(start_bot())
    task_process = asyncio.create_task(process_loop())
    await asyncio.gather(task_bot, task_process)


if __name__ == "__main__":
    asyncio.run(main())
