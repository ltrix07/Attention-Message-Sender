# Attention Message Sender

Python service that monitors orders in Google Sheets and sends automated alerts to Telegram when something goes wrong (bad prices, forbidden items, missing sheets, “No stock” spikes, etc.).

It is built for e‑commerce teams that manage orders in Google Sheets and use Telegram for daily communication.

---

## Features

- 🔗 **Google Sheets + Telegram integration**
  - Reads order data from one or more Google Sheets.
  - Sends alerts to dedicated Telegram chats.

- 🧠 **Business rules / inspections**
  - **Bad price** – too large negative profit.
  - **Forbidden item / supplier** marked as `ЗАПРЕЩЕНКА!`.
  - **Missing current month sheet**.
  - **No access** to Google Sheet (forbidden).
  - **Too many empty fee values**.
  - **Scraper not pulling prices** (`buy_price` is empty but supplier exists).
  - **Suppliers not collected** (empty `supplier_link`).
  - **Checker issues** – too many `No stock` for today’s orders.
  - **Attention statuses** from sheet:
    - `Срочно проблема`
    - `Срочно треб.закуп`
    - `Треб.закуп новый поставщик`

- 💬 **Smart Telegram messages**
  - Mentions responsible staff (analysts, buyers, developers, managers).
  - Each message is stored in SQLite so it is not duplicated.
  - When a problem is fixed, the message is deleted or updated in chat and removed from DB.

- 🛠️ **Admin CLI for shops**
  - Manage shops and their sheet configuration via `shop_cli`:
    - add / show / list / remove shops.

- ⚙️ **Modular, async architecture**
  - Clear separation: Google client, inspections, Telegram bot, DB layer, CLI, config.
  - Asynchronous processing loop, non‑blocking Telegram bot.

---

## Project structure

```text
.
├─ main.py                     # Entry point: runs bot + processing loop
├─ attention_sender/
│  ├─ __init__.py              # Exports core constants
│  ├─ config.py                # Centralized paths & settings
│  ├─ constants.py             # Time thresholds, business thresholds, status strings
│  ├─ collector.py             # Helper for current/previous month
│  ├─ db.py                    # Async wrapper around SQLite (sent_messages)
│  ├─ errors.py                # Google Sheets error classification
│  ├─ google_client.py         # Google Sheets client (gspread)
│  ├─ inspections.py           # Main rules engine (all checks)
│  ├─ telegram_bot.py          # Telegram bot, messaging helpers, callbacks
│  ├─ utils.py                 # JSON helpers, date helper, message builders
│  └─ shop_cli.py              # CLI for managing shops (spreadsheets.json)
├─ creds/
│  ├─ telegram.json            # Telegram bot token
│  └─ google_creds.json        # Google service account credentials
├─ db/
│  ├─ staff.json               # Staff roles and usernames
│  ├─ spreadsheets.json        # Shops configuration (sheets + columns mapping)
│  └─ chat_data.json           # Telegram chat IDs for problems/attentions
└─ cech/
   └─ messages.db              # SQLite database with sent messages
```

---

## Requirements

- Python **3.10+**
- Google service account with access to the required spreadsheets
- Telegram bot token (from [BotFather](https://t.me/BotFather))

Python dependencies (typical `requirements.txt`):

```txt
aiogram
aiosqlite
gspread
google-auth
google-auth-oauthlib
google-auth-httplib2
```

---

## Installation

Clone the repository and create a virtual environment:

```bash
git clone https://github.com/<your-username>/Attention-Message-Sender.git
cd Attention-Message-Sender

python -m venv .venv
source .venv/bin/activate   # on Linux / macOS
# .venv\Scripts\activate  # on Windows
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Configuration

All important paths are defined in `attention_sender/config.py` via the `Settings` / `Paths` dataclasses.  
By default the project expects the following files and folders.

### 1. `creds/telegram.json`

```json
{
  "token": "YOUR_TELEGRAM_BOT_TOKEN"
}
```

You can obtain a token from [BotFather](https://t.me/BotFather).

---

### 2. `creds/google_creds.json`

Standard Google service account JSON, e.g. downloaded from Google Cloud Console:

```json
{
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "your-service-account@project.iam.gserviceaccount.com",
  "client_id": "...",
  "token_uri": "https://oauth2.googleapis.com/token",
  "...": "..."
}
```

The `client_email` from this file must have at least **read access** to each Google Sheet you monitor.

---

### 3. `db/staff.json`

Staff usernames grouped by roles. These roles are used when building messages and mentions:

```json
{
  "analysts":   ["@analyst1", "@analyst2"],
  "buyers":     ["@buyer1"],
  "developers": ["@dev1"],
  "managers":   ["@manager1"]
}
```

You can freely change the usernames; role names are referenced from `inspections.py`.

---

### 4. `db/chat_data.json`

Telegram chat IDs where notifications will be sent:

```json
{
  "chat_w_problems": -1001234567890,
  "chat_w_attentions": -1009876543210
}
```

- `chat_w_problems` – bad prices, forbidden, technical issues, checker problems, etc.
- `chat_w_attentions` – attention statuses from Google Sheets (`Срочно проблема`, etc.).

You can use the same chat ID for both if you wish.

---

### 5. `db/spreadsheets.json`

Shops and their Google Sheet configuration.

Example with a single shop:

```json
{
  "shop1": {
    "table_id": "1AbCdEfGhIjKlMnOpQrStUvWxYz1234567890",   // Google Sheets document ID
    "columns": {
      "status1": "Status 1",
      "status2": "Status 2",
      "order_num": "Order ID",
      "purchase_date": "Purchase date",
      "profit_amount": "Profit amount",
      "perc_w_gift": "Profit % (with gift)",
      "fee": "Fee",
      "supplier_link": "Supplier link",
      "comment_field": "Comment",
      "buy_price": "Buy price"
    }
  }
}
```

Keys under `columns` are logical names used in the code; values are **exact header texts** from the first row of your Google Sheet.

You can manage this file more easily via the CLI (`shop_cli.py`), see below.

---

## Using the shop CLI

To manage shops configuration from the command line:

```bash
python -m attention_sender.shop_cli list
python -m attention_sender.shop_cli add
python -m attention_sender.shop_cli show shop1
python -m attention_sender.shop_cli remove shop1
```

- `list` – shows all configured shops.
- `add` – interactive wizard that asks for Google Sheet ID and column headers.
- `show` – prints full configuration for a given shop.
- `remove` – deletes a shop from `spreadsheets.json`.

---

## How it works

1. **Telegram bot**  
   `attention_sender/telegram_bot.py` creates a bot using `aiogram` and exposes:
   - polling dispatcher (`dp`);
   - helper functions for sending messages with/without buttons;
   - callback handler for “resolved” buttons;
   - logic for deleting or updating old messages.

2. **Google Sheets client**  
   `attention_sender/google_client.py` uses `gspread` to:
   - list sheet titles for a given spreadsheet (`get_sheets_name`);
   - read all values from a worksheet (`get_all_info_from_sheet`);
   - map logical column keys to indices based on header row (`get_columns_indices`).

3. **Inspections / rules**  
   `attention_sender/inspections.py` is the central rules engine.  
   It receives filtered table data and runs a series of checks, e.g.:

   - **Bad price (`bad_price`)**
     - Profit percentage ≤ configured threshold (default `-7%`);
     - Status 1 is empty or `"Треб.закуп преп"`;
     - Status 2 is empty.
     - Sends a message and remembers it in DB.  
       If later profit is fixed or status changes, the message is removed.

   - **Forbidden supplier / item (`bad_supplier`)**
     - `comment_field` contains `ЗАПРЕЩЕНКА!`.
     - Status 1 is empty.
     - When marker disappears or status changes, message is removed.

   - **Missing sheet / access**
     - If there is no sheet for current month → send `no_sheet`.
     - If Google API response indicates forbidden access → send `no_access`.

   - **Fee, scraper, suppliers, checker**
     - Too many rows with `fee = "-"`.
     - Too many orders today with empty `buy_price` but non‑empty supplier.
     - Too many orders today with empty `supplier_link`.
     - Too many `No stock` among today’s orders (checker problem).

   - **Attention statuses**
     - Look at `status1` and `status2` columns:
       - `Срочно проблема` → ping `analysts`.
       - `Срочно треб.закуп` → ping `buyers`.
       - `Треб.закуп новый поставщик` → ping `buyers`.  
     - If the status changes or the order becomes `"закуплен"`, the old message is removed.

4. **Database layer**  
   `attention_sender/db.py` wraps `aiosqlite` and stores messages in a `sent_messages` table:
   - `message_id`, `chat_id`, `shop_name`, `message_type`, `order_id`, `text`, `date`.
   - Used to avoid duplicates and to delete/update messages when needed.

5. **Main loop**  
   `main.py` runs:
   - Telegram bot polling;
   - Async processing loop that:
     - iterates over all shops in `db/spreadsheets.json`;
     - for each shop, detects current/previous month sheets;
     - loads and filters table data via `GoogleSheetsClient`;
     - runs all inspections.

---

## Running the service

After you have:

- created virtual environment,
- installed dependencies,
- filled `creds/`, `db/` JSON files,

you can start the service with:

```bash
python main.py
```

What happens:

- The Telegram bot starts polling.
- The processing loop runs continuous cycles over all configured shops.
- When rules are triggered, messages appear in your Telegram chats.

You can stop the service with `Ctrl + C`.

---

## Development notes

- The project uses an **async** architecture:
  - `aiogram` for Telegram bot;
  - `aiosqlite` for DB access;
  - `asyncio` for running bot and processing loop in parallel.
- Business rules, thresholds and status strings are defined in
  `attention_sender/constants.py` and can be adjusted for your team.
- All comments and docstrings inside the code are in English,
  while user‑visible messages remain in Russian (to match existing workflows).

---

## TODO / ideas

- Docker image for easy deployment.
- Simple web dashboard for monitoring last alerts.
- More granular configuration per shop (different thresholds, chat IDs, etc.).
- Tests for core inspection logic.