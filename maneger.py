from attention_sender.utils import read_json, write_json


def add_shop():
    g_creds = read_json('./creds/google_creds.json')
    all_data = read_json('./db/spreadsheets.json')
    shop_name = input('Enter shop name: ').lower().strip()
    for shop in all_data.keys():
        if shop_name == shop:
            return 'Shop already in database'

    print(f'Give allow for this email - {g_creds.get("client_email")}')
    shop_data = {
        "table_id": input('Enter table id: '),
        "columns": {
            "status1": input('Enter column name for "status 1": '),
            "purchase_date": input('Enter column name for "purchase date": '),
            "profit_amount": input('Enter columns name for "profit amount": '),
            "perc_profit": input('Enter columns name for "percent profit": '),
            "perc_w_gift": input('Enter columns name for "percent profit with gift": '),
            "order_num": input('Enter columns name for "order number": '),
            "buy_price": input('Enter columns name for "buy price": ')
        }
    }

    all_data[shop_name] = shop_data
    write_json('./db/spreadsheets.json', all_data)
    return 'Shop added successful!'


def delete_shop():
    shop_name = input('Enter shop name: ').lower().strip()
    all_data = read_json('./db/spreadsheets.json')
    for shop in all_data.keys():
        if shop_name == shop:
            del all_data[shop]
            write_json('./db/spreadsheets.json', all_data)
            return 'Shop delete successful!'
    return f'No shop with name "{shop_name}"'


def maneger():
    print(
        'Actions:\n'
        '1. Add shop\n'
        '2. Delete shop\n'
    )
    choice = input('Choose action: ').strip()
    if choice == '1':
        inf = add_shop()
        print(inf)
    elif choice == '2':
        inf = delete_shop()
        print(inf)


if __name__ == '__main__':
    maneger()
