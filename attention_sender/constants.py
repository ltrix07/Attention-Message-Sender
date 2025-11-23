from datetime import time, timedelta
from typing import Final


# ---------------------------------------------------------------------------
# Time-related settings
# ---------------------------------------------------------------------------

#: Time of day after which checker logic becomes active.
#: Used in Inspect.inspect_checker().
TIME_TRIGGER: Final[time] = time(hour=12, minute=0)

#: How long a Telegram message is considered "fresh" and can be fully deleted.
#: After this, the bot will try to edit text instead of deleting.
MESSAGE_LIFETIME: Final[timedelta] = timedelta(days=2)


# ---------------------------------------------------------------------------
# Business thresholds (tunable rules)
# ---------------------------------------------------------------------------

#: Profit percentage threshold for "bad price" (too big negative profit).
BAD_PRICE_THRESHOLD: Final[float] = -7.0

#: Minimum number of rows in a sheet to run fee-missing checks.
MIN_ROWS_FOR_FEE_CHECK: Final[int] = 10

#: Share of rows with missing fee (e.g. "-") above which a warning is sent.
MISSING_FEE_SHARE_THRESHOLD: Final[float] = 0.5

#: Minimum number of today's orders required to run daily checks
#: (checker, missing prices, missing suppliers).
MIN_ORDERS_FOR_DAILY_CHECKS: Final[int] = 5

#: Threshold of today's orders with missing buy_price (but with supplier)
#: above which scraper-problem warning is sent.
NO_PRICE_SCRAPING_SHARE_THRESHOLD: Final[float] = 0.3

#: Threshold of today's orders with missing supplier_link
#: above which supplier-collecting warning is sent.
NO_SUPPLIERS_SHARE_THRESHOLD: Final[float] = 0.4

#: "No stock" share threshold for checker.
#: If more than this fraction of today's orders have "No stock" in buy_price,
#: a checker warning is sent.
NO_STOCK_SHARE_THRESHOLD: Final[float] = 0.1


# ---------------------------------------------------------------------------
# Status strings used in Google Sheets
# ---------------------------------------------------------------------------

#: Attention status: urgent problem.
STATUS_SR_PROBLEM: Final[str] = "Срочно проблема"

#: Attention status: urgent purchase required.
STATUS_SR_PURCHASE: Final[str] = "Срочно треб.закуп"

#: Attention status: need new supplier for purchase.
STATUS_NEW_SUPPLIER: Final[str] = "Треб.закуп новый поставщик"

#: Status meaning that the order has been purchased.
STATUS_PURCHASED: Final[str] = "закуплен"


# ---------------------------------------------------------------------------
# Markers / special keywords
# ---------------------------------------------------------------------------

#: Marker used in comment_field column to indicate forbidden supplier / item.
FORBIDDEN_MARKER: Final[str] = "ЗАПРЕЩЕНКА!"


# ---------------------------------------------------------------------------
# Message types stored in the DB
# ---------------------------------------------------------------------------

#: Type for large negative profit messages.
MESSAGE_TYPE_BAD_PRICE: Final[str] = "bad_price"

#: Type for formula error messages.
MESSAGE_TYPE_FORMULA_ERROR: Final[str] = "formula_error"

#: Type for missing or outdated fee messages.
MESSAGE_TYPE_NEED_FEE_UPDATE: Final[str] = "need_fee_update"

#: Type for missing scraping price messages.
MESSAGE_TYPE_NO_PRICE_SCRAPPING: Final[str] = "no_price_scrapping"

#: Type for missing suppliers collection messages.
MESSAGE_TYPE_NO_SUPPLIERS_COLLECTION: Final[str] = "no_suppliers_collection"

#: Type for forbidden supplier / item messages.
MESSAGE_TYPE_BAD_SUPPLIER: Final[str] = "bad_supplier"

#: Type for access (no permissions) problems.
MESSAGE_TYPE_NO_ACCESS: Final[str] = "no_access"

#: Type for missing current-month sheet messages.
MESSAGE_TYPE_NO_SHEET: Final[str] = "no_sheet"

#: Type for checker-related messages (too many "No stock").
MESSAGE_TYPE_INSPECT_CHECKER: Final[str] = "inspect_checker"
