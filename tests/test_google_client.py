import pytest

from attention_sender.google_client import GoogleSheetsClient


def test_get_columns_indices_success():
    """get_columns_indices should map logical names to correct header indices."""
    data = [
        ["Order ID", "Status 1", "Status 2", "Profit amount"],
        ["1", "ok", "", "10"],
        ["2", "bad", "", "-5"],
    ]
    columns_cfg = {
        "order_num": "Order ID",
        "status1": "Status 1",
        "status2": "Status 2",
        "profit_amount": "Profit amount",
    }

    indices = GoogleSheetsClient.get_columns_indices(data, columns_cfg)

    assert indices["order_num"] == 0
    assert indices["status1"] == 1
    assert indices["status2"] == 2
    assert indices["profit_amount"] == 3


def test_get_columns_indices_missing_header_raises():
    """get_columns_indices should raise KeyError if header is missing."""
    data = [
        ["Order ID", "Status 1"],  # no "Profit amount"
        ["1", "ok"],
    ]
    columns_cfg = {
        "order_num": "Order ID",
        "profit_amount": "Profit amount",
    }

    with pytest.raises(KeyError):
        GoogleSheetsClient.get_columns_indices(data, columns_cfg)
