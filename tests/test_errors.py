import pytest

from attention_sender.errors import google_sheet_err_proc


@pytest.mark.asyncio
async def test_google_sheet_err_proc_forbidden():
    """Should return 'forbidden' if errors contain a forbidden entry."""
    data = {
        "status": "error",
        "errors": [
            {"some_other_error": "smth"},
            {"forbidden_403": "no access"},
        ],
    }

    res = await google_sheet_err_proc(data)
    assert res == "forbidden"


@pytest.mark.asyncio
async def test_google_sheet_err_proc_bad_req_on_http_500():
    """Should return 'bad_req' if errors contain http_error_500."""
    data = {
        "status": "error",
        "errors": [
            {"http_error_500": "server error"},
        ],
    }

    res = await google_sheet_err_proc(data)
    assert res == "bad_req"


@pytest.mark.asyncio
async def test_google_sheet_err_proc_bad_req_on_empty_list():
    """Should return 'bad_req' for an empty list result."""
    data = []

    res = await google_sheet_err_proc(data)
    assert res == "bad_req"


@pytest.mark.asyncio
async def test_google_sheet_err_proc_ok_otherwise():
    """Should return 'ok' if result does not match error patterns."""
    data = {
        "status": "success",
        "sheets": ["1", "2", "3"],
    }

    res = await google_sheet_err_proc(data)
    assert res == "ok"
