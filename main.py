import asyncio
import logging
import sys
import time
from typing import Any, Dict

from attention_sender.collector import Collector
from attention_sender.telegram_bot import bot, dp
from attention_sender.utils import read_json
from attention_sender.inspections import Inspect
from attention_sender.config import settings
from attention_sender.google_client import GoogleSheetsClient

sys.stdout.reconfigure(encoding="utf-8")


async def start_bot() -> None:
    """
    Start Telegram bot polling.

    Bot instance and dispatcher are created in attention_sender.telegram_bot.
    """
    await dp.start_polling(bot)


async def run_blocking(func, *args, **kwargs):
    """
    Run a blocking function in a separate thread, returning its result.

    This is used to call Google Sheets API methods from async code without
    blocking the event loop.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


async def sheet_look(
    inspector: Inspect,
    google: GoogleSheetsClient,
    table_conf: Dict[str, Any],
    worksheet: str,
    chat_problems: int,
    chat_attentions: int,
    shop_name: str,
) -> None:
    """
    Fetch data for a single worksheet and run all inspections on it.

    :param inspector: Inspect instance with business rules
    :param google: GoogleSheetsClient instance
    :param table_conf: configuration for the shop (table_id, columns mapping)
    :param worksheet: worksheet (tab) name to read
    :param chat_problems: Telegram chat id for problem notifications
    :param chat_attentions: Telegram chat id for attention notifications
    :param shop_name: shop name (used in messages and DB)
    """
    table_id = table_conf.get("table_id")
    columns_cfg = table_conf.get("columns", {})

    # Fetch all rows from sheet
    raw_data = await run_blocking(
        google.get_all_info_from_sheet, table_id, worksheet
    )
    try:
        indices = google.get_columns_indices(raw_data, columns_cfg)
        filtered_data = inspector.filter_data_by_indices(raw_data, indices)
    except (KeyError, IndexError) as exc:
        # Misconfigured columns or malformed sheet header
        logging.warning(
            "Failed to map columns for shop '%s' sheet '%s': %s",
            shop_name,
            worksheet,
            exc,
        )
        return

    # Run problem checks and attention checks
    await inspector.check_problems(filtered_data, chat_problems, shop_name, worksheet)
    await inspector.check_attentions(filtered_data, chat_attentions, shop_name, worksheet)


async def look_table(
    g_creds_ph: str,
    chat_data: Dict[str, Any],
    shop_name: str,
    table_conf: Dict[str, Any],
    staff_ph: str,
) -> None:
    """
    Process all relevant sheets for a single shop.

    It:
      - builds GoogleSheetsClient and Inspect instances,
      - reads list of worksheet titles,
      - checks if current month sheet exists (and access is ok),
      - runs inspections for current/previous-month-related sheets.
    """
    shop_name_cap = shop_name.capitalize()
    collector = Collector()
    google = GoogleSheetsClient(g_creds_ph)
    inspector = Inspect(staff_ph)

    table_id = table_conf.get("table_id")
    sheets = await run_blocking(google.get_sheets_name, table_id)

    now_m, prev_m = await collector.define_months()

    chat_problems = chat_data.get("chat_w_problems")
    chat_attentions = chat_data.get("chat_w_attentions")

    # Check that we have access and current month sheet
    has_current_month = await inspector.now_m_in_sheet(
        shop_name_cap,
        chat_problems,
        sheets,
        now_m,
    )
    if not has_current_month:
        return

    # Candidate sheets to inspect (order matters)
    candidate_sheets = [
        str(now_m),
        str(prev_m),
        f"azat_{now_m}",
        f"azat_{prev_m}",
        f"bro_{now_m}",
        f"bro_{prev_m}",
    ]

    for sheet in candidate_sheets:
        if sheet in sheets:
            await sheet_look(
                inspector=inspector,
                google=google,
                table_conf=table_conf,
                worksheet=sheet,
                chat_problems=chat_problems,
                chat_attentions=chat_attentions,
                shop_name=shop_name_cap,
            )
            # Stop after the first matching sheet
            break


async def process_loop() -> None:
    """
    Main processing loop.

    Iterates over all shops from spreadsheets.json and runs inspections
    in continuous cycles.
    """
    spreadsheets = read_json(settings.paths.spreadsheets.as_posix())
    chat_data = read_json(settings.paths.chat_data.as_posix())
    g_creds_ph = settings.paths.google_creds.as_posix()
    staff_ph = settings.paths.staff.as_posix()

    while True:
        start_t = time.time()
        for shop_name, table_conf in spreadsheets.items():
            logging.info("Processing shop: %s", shop_name)
            try:
                await look_table(
                    g_creds_ph=g_creds_ph,
                    chat_data=chat_data,
                    shop_name=shop_name,
                    table_conf=table_conf,
                    staff_ph=staff_ph,
                )
            except Exception as exc:
                logging.exception("Error while processing shop '%s': %s", shop_name, exc)
            # Small delay between shops to avoid hammering the API
            await asyncio.sleep(5)

        cycle_duration = time.time() - start_t
        logging.info("Cycle finished in %.2f seconds", cycle_duration)


async def main() -> None:
    """
    Entry point for the application.

    Runs Telegram bot polling and processing loop in parallel.
    """
    logging.info("Starting bot and processing loop")
    task_bot = asyncio.create_task(start_bot())
    task_process = asyncio.create_task(process_loop())
    await asyncio.gather(task_bot, task_process)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Shutting down on KeyboardInterrupt")
