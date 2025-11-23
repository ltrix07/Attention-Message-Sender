# attention_sender/utils.py
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from attention_sender.config import settings


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def read_json(file_path: str) -> Dict[str, Any]:
    """
    Read JSON file and return its content as a dict.

    :param file_path: path to JSON file
    """
    path = Path(file_path)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(file_path: str, data: Dict[str, Any]) -> None:
    """
    Write dict data to JSON file with indentation.

    :param file_path: path to JSON file
    :param data: dictionary to be dumped into file
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def today_or_not(date: str, date_format: str = "%d.%m.%Y %H:%M:%S") -> bool:
    """
    Check if the given date string corresponds to today's date.

    :param date: date string from Google Sheets
    :param date_format: expected format of the date string
    :return: True if date is today, False otherwise (or on parse error)
    """
    try:
        date_obj = datetime.strptime(date, date_format)
    except (ValueError, TypeError):
        return False

    today = datetime.now()
    return date_obj.date() == today.date()


# ---------------------------------------------------------------------------
# Message builders
# All functions below return ready-to-send Russian text for Telegram.
# ---------------------------------------------------------------------------

def message_no_sheet(workers: str, shop: str) -> str:
    """
    Build message about missing current month sheet.
    """
    return (
        f"{workers}\n"
        f"В таблице \"{shop}\" нет листа с текущим месяцем."
    )


def message_forbidden(workers: str, shop: str) -> str:
    """
    Build message about missing access to Google Sheet.
    """
    g_creds = read_json(settings.paths.google_creds.as_posix())
    serv_email = g_creds.get("client_email", "SERVICE_ACCOUNT_EMAIL_NOT_FOUND")

    return (
        f"{workers}\n"
        f"У бота нет доступа к таблице \"{shop}\".\n"
        f"Нужно выдать доступ для почты сервисного аккаунта:\n\n"
        f"{serv_email}"
    )


def message_formula_check(workers: str, shop: str, sheet: str) -> str:
    """
    Build message asking to check formulas on a specific sheet.
    """
    return (
        f"{workers}\n"
        f"На магазине \"{shop}\" нужно проверить формулы.\n"
        f"Лист: \"{sheet}\""
    )


def message_need_fee_update(workers: str, shop: str) -> str:
    """
    Build message about outdated or missing fee values.
    """
    return (
        f"{workers}\n"
        f"На магазине \"{shop}\" нужно обновить fee."
    )


def message_no_scraping_price(workers: str, shop: str) -> str:
    """
    Build message about missing prices from scraper (buy_price is empty).
    """
    return (
        f"{workers}\n"
        f"На магазине \"{shop}\" скрипт не тянет цены. "
        f"Много заказов без покупной цены при наличии поставщика."
    )


def message_no_collection_supp(workers: str, shop: str) -> str:
    """
    Build message about missing suppliers collection (supplier_link is empty).
    """
    return (
        f"{workers}\n"
        f"На магазине \"{shop}\" не собираются поставщики (пустой supplier_link "
        f"у большого числа сегодняшних заказов)."
    )


def message_bad_price(
    workers: str,
    order: str,
    prof_amount: str,
    prof: float,
    shop: str,
    sheet: str,
) -> str:
    """
    Build message about too large negative profit (bad price).
    """
    return (
        f"{workers}\n"
        f"❗️Слишком большой минус по заказу.\n\n"
        f"Заказ: {order}\n"
        f"Прибыль: {prof_amount} ({prof}%)\n\n"
        f"🏪 Магазин: {shop}\n"
        f"📁 Лист: {sheet}"
    )


def message_bad_supplier(
    workers: str,
    shop: str,
    order: str,
    sheet: str,
) -> str:
    """
    Build message about forbidden supplier / item marked as 'ЗАПРЕЩЕНКА!'.
    """
    return (
        f"{workers}\n"
        f"❗️Обнаружена ЗАПРЕЩЕНКА!\n\n"
        f"Заказ: {order}\n"
        f"🏪 Магазин: {shop}\n"
        f"📁 Лист: {sheet}"
    )


def message_inspect_checker(
    workers: str,
    shop: str,
    orders_today: int,
    no_stock_qty: int,
) -> str:
    """
    Build message about possible checker malfunction
    (too many 'No stock' among today's orders).
    """
    return (
        f"{workers}\n"
        f"На магазине \"{shop}\", скорее всего, не работает чекер.\n"
        f"Всего ордеров за сегодня: {orders_today}\n"
        f"Из них No stock: {no_stock_qty}\n"
    )


def message_attention(
    workers: str,
    buy_date: str,
    status: str,
    order: str,
    shop_name: str,
    sheet_name: str,
    worker_type: str,
) -> str:
    """
    Build attention message for specific status (e.g. 'Срочно проблема').
    """
    return (
        f"{workers}\n"
        f"❗️{status}\n\n"
        f"{order}\n\n"
        f"📅 {buy_date}\n"
        f"👨‍💻 {worker_type.capitalize()}\n"
        f"🏪 {shop_name}\n"
        f"📁 {sheet_name}"
    )
