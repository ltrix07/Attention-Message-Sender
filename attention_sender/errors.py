async def google_sheet_err_proc(g_proc_res: list | dict) -> str | None:
    if isinstance(g_proc_res, dict):
        if g_proc_res.get('errors'):
            if 'forbidden' in g_proc_res.get('errors'):
                return None
    return 'ok'
