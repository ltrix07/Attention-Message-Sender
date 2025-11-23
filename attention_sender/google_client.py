from dataclasses import dataclass
from typing import List, Dict, Any, Mapping

from google.oauth2.service_account import Credentials
import gspread


# Scopes for read-only access to Google Sheets
SCOPES = ("https://www.googleapis.com/auth/spreadsheets.readonly",)


@dataclass
class GoogleSheetsClient:
    """
    Thin wrapper around Google Sheets API using gspread.

    Responsibilities:
      - Authorize via service account credentials JSON,
      - Fetch list of sheet titles for a given spreadsheet,
      - Fetch all values from a specific worksheet,
      - Map logical column names to indices based on header row.
    """

    creds_path: str

    def __post_init__(self) -> None:
        """
        Initialize gspread client from service account credentials.
        """
        credentials = Credentials.from_service_account_file(
            self.creds_path, scopes=SCOPES
        )
        self.client = gspread.authorize(credentials)

    # --------------------------------------------------------------------- #
    # Public API                                                            #
    # --------------------------------------------------------------------- #

    def get_sheets_name(self, spreadsheet_id: str) -> List[str]:
        """
        Return a list of sheet titles for the given spreadsheet.

        :param spreadsheet_id: Google Sheets document ID
        :return: list of worksheet titles
        """
        sh = self.client.open_by_key(spreadsheet_id)
        return [ws.title for ws in sh.worksheets()]

    def get_all_info_from_sheet(
        self, spreadsheet_id: str, worksheet_title: str
    ) -> List[List[Any]]:
        """
        Return all values from the given worksheet as a 2D list.

        :param spreadsheet_id: Google Sheets document ID
        :param worksheet_title: worksheet name (tab title)
        :return: list of rows, each row is a list of cell values
        """
        sh = self.client.open_by_key(spreadsheet_id)
        ws = sh.worksheet(worksheet_title)
        return ws.get_all_values()

    @staticmethod
    def get_columns_indices(
        data: List[List[Any]],
        columns_config: Mapping[str, str],
    ) -> Dict[str, int]:
        """
        Map logical column keys to indices based on header row.

        :param data: full sheet data, including header row
        :param columns_config: mapping
               logical_name -> header text in the sheet

               Example:
                 {
                   "order_num": "Order ID",
                   "status1": "Status 1",
                   "status2": "Status 2",
                   "purchase_date": "Purchase date",
                   ...
                 }

        :return: mapping logical_name -> index in row
        :raises KeyError: if any configured header text is not found
        :raises IndexError: if data is empty or header row is missing
        """
        if not data:
            raise IndexError("Sheet data is empty – cannot read header row")

        header = data[0]
        indices: Dict[str, int] = {}

        for logical_name, header_text in columns_config.items():
            try:
                idx = header.index(header_text)
            except ValueError as exc:
                raise KeyError(
                    f"Header '{header_text}' for column '{logical_name}' not found in sheet header"
                ) from exc
            indices[logical_name] = idx

        return indices
