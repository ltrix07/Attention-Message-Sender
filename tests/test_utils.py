from datetime import datetime, timedelta

from attention_sender.utils import today_or_not, message_bad_price


def test_today_or_not_true_for_today():
    """today_or_not() should return True for today's date string."""
    now = datetime.now()
    date_str = now.strftime("%d.%m.%Y %H:%M:%S")

    assert today_or_not(date_str) is True


def test_today_or_not_false_for_other_day():
    """today_or_not() should return False for a different day."""
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime("%d.%m.%Y %H:%M:%S")

    assert today_or_not(date_str) is False


def test_message_bad_price_contains_core_fields():
    """message_bad_price() should include order, profit amount and sheet name."""
    msg = message_bad_price(
        workers="@analyst",
        order="123-ABC",
        prof_amount="$-10.00",
        prof=-15.0,
        shop="test_shop",
        sheet="3",
    )

    assert "123-ABC" in msg
    assert "$-10.00" in msg
    assert "test_shop" in msg
    assert "3" in msg
    assert "@analyst" in msg
