import datetime


class Collector:
    def __init__(self):
        pass

    @staticmethod
    def define_months() -> tuple[int, int]:
        now_month = datetime.datetime.now().month
        prev_month = now_month - 1 if now_month != 1 else 12
        return now_month, prev_month
