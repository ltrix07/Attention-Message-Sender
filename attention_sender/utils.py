import json


def read_json(file_path: str) -> dict:
    with open(file_path, 'r') as f:
        return json.load(f)


def write_json(file_path: str, data: dict) -> None:
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)


def message_no_sheet(workers, shop):
    return (f'{workers}\n'
            f'В таблице "{shop}" нет листа с текущим месяцем.')


def message_forbidden(workers, shop):
    g_creds = read_json('./creds/google_creds.json')
    serv_email = g_creds.get('client_email')
    return (f'{workers}\n'
            f'У бота нет доступа к таблице "{shop}"\n'
            f'Надо дать доступ для почты:\n\n'
            f'{serv_email}')


def message_bad_price(
        order_id: str, prof_amount: str, prof_perc: float, shop_name: str, sheet_name: str
) -> str:
    return (f'❗️Warning: Слишком большой минус.\n\n'
            f'Amazon order: {order_id}\n'
            f'Profit ($): {prof_amount}$\n'
            f'Profit (%): {prof_perc}%\n'
            f'Shop: "{shop_name}"\n'
            f'Sheet name: "{sheet_name}"')


def message_attention(
        workers: str, buy_date: str, status: str, order: str, shop_name: str, sheet_name: str, worker_type: str
) -> str:
    return (f'{workers}\n'
            f'❗️{status}\n\n'
            f'{order}\n\n'
            f'📅{buy_date}\n'
            f'👨‍💻{worker_type.capitalize()}\n'
            f'🏪{shop_name}\n'
            f'📁{sheet_name}')
