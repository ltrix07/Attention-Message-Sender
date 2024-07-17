from attention_sender.utils import read_json, message_bad_price, message_attention, message_no_sheet, \
    message_forbidden
from attention_sender.telegram_bot import db, delete_message, send_message_w_button, send_message
from attention_sender.errors import google_sheet_err_proc


class Inspect:
    def __init__(self, staff_data_ph: str):
        self.staff = read_json(staff_data_ph)

    @staticmethod
    async def _mes_sender_bp(
            order: str, prof_amount: str, prof: float, shop: str, sheet: str, chat_id: int
    ) -> None:
        message = message_bad_price(order, prof_amount, prof, shop, sheet)
        await send_message(chat_id, message, shop, 'bad_price', order)

    async def _mes_sender_at(
            self, date: str, status: str, order: str, shop: str, sheet: str,
            worker_type: str, chat: int, status_point: str
    ) -> None:
        workers = ", ".join(self.staff.get(worker_type))
        message = message_attention(
            workers, date, status, order, shop, sheet, worker_type
        )
        await send_message(chat, message, shop, status_point, order)

    @staticmethod
    async def _mes_deleter(shop: str, order: str, chat_id: int) -> None:
        mess_id = db.get_item('message_id', shop_name=shop, message_type='bad_price', order_id=order)
        await delete_message(chat_id, mess_id)

    async def now_m_in_sheet(
            self, shop_name: str, chat_id: int, sheets: list, now_month: int
    ):
        err_stat = await google_sheet_err_proc(sheets)
        print(err_stat)
        if not err_stat:
            await self.no_access_to_table(chat_id, shop_name)
            return False
        elif str(now_month) not in sheets:
            await self.no_sheet_in_table(chat_id, shop_name)
            return False
        return True

    async def no_access_to_table(self, chat_id: int, shop_name: str) -> None:
        workers = f'{", ".join(self.staff.get('analysts'))}, {", ".join(self.staff.get('developers'))}, {", ".join(self.staff.get('managers'))}'
        message = message_forbidden(workers, shop_name)
        await send_message_w_button(
            chat_id, message, 'Дал доступ', shop_name, 'no_access', None
        )

    async def no_sheet_in_table(self, chat_id: int, shop_name: str):
        workers = f'{", ".join(self.staff.get('analysts'))}, {", ".join(self.staff.get('developers'))}'
        message = message_no_sheet(workers, shop_name)
        await send_message_w_button(
            chat_id, message, 'Добавил лист', shop_name, 'no_sheet', None
        )

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

    async def check_problems(self, data: dict, chat_id: int, shop: str, sheet: str) -> None:
        for i, prof in enumerate(data.get('perc_w_gift')):
            prof = float(prof.replace('%', ''))
            order = data.get('order_num')[i]
            prof_amount = data.get('profit_amount')[i]
            status_1 = data.get('status1')[i]
            status_2 = data.get('status2')[i]
            in_db = db.check_values_in_columns(shop_name=shop, message_type='bad_price', order_id=order)

            if prof <= -7 and not in_db:
                await self._mes_sender_bp(order, prof_amount, prof, shop, sheet, chat_id)
            elif prof > -7 and in_db:
                await self._mes_deleter(shop, order, chat_id)
            elif status_1 == 'Жду трек':
                await self._mes_deleter(shop, order, chat_id)
            elif status_2 == 'закуплен' and in_db:
                await self._mes_deleter(shop, order, chat_id)

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
            in_db = db.check_values_in_columns(shop_name=shop, message_type=status_point, order_id=order)

            if status_1 == status_point and not in_db:
                await self._mes_sender_at(date, status_1, order, shop, sheet, worker_type, chat, status_point)
            elif in_db and status_1 != status_point:
                await self._mes_deleter(shop, order, chat)
            elif in_db and status_2 == 'закуплен':
                await self._mes_deleter(shop, order, chat)
