from attention_sender.inspections import Inspect


def test_filter_data_by_indices_basic():
    """filter_data_by_indices should build a column->values dict from raw rows."""
    data = [
        ["Order ID", "Status 1", "Profit amount"],  # header
        ["1", "ok", "10"],
        ["2", "bad", "-5"],
    ]

    indices = {
        "order_num": 0,
        "status1": 1,
        "profit_amount": 2,
    }

    # staff_data_ph will not be used in this test, so we can pass any json with {}
    inspector = Inspect(staff_data_ph="tests/fixtures/empty_staff.json")
    filtered = inspector.filter_data_by_indices(data, indices)

    assert filtered["order_num"] == ["1", "2"]
    assert filtered["status1"] == ["ok", "bad"]
    assert filtered["profit_amount"] == ["10", "-5"]
