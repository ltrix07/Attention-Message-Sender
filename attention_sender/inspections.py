from attention_sender.utils import read_json, message_bad_price, message_attention
from attention_sender.telegram_bot import db, delete_message, send_message_w_button, send_message


class Inspect:
    def __init__(self, staff_data_ph: str):
        self.staff = read_json(staff_data_ph)

    async def now_m_in_sheet(
            self, shop_name: str, chat_id: int, sheets: list, now_month: int
    ):
        if str(now_month) not in sheets:
            message = (f'{", ".join(self.staff.get("analysts"))}, ' + f'{", ".join(self.staff.get("developers"))}\n'
                       f'В таблице "{shop_name}" нет листа с текущим месяцем.')
            await send_message_w_button(
                chat_id, message, 'Я добавил лист', shop_name, 'no_sheet', None
            )
            return False
        return True

    @staticmethod
    async def filter_data_by_indices(data: list, indices: dict):
        res = {}
        for row in data[1:]:
            for col, i in indices.items():
                if res.get(col):
                    res[col].append(row[i])
                else:
                    res[col] = [row[i]]
        return res

    @staticmethod
    async def check_problems(data: dict, chat_id: int, shop: str, sheet: str):
        for i, prof in enumerate(data.get('perc_w_gift')):
            prof = float(prof.replace('%', ''))
            order = data.get('order_num')[i]
            prof_amount = data.get('profit_amount')[i]

            if prof <= -7:
                message = message_bad_price(order, prof_amount, prof, shop, sheet)
                await send_message(chat_id, message, shop, 'bad_price', order)
            elif prof > -7 and db.check_values_in_columns(shop_name=shop, message_type='bad_price', order=order):
                mess_id = db.get_item('message_id', shop_name=shop, message_type='bad_price', order=order)
                await delete_message(chat_id, mess_id)

    async def check_attentions(self, data: dict, chat_id: int, shop: str, sheet: str):
        await self.attention_handler('Срочно проблема', data, 'analysts', shop, sheet, chat_id)
        await self.attention_handler('Срочно треб.закуп', data, 'buyers', shop, sheet, chat_id)
        await self.attention_handler('Треб.закуп новый поставщик', data, 'buyers', shop, sheet, chat_id)
        await self.attention_handler('Отмена', data, 'trackers', shop, sheet, chat_id)

    async def attention_handler(self, status_point: str, data: dict, worker_type: str, shop: str, sheet: str, chat: int):
        workers = ", ".join(self.staff.get(worker_type))
        for i, status in data.get('status1'):
            order = data.get('order_num')[i]
            date = data.get('purchase_date')[i]

            if status == status_point:
                message = message_attention(
                    workers, date, status, order, shop, sheet, worker_type
                )
                await send_message(chat, message, shop, status_point, order)
            elif db.check_values_in_columns(message_type=status_point, order=order) and status != status_point:
                mess_id = db.get_item('message_id', message_type=status_point, order=order)
                await delete_message(chat, mess_id)

