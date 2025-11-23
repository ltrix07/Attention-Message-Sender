"""
Command-line tool for managing shops configuration (spreadsheets.json).

Usage examples:

  # List all shops
  python -m attention_sender.shop_cli list

  # Add a new shop (interactive)
  python -m attention_sender.shop_cli add

  # Remove a shop
  python -m attention_sender.shop_cli remove my_shop

  # Show details of a single shop
  python -m attention_sender.shop_cli show my_shop
"""

import argparse
from typing import Dict, Any

from attention_sender.utils import read_json, write_json
from attention_sender.config import settings


SPREADSHEETS_PATH = settings.paths.spreadsheets.as_posix()
GOOGLE_CREDS_PATH = settings.paths.google_creds.as_posix()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_shops() -> Dict[str, Any]:
    """
    Load shops configuration from spreadsheets.json.

    :return: mapping shop_name -> shop_config
    """
    try:
        return read_json(SPREADSHEETS_PATH)
    except FileNotFoundError:
        return {}


def save_shops(data: Dict[str, Any]) -> None:
    """
    Save shops configuration back to spreadsheets.json.
    """
    write_json(SPREADSHEETS_PATH, data)


def print_shop(name: str, cfg: Dict[str, Any]) -> None:
    """
    Pretty-print single shop configuration.
    """
    print(f"\nShop: {name}")
    print(f"  table_id: {cfg.get('table_id', '')}")
    columns = cfg.get("columns", {})
    if columns:
        print("  columns:")
        for k, v in columns.items():
            print(f"    {k}: {v}")
    print()


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def action_list(_: argparse.Namespace) -> None:
    """
    List all configured shops.
    """
    shops = load_shops()
    if not shops:
        print("No shops configured yet.")
        return

    print("Configured shops:")
    for name in shops.keys():
        print(f"  - {name}")


def action_show(args: argparse.Namespace) -> None:
    """
    Show full configuration of a specific shop.
    """
    shops = load_shops()
    name = args.name.lower().strip()

    cfg = shops.get(name)
    if not cfg:
        print(f"Shop '{name}' not found.")
        return

    print_shop(name, cfg)


def action_remove(args: argparse.Namespace) -> None:
    """
    Remove a shop from configuration.
    """
    shops = load_shops()
    name = args.name.lower().strip()

    if name not in shops:
        print(f"Shop '{name}' not found.")
        return

    confirm = input(f"Are you sure you want to delete shop '{name}'? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return

    del shops[name]
    save_shops(shops)
    print(f"Shop '{name}' removed.")


def action_add(_: argparse.Namespace) -> None:
    """
    Interactively add a new shop to configuration.
    """
    shops = load_shops()
    g_creds = read_json(GOOGLE_CREDS_PATH)

    shop_name = input("Enter shop name: ").lower().strip()
    if not shop_name:
        print("Shop name cannot be empty.")
        return

    if shop_name in shops:
        print("Shop already exists in configuration.")
        return

    print("\nYou need to grant access to this service account email:")
    print(g_creds.get("client_email", "SERVICE_ACCOUNT_EMAIL_NOT_FOUND"))
    print()

    table_id = input("Enter Google Sheets table ID: ").strip()
    if not table_id:
        print("Table ID cannot be empty.")
        return

    print(
        "\nNow enter exact column headers from the sheet for each logical field.\n"
        "If some column is not used in your setup, you can leave it empty.\n"
    )

    columns = {
        "status1": input('Header for column "status 1": ').strip(),
        "status2": input('Header for column "status 2": ').strip(),
        "order_num": input('Header for column "order number": ').strip(),
        "purchase_date": input('Header for column "purchase date": ').strip(),
        "profit_amount": input('Header for column "profit amount": ').strip(),
        "perc_w_gift": input('Header for column "profit % (with gift)": ').strip(),
        "fee": input('Header for column "fee": ').strip(),
        "supplier_link": input('Header for column "supplier link": ').strip(),
        "comment_field": input('Header for column "comment": ').strip(),
        "buy_price": input('Header for column "buy price": ').strip(),
    }

    # Clean up empty values (user may leave some headers blank)
    columns = {k: v for k, v in columns.items() if v}

    if not columns:
        print("No columns provided, cannot create shop config.")
        return

    shops[shop_name] = {
        "table_id": table_id,
        "columns": columns,
    }

    save_shops(shops)
    print("\nShop has been added successfully:")
    print_shop(shop_name, shops[shop_name])


# ---------------------------------------------------------------------------
# CLI bootstrap
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CLI tool for managing shops in spreadsheets.json"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = subparsers.add_parser("list", help="List all shops")
    p_list.set_defaults(func=action_list)

    # show
    p_show = subparsers.add_parser("show", help="Show details of a single shop")
    p_show.add_argument("name", help="Shop name")
    p_show.set_defaults(func=action_show)

    # add
    p_add = subparsers.add_parser("add", help="Add a new shop (interactive)")
    p_add.set_defaults(func=action_add)

    # remove
    p_rm = subparsers.add_parser("remove", help="Remove a shop")
    p_rm.add_argument("name", help="Shop name")
    p_rm.set_defaults(func=action_remove)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
