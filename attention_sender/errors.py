from typing import Union, List, Dict, Optional


async def google_sheet_err_proc(
    g_proc_res: Union[List, Dict]
) -> str:
    """
    Process Google Sheets API result and classify possible error states.

    The function is designed to work with two typical cases:

      1) API returns a dict with a structure like:
         {
           "status": "error",
           "errors": [
             { "forbidden": "... details ..." },
             { "http_error_500": "... details ..." },
             ...
           ]
         }

      2) API returns an empty list [] when request failed in some way.

    It returns one of:
      - "forbidden"  → no access to the sheet (HTTP 403)
      - "bad_req"    → server or request error (HTTP 500 or empty list)
      - "ok"         → everything looks good

    :param g_proc_res: Google Sheets processing result
    :return: string status: "forbidden", "bad_req" or "ok"
    """
    # Case 1: structured error response as dict
    if isinstance(g_proc_res, dict):
        if g_proc_res.get("status") == "error" and g_proc_res.get("errors"):
            for error in g_proc_res.get("errors", []):
                for key in error.keys():
                    if "forbidden" in key:
                        return "forbidden"
                    if "http_error_500" in key:
                        return "bad_req"

    # Case 2: empty list returned by client
    elif isinstance(g_proc_res, list) and len(g_proc_res) == 0:
        return "bad_req"

    # Default: everything is fine
    return "ok"
