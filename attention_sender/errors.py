async def google_sheet_err_proc(g_proc_res: list | dict) -> str | None:
    if isinstance(g_proc_res, dict):
        if g_proc_res['status'] == 'error' and g_proc_res.get('errors'):
            for error in g_proc_res.get('errors'):
                for key, _ in error.keys():
                    if 'forbidden' in key:
                        return 'forbidden'
                    if 'http_error_500' in key:
                        return 'bad_req'
    elif isinstance(g_proc_res, list) and len(g_proc_res) == 0:
        return 'bad_req'
    return 'ok'
