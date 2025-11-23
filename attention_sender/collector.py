import datetime
from typing import Tuple


class Collector:
    """
    Helper class for collecting date-related information.

    Currently responsible for:
      - detecting current month,
      - computing previous month (with year wrap-around: January -> December).
    """

    def __init__(self) -> None:
        """No state is required at the moment."""
        pass

    @staticmethod
    async def define_months() -> Tuple[int, int]:
        """
        Return current and previous month numbers.

        Example:
          - If today is 2025-03-15 → (3, 2)
          - If today is 2025-01-10 → (1, 12)

        :return: tuple (current_month, previous_month)
        """
        now = datetime.datetime.now()
        now_month = now.month
        prev_month = now_month - 1 if now_month != 1 else 12
        return now_month, prev_month
