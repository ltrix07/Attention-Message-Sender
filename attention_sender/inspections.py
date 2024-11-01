from attention_sender.utils import read_json, message_bad_price, message_attention, message_no_sheet, \
    message_forbidden, message_formula_check, message_need_fee_update, today_or_not, message_no_scraping_price, \
    message_no_collection_supp, message_bad_supplier, message_inspect_checker
from attention_sender import TIME_TRIGGER
from attention_sender.telegram_bot import delete_or_update_message, send_message_w_button, send_message
from attention_sender.db import DataBase
from attention_sender.errors import google_sheet_err_proc
from typing import Callable
from datetime import datetime


class Inspect:
    def __init__(self, staff_data_ph: str):
        self.staff = read_json(staff_data_ph)

    async def _collect_workers(self, workers_type: list | str = 'all') -> str:
        workers_str = ""
        if workers_type == 'all':
            for workers in self.staff.keys():
                workers_str += ", ".join(self.staff[workers])
        else:
            for index, worker in enumerate(workers_type):
                if index == len(workers_type) - 1:
                    workers_str += ", ".join(self.staff.get(worker, []))
                else:
                    workers_str += ", ".join(self.staff.get(worker, [])) + ", "
        return workers_str

    async def _mes_sender_bp(
            self, order: str, prof_amount: str, prof: float, shop: str, sheet: str, chat_id: int
    ) -> None:
        workers = ", ".join(self.staff.get('analysts')) + ', ' + ", ".join(self.staff.get('developers')) \
            + ', ' + ", ".join(self.staff.get('managers'))
        message = message_bad_price(workers, order, prof_amount, prof, shop, sheet)
        await send_message(chat_id, message, shop, 'bad_price', order)

    async def _mes_sender_bs(
            self, order: str, shop: str, sheet: str, chat_id: int, workers_type: list | str = 'all'
    ):
        workers_str = await self._collect_workers(workers_type)
        message = message_bad_supplier(workers_str, shop, order, sheet)
        await send_message(chat_id, message, shop, 'bad_supplier', order)

    async def _mes_sender_at(
            self, date: str, status: str, order: str, shop: str, sheet: str,
            worker_type: str, chat: int, status_point: str
    ) -> None:
        workers = ", ".join(self.staff.get(worker_type))
        message = message_attention(
            workers, date, status, order, shop, sheet, worker_type
        )
        await send_message(chat, message, shop, status_point, order)

    async def _generate_and_send_bad_mess(
            self, workers_list: list | str, chat_id: int, shop_name: str, mess_func: Callable,
            btn_txt: str, mes_type: str, sheet: str | None = None, **kwargs
    ):
        workers_str = await self._collect_workers(workers_list)
        if sheet:
            message = mess_func(workers_str, shop_name, sheet, **kwargs)
        else:
            message = mess_func(workers_str, shop_name, **kwargs)
        await send_message_w_button(
            chat_id, message, btn_txt, shop_name, mes_type, None
        )

    @staticmethod
    async def _mes_deleter(shop: str, order: str, chat_id: int, mes_type: str) -> None:
        async with DataBase() as db:
            mess_id, mess_date = await db.get_item(["message_id", "date"], shop_name=shop,
                                                   message_type=mes_type, order_id=order)
            await delete_or_update_message(chat_id, mess_id, mess_date)

    async def now_m_in_sheet(
            self, shop_name: str, chat_id: int, sheets: list, now_month: int
    ):
        err_stat = await google_sheet_err_proc(sheets)
        if err_stat == 'forbidden':
            await self._generate_and_send_bad_mess(
                ['analysts', 'developers', 'managers'],  chat_id, shop_name, message_forbidden,
                'Дал доступ', 'no_access'
            )
            return False
        elif err_stat != 'bad_req' and str(now_month) not in sheets:
            await self._generate_and_send_bad_mess(
                ['analysts', 'developers'], chat_id, shop_name, message_no_sheet, 'Добавил лист',
                'no_sheet'
            )
            return False
        return True

    @staticmethod
    async def filter_data_by_indices(data: list, indices: dict) -> dict:
        res = {}
        for row in data[1:]:
            for col, i in indices.items():
                if res.get(col):
                    res[col].append(row[i])
                else:
                    res[col] = [row[i]]
        return res

    async def bad_price_handler(self, data: dict, chat_id: int, shop: str, sheet: str):
        for i, prof in enumerate(data.get('perc_w_gift')):
            try:
                prof = float(prof.replace('%', ''))
            except ValueError:
                await self._generate_and_send_bad_mess(
                    ['developers'], chat_id, shop, message_formula_check, 'Исправил',
                    'formula_error', sheet
                )
                return

            order = data.get('order_num')[i]
            prof_amount = data.get('profit_amount')[i]
            status_1 = data.get('status1')[i]
            status_2 = data.get('status2')[i]
            async with DataBase() as db:
                in_db = await db.check_values_in_columns(shop_name=shop, message_type='bad_price', order_id=order)

            if not in_db and prof <= -7 and (status_1 == '' or status_1 == 'Треб.закуп преп') and status_2 == '':
                return await self._mes_sender_bp(order, prof_amount, prof, shop, sheet, chat_id)
            elif prof > -7 and in_db:
                return await self._mes_deleter(shop, order, chat_id, 'bad_price')
            elif (status_1 != '' or status_1 == 'Треб.закуп преп' or status_2 != '') and in_db:
                return await self._mes_deleter(shop, order, chat_id, 'bad_price')
            return

    async def update_fee_check(self, data: dict, chat_id: int, shop: str):
        all_fee = data.get('fee')
        all_fee_num = len(all_fee)
        no_fee = 0
        for fee in all_fee:
            if fee.strip() == '-':
                no_fee += 1
        if no_fee > 0:
            no_fee_perc = round(no_fee / all_fee_num, 2)
            if no_fee_perc > 0.5 and all_fee_num > 9:
                await self._generate_and_send_bad_mess(
                    ['developers'], chat_id, shop, message_need_fee_update, 'Обновил Fee',
                    'need_fee_update'
                )

    async def script_no_check_price(self, data: dict, chat_id: int, shop: str):
        purch_days = data.get('purchase_date')
        buy_price = data.get('buy_price')
        suppliers = data.get('supplier_link')
        b_price_len = len(buy_price)
        no_price = 0
        orders_today = 0
        for i, day in enumerate(purch_days):
            is_today = today_or_not(day)
            if is_today:
                orders_today += 1

        if orders_today > 5:
            for i, day in enumerate(purch_days):
                is_today = today_or_not(day)
                if is_today:
                    price = buy_price[i]
                    if price == '' and suppliers[i] != '':
                        no_price += 1
        if no_price > 0:
            no_price_perc = round(no_price / b_price_len, 2)
            if no_price_perc > 0.3:
                await self._generate_and_send_bad_mess(
                    ['developers'], chat_id, shop, message_no_scraping_price, 'Исправил',
                    'no_price_scrapping'
                )

    async def script_no_collect_suppliers(self, data: dict, chat_id: int, shop: str):
        purch_days = data.get('purchase_date')
        suppliers = data.get('supplier_link')
        suppliers_len = len(suppliers)
        no_supp = 0
        orders_today = 0
        for i, day in enumerate(purch_days):
            is_today = today_or_not(day)
            if is_today:
                orders_today += 1

        if orders_today > 5:
            for i, day in enumerate(purch_days):
                is_today = today_or_not(day)
                if is_today:
                    supplier = suppliers[i]
                    if supplier == '':
                        no_supp += 1
        if no_supp > 0:
            no_supp_perc = round(no_supp / suppliers_len, 2)
            if no_supp_perc > 0.4:
                await self._generate_and_send_bad_mess(
                    ['developers'], chat_id, shop, message_no_collection_supp, 'Исправил',
                    'no_suppliers_collection'
                )

    async def bad_suppliers_check(self, data: dict, chat_id: int, shop: str, sheet: str):
        comm_field = data.get('comment_field')
        orders = data.get('order_num')
        statuses_1 = data.get('status1')
        for i, comment in enumerate(comm_field):
            order = orders[i]
            status_1 = statuses_1[i]
            async with DataBase() as db:
                in_db = await db.check_values_in_columns(shop_name=shop, message_type='bad_supplier', order_id=order)

            if not in_db and 'ЗАПРЕЩЕНКА!' in comment and status_1 == '':
                await self._mes_sender_bs(order, shop, sheet, chat_id, ['analysts'])
            elif in_db and ('ЗАПРЕЩЕНКА!' not in comment or status_1 != ''):
                await self._mes_deleter(shop, order, chat_id, 'bad_supplier')

    async def inspect_checker(self, data: dict, chat_id: int, shop: str):
        time_is = datetime.now().time()
        if time_is <= TIME_TRIGGER:
            return
        purch_days = data.get('purchase_date')
        buy_price = data.get('buy_price')
        no_stock = 0
        orders_today = 0
        for i, day in enumerate(purch_days):
            is_today = today_or_not(day)
            if is_today:
                orders_today += 1

        if orders_today > 5:
            for i, day in enumerate(purch_days):
                is_today = today_or_not(day)
                if is_today:
                    price = buy_price[i]
                    if 'No stock' in price:
                        no_stock += 1
        if no_stock > 0:
            no_stock_perc = round(no_stock / orders_today, 3)
            if no_stock_perc > 0.1:
                await self._generate_and_send_bad_mess(
                    ['developers'], chat_id, shop, message_inspect_checker, 'Включил чекер',
                    'inspect_checker', orders_today=orders_today, no_stock_qty=no_stock
                )

    async def check_problems(self, data: dict, chat_id: int, shop: str, sheet: str) -> None:
        await self.bad_price_handler(data, chat_id, shop, sheet)
        await self.bad_suppliers_check(data, chat_id, shop, sheet)
        await self.script_no_check_price(data, chat_id, shop)
        await self.script_no_collect_suppliers(data, chat_id, shop)
        await self.inspect_checker(data, chat_id, shop)
        if str(datetime.now().month) == str(sheet):
            await self.update_fee_check(data, chat_id, shop)

    async def check_attentions(self, data: dict, chat_id: int, shop: str, sheet: str) -> None:
        await self.attention_handler('Срочно проблема', data, 'analysts', shop, sheet, chat_id)
        await self.attention_handler('Срочно треб.закуп', data, 'buyers', shop, sheet, chat_id)
        await self.attention_handler('Треб.закуп новый поставщик', data, 'buyers', shop, sheet, chat_id)

    async def attention_handler(
            self, status_point: str, data: dict, worker_type: str, shop: str, sheet: str, chat: int
    ) -> None:
        for i, status_1 in enumerate(data.get('status1')):
            status_2 = data.get('status2')[i]
            order = data.get('order_num')[i]
            date = data.get('purchase_date')[i]
            async with DataBase() as db:
                in_db = await db.check_values_in_columns(shop_name=shop, message_type=status_point, order_id=order)

            if not in_db and status_1 == status_point and status_2 != 'закуплен':
                await self._mes_sender_at(date, status_1, order, shop, sheet, worker_type, chat, status_point)
            elif in_db and status_1 != status_point:
                await self._mes_deleter(shop, order, chat, status_point)
            elif in_db and status_2 == 'закуплен':
                await self._mes_deleter(shop, order, chat, status_point)
