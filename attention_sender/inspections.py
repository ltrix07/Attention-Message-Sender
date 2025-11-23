import logging
from datetime import datetime
from typing import Callable, Union, List, Optional, Dict, Any

from attention_sender.utils import (
    read_json,
    message_bad_price,
    message_attention,
    message_no_sheet,
    message_forbidden,
    message_formula_check,
    message_need_fee_update,
    today_or_not,
    message_no_scraping_price,
    message_no_collection_supp,
    message_bad_supplier,
    message_inspect_checker,
)
from attention_sender import TIME_TRIGGER
from attention_sender.telegram_bot import (
    delete_or_update_message,
    send_message_w_button,
    send_message,
)
from attention_sender.db import DataBase
from attention_sender.errors import google_sheet_err_proc


logger = logging.getLogger(__name__)


class Inspect:
    """
    Core inspection / rules engine.

    Responsibilities:
      - Analyse order data (dict[column_name] -> list of values),
      - Apply business rules (bad price, forbidden, missing sheet, checker, fee, No stock, etc.),
      - Send messages to Telegram and persist them in DB,
      - Remove/update messages when the underlying problem disappears.
    """

    def __init__(self, staff_data_ph: str) -> None:
        """
        :param staff_data_ph: path to JSON file with staff roles
                              (mapping role -> list of @usernames)
        """
        self.logger = logger
        self.staff: Dict[str, List[str]] = read_json(staff_data_ph)

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    async def _collect_workers(
        self, workers_type: Optional[Union[str, List[str]]] = "all"
    ) -> str:
        """
        Build a string with staff mentions for a given set of roles.

        :param workers_type:
          - "all" → join all roles from self.staff
          - list[str] → join only selected roles
        :return: comma-separated string with @usernames
        """
        if not self.staff:
            return ""

        if workers_type == "all":
            all_workers: List[str] = []
            for users in self.staff.values():
                all_workers.extend(users)
            return ", ".join(all_workers)

        workers_str_parts: List[str] = []
        if isinstance(workers_type, list):
            for worker_role in workers_type:
                users = self.staff.get(worker_role, [])
                if users:
                    workers_str_parts.append(", ".join(users))
        return ", ".join(workers_str_parts)

    async def _mes_sender_bp(
        self,
        order: str,
        prof_amount: str,
        prof: float,
        shop: str,
        sheet: str,
        chat_id: int,
    ) -> None:
        """
        Send a bad price message (high negative profit).
        """
        workers_str = await self._collect_workers(
            ["analysts", "developers", "managers"]
        )
        message = message_bad_price(workers_str, order, prof_amount, prof, shop, sheet)
        await send_message(chat_id, message, shop, "bad_price", order)

    async def _mes_sender_bs(
        self,
        order: str,
        shop: str,
        sheet: str,
        chat_id: int,
        workers_type: Optional[List[str]] = None,
    ) -> None:
        """
        Send a message about forbidden goods / supplier.
        """
        workers_list: Union[List[str], str] = workers_type or "all"
        workers_str = await self._collect_workers(workers_list)
        message = message_bad_supplier(workers_str, shop, order, sheet)
        await send_message(chat_id, message, shop, "bad_supplier", order)

    async def _mes_sender_at(
        self,
        date: str,
        status: str,
        order: str,
        shop: str,
        sheet: str,
        worker_type: str,
        chat_id: int,
        status_point: str,
    ) -> None:
        """
        Send an attention message for a given status.
        """
        workers = ", ".join(self.staff.get(worker_type, []))
        message = message_attention(
            workers, date, status, order, shop, sheet, worker_type
        )
        await send_message(chat_id, message, shop, status_point, order)

    async def _generate_and_send_bad_mess(
        self,
        workers_list: Union[List[str], str],
        chat_id: int,
        shop_name: str,
        mess_func: Callable,
        btn_txt: str,
        mes_type: str,
        sheet: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Generic helper to generate a message with a button and send it.

        :param workers_list: "all" or list of roles
        :param chat_id: Telegram chat id
        :param shop_name: shop name
        :param mess_func: message builder function from utils
        :param btn_txt: button text for inline keyboard
        :param mes_type: message type (DB key)
        :param sheet: sheet name, if needed
        :param kwargs: extra keyword arguments passed to mess_func
        """
        workers_str = await self._collect_workers(workers_list)
        if sheet is not None:
            message = mess_func(workers_str, shop_name, sheet, **kwargs)
        else:
            message = mess_func(workers_str, shop_name, **kwargs)

        # order_id=None → DB record will be keyed only by mes_type
        await send_message_w_button(
            chat_id=chat_id,
            message=message,
            btn_txt=btn_txt,
            shop_name=shop_name,
            mes_type=mes_type,
            order=None,
        )

    @staticmethod
    async def _mes_deleter(
        shop: str,
        order: str,
        chat_id: int,
        mes_type: str,
    ) -> None:
        """
        Find a message by (shop, message_type, order_id) and:

          - delete/update it in Telegram,
          - remove the DB record.

        Used when an underlying problem has been resolved.
        """
        async with DataBase() as db:
            row = await db.get_message(
                shop_name=shop, message_type=mes_type, order_id=order
            )
            if not row:
                return

            message_id = row["message_id"]
            message_date = row["date"]

        # First, update/delete message in Telegram
        await delete_or_update_message(
            chat_id=chat_id,
            message_id=message_id,
            message_date=message_date,
        )

        # Then clean up DB record
        async with DataBase() as db:
            await db.delete_message(
                shop_name=shop, message_type=mes_type, order_id=order
            )

    # -------------------------------------------------------------------------
    # Sheet / access checks
    # -------------------------------------------------------------------------

    async def now_m_in_sheet(
        self, shop_name: str, chat_id: int, sheets: List[str], now_month: int
    ) -> bool:
        """
        Check whether the sheet for current month exists and table is accessible.

        :return: True if everything is fine or if error is "bad_req",
                 False if an issue was detected and handled.
        """
        err_stat = await google_sheet_err_proc(sheets)

        if err_stat == "forbidden":
            await self._generate_and_send_bad_mess(
                ["analysts", "developers", "managers"],
                chat_id,
                shop_name,
                message_forbidden,
                "Дал доступ",
                "no_access",
            )
            return False

        if err_stat != "bad_req" and str(now_month) not in sheets:
            self.logger.warning(f"sheets: {sheets}")
            self.logger.warning(f"err_stat: {err_stat}")
            self.logger.warning(f"now_month: {now_month}; type: {type(now_month)}")
            self.logger.warning(f"string month in sheets: {str(now_month) in sheets}")
            await self._generate_and_send_bad_mess(
                ["analysts", "developers"],
                chat_id,
                shop_name,
                message_no_sheet,
                "Добавил лист",
                "no_sheet",
            )
            return False

        return True

    # -------------------------------------------------------------------------
    # Data helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def filter_data_by_indices(
        data: List[List[Any]], indices: Dict[str, int]
    ) -> Dict[str, List[Any]]:
        """
        Filter raw Google Sheets data by column indices.

        :param data: list of rows (header + data)
        :param indices: mapping column_name -> index in row
        :return: dict[column_name] = list of values
        """
        res: Dict[str, List[Any]] = {}
        if not data or len(data) < 2:
            return res

        for row in data[1:]:
            for col, i in indices.items():
                value = row[i] if i < len(row) else ""
                res.setdefault(col, []).append(value)
        return res

    # -------------------------------------------------------------------------
    # Problem checks (bad price, fee, checker, etc.)
    # -------------------------------------------------------------------------

    async def bad_price_handler(
        self, data: Dict[str, List[str]], chat_id: int, shop: str, sheet: str
    ) -> None:
        """
        Check for large negative profit (bad_price) and formula issues.
        """
        if not data.get("perc_w_gift"):
            return

        for i, prof_raw in enumerate(data.get("perc_w_gift", [])):
            try:
                prof = float(prof_raw.replace("%", ""))
            except (ValueError, AttributeError):
                # Unable to parse percentage → a formula issue
                await self._generate_and_send_bad_mess(
                    ["developers"],
                    chat_id,
                    shop,
                    message_formula_check,
                    "Исправил",
                    "formula_error",
                    sheet=sheet,
                )
                return

            order = data.get("order_num", [None])[i]
            prof_amount = data.get("profit_amount", [None])[i]
            status_1 = data.get("status1", [""])[i]
            status_2 = data.get("status2", [""])[i]

            if not order or not prof_amount:
                continue

            async with DataBase() as db:
                in_db = await db.check_values_in_columns(
                    shop_name=shop, message_type="bad_price", order_id=order
                )

            # New bad price notification
            if (
                not in_db
                and prof <= -7
                and (status_1 == "" or status_1 == "Треб.закуп преп")
                and status_2 == ""
            ):
                await self._mes_sender_bp(
                    order, prof_amount, prof, shop, sheet, chat_id
                )
                continue

            # Profit is fine now
            if prof > -7 and in_db:
                await self._mes_deleter(shop, order, chat_id, "bad_price")
                continue

            # Status has changed → message is no longer relevant
            if (
                ((status_1 != "" and status_1 != "Треб.закуп преп") or status_2 != "")
                and in_db
            ):
                await self._mes_deleter(shop, order, chat_id, "bad_price")

    async def update_fee_check(
        self, data: Dict[str, List[str]], chat_id: int, shop: str
    ) -> None:
        """
        Check if there are too many rows with missing fee values.
        """
        if not data.get("fee"):
            return

        all_fee = data.get("fee", [])
        all_fee_num = len(all_fee)
        no_fee = sum(1 for fee in all_fee if fee.strip() == "-")

        if no_fee <= 0:
            return

        no_fee_perc = round(no_fee / all_fee_num, 2)
        if no_fee_perc > 0.5 and all_fee_num > 9:
            await self._generate_and_send_bad_mess(
                ["developers"],
                chat_id,
                shop,
                message_need_fee_update,
                "Обновил Fee",
                "need_fee_update",
            )

    async def script_no_check_price(
        self, data: Dict[str, List[str]], chat_id: int, shop: str
    ) -> None:
        """
        Check orders that have supplier but missing buy_price (scraper issue).
        """
        purch_days = data.get("purchase_date")
        buy_price = data.get("buy_price")
        suppliers = data.get("supplier_link")

        if not purch_days or not buy_price or not suppliers:
            return

        b_price_len = len(buy_price)
        no_price = 0
        orders_today = 0

        for day in purch_days:
            if today_or_not(day):
                orders_today += 1

        if orders_today <= 5:
            return

        for i, day in enumerate(purch_days):
            if today_or_not(day):
                price = buy_price[i]
                if price == "" and suppliers[i] != "":
                    no_price += 1

        if no_price <= 0:
            return

        no_price_perc = round(no_price / b_price_len, 2)
        if no_price_perc > 0.3:
            await self._generate_and_send_bad_mess(
                ["developers"],
                chat_id,
                shop,
                message_no_scraping_price,
                "Исправил",
                "no_price_scrapping",
            )

    async def script_no_collect_suppliers(
        self, data: Dict[str, List[str]], chat_id: int, shop: str
    ) -> None:
        """
        Check orders that have purchase date today but missing supplier_link.
        """
        purch_days = data.get("purchase_date")
        suppliers = data.get("supplier_link")

        if not purch_days or not suppliers:
            return

        suppliers_len = len(suppliers)
        no_supp = 0
        orders_today = 0

        for day in purch_days:
            if today_or_not(day):
                orders_today += 1

        if orders_today <= 5:
            return

        for i, day in enumerate(purch_days):
            if today_or_not(day):
                supplier = suppliers[i]
                if supplier == "":
                    no_supp += 1

        if no_supp <= 0:
            return

        no_supp_perc = round(no_supp / suppliers_len, 2)
        if no_supp_perc > 0.4:
            await self._generate_and_send_bad_mess(
                ["developers"],
                chat_id,
                shop,
                message_no_collection_supp,
                "Исправил",
                "no_suppliers_collection",
            )

    async def bad_suppliers_check(
        self, data: Dict[str, List[str]], chat_id: int, shop: str, sheet: str
    ) -> None:
        """
        Check for forbidden suppliers indicated as "ЗАПРЕЩЕНКА!" in comment_field.
        """
        comm_field = data.get("comment_field")
        orders = data.get("order_num")
        statuses_1 = data.get("status1")

        if not comm_field or not orders or not statuses_1:
            return

        for i, comment in enumerate(comm_field):
            order = orders[i]
            status_1 = statuses_1[i]

            async with DataBase() as db:
                in_db = await db.check_values_in_columns(
                    shop_name=shop, message_type="bad_supplier", order_id=order
                )

            # New forbidden supplier message
            if not in_db and "ЗАПРЕЩЕНКА!" in comment and status_1 == "":
                await self._mes_sender_bs(order, shop, sheet, chat_id, ["analysts"])

            # Comment changed or status updated → remove message
            elif in_db and ("ЗАПРЕЩЕНКА!" not in comment or status_1 != ""):
                await self._mes_deleter(shop, order, chat_id, "bad_supplier")

    async def inspect_checker(
        self, data: Dict[str, List[str]], chat_id: int, shop: str
    ) -> None:
        """
        Check "checker" condition: share of "No stock" among today's orders.

        If > 10% with more than 5 orders today, send a notification.
        """
        time_is = datetime.now().time()
        purch_days = data.get("purchase_date")
        buy_price = data.get("buy_price")

        if time_is <= TIME_TRIGGER or not purch_days or not buy_price:
            return

        no_stock = 0
        orders_today = 0

        for day in purch_days:
            if today_or_not(day):
                orders_today += 1

        if orders_today <= 5:
            return

        for i, day in enumerate(purch_days):
            if today_or_not(day):
                price = buy_price[i]
                if "No stock" in str(price):
                    no_stock += 1

        if no_stock <= 0:
            return

        no_stock_perc = round(no_stock / orders_today, 3)
        if no_stock_perc > 0.1:
            await self._generate_and_send_bad_mess(
                ["developers"],
                chat_id,
                shop,
                message_inspect_checker,
                "Включил чекер",
                "inspect_checker",
                orders_today=orders_today,
                no_stock_qty=no_stock,
            )

    async def check_problems(
        self, data: Dict[str, List[str]], chat_id: int, shop: str, sheet: str
    ) -> None:
        """
        Run all problem checks for a given shop/sheet.
        """
        await self.bad_price_handler(data, chat_id, shop, sheet)
        await self.bad_suppliers_check(data, chat_id, shop, sheet)
        await self.script_no_check_price(data, chat_id, shop)
        await self.script_no_collect_suppliers(data, chat_id, shop)
        await self.inspect_checker(data, chat_id, shop)

        # Fee update check is relevant only for current month sheet
        if str(datetime.now().month) == str(sheet):
            await self.update_fee_check(data, chat_id, shop)

    # -------------------------------------------------------------------------
    # Attention statuses
    # -------------------------------------------------------------------------

    async def check_attentions(
        self, data: Dict[str, List[str]], chat_id: int, shop: str, sheet: str
    ) -> None:
        """
        Run all attention-status checks for a given shop/sheet.
        """
        await self.attention_handler(
            "Срочно проблема", data, "analysts", shop, sheet, chat_id
        )
        await self.attention_handler(
            "Срочно треб.закуп", data, "buyers", shop, sheet, chat_id
        )
        await self.attention_handler(
            "Треб.закуп новый поставщик", data, "buyers", shop, sheet, chat_id
        )

    async def attention_handler(
        self,
        status_point: str,
        data: Dict[str, List[str]],
        worker_type: str,
        shop: str,
        sheet: str,
        chat: int,
    ) -> None:
        """
        Handle a single attention status (e.g. 'Срочно проблема').
        """
        if not data.get("status1"):
            return

        for i, status_1 in enumerate(data.get("status1", [])):
            status_2 = data.get("status2", [""])[i]
            order = data.get("order_num", [None])[i]
            date = data.get("purchase_date", [""])[i]

            if not order:
                continue

            async with DataBase() as db:
                in_db = await db.check_values_in_columns(
                    shop_name=shop, message_type=status_point, order_id=order
                )

            # New attention message
            if not in_db and status_1 == status_point and status_2 != "закуплен":
                await self._mes_sender_at(
                    date, status_1, order, shop, sheet, worker_type, chat, status_point
                )

            # Status changed → remove message
            elif in_db and status_1 != status_point:
                await self._mes_deleter(shop, order, chat, status_point)

            # Order purchased → remove message
            elif in_db and status_2 == "закуплен":
                await self._mes_deleter(shop, order, chat, status_point)
