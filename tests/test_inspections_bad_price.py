import pytest

import attention_sender.inspections as insp_mod
from attention_sender.inspections import Inspect


class FakeDB:
    """Minimal async context manager to replace DataBase in tests."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def check_values_in_columns(self, shop_name, message_type, order_id):
        # In this test we want to simulate that DB has no existing records
        return False

    async def get_message(self, **filters):
        return None

    async def delete_message(self, **filters):
        return None


@pytest.mark.asyncio
async def test_bad_price_handler_sends_message(monkeypatch, tmp_path):
    """
    bad_price_handler should call send_message() when profit <= threshold
    and there is no existing record in DB.
    """
    # Prepare fake staff json file (empty is enough for this test)
    staff_file = tmp_path / "staff.json"
    staff_file.write_text("{}", encoding="utf-8")

    inspector = Inspect(staff_data_ph=str(staff_file))

    # Prepare data with one bad price row
    data = {
        "perc_w_gift": ["-10%"],
        "order_num": ["ORDER-1"],
        "profit_amount": ["-5"],
        "status1": [""],
        "status2": [""],
    }

    # Storage for calls to fake send_message
    calls = []

    async def fake_send_message(chat_id, message, shop_name, mes_type, order):
        calls.append(
            {
                "chat_id": chat_id,
                "message": message,
                "shop_name": shop_name,
                "mes_type": mes_type,
                "order": order,
            }
        )

    # Patch DataBase and send_message inside inspections module
    monkeypatch.setattr(insp_mod, "DataBase", FakeDB)
    monkeypatch.setattr(insp_mod, "send_message", fake_send_message)

    # Run handler
    await inspector.bad_price_handler(
        data=data,
        chat_id=123456,
        shop="test_shop",
        sheet="3",
    )

    # We expect exactly one message to be sent
    assert len(calls) == 1
    call = calls[0]
    assert call["chat_id"] == 123456
    assert call["shop_name"] == "test_shop"
    assert call["mes_type"] == "bad_price"
    assert call["order"] == "ORDER-1"
    # Very basic check that message text contains order and sheet
    assert "ORDER-1" in call["message"]
    assert "3" in call["message"]
