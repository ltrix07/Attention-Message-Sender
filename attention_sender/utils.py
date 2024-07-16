import json


def read_json(file_path) -> dict:
    with open(file_path, 'r') as f:
        return json.load(f)


def write_json(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)


def message_bad_price(order_id, prof_amount, prof_perc, shop_name, sheet_name):
    return (f'❗️Warning: Слишком большой минус.\n\n'
            f'Amazon order: {order_id}\n'
            f'Profit ($): {prof_amount}$\n'
            f'Profit (%): {prof_perc}%\n'
            f'Shop: "{shop_name}"\n'
            f'Sheet name: "{sheet_name}"')


def message_attention(workers: str, buy_date: str, status: str, order: str, shop_name: str, sheet_name: str, worker_type: str):
    return (f'{workers}\n'
            f'❗️{status}\n\n'
            f'{order}\n\n'
            f'📅{buy_date}\n'
            f'👨‍💻{worker_type.capitalize()}\n'
            f'🏪{shop_name}\n'
            f'📁{sheet_name}')
