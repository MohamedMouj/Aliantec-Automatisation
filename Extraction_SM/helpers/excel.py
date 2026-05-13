import openpyxl
import re


class ExcelParser:
    SHEET_NAME = "Sommaire"

    def __init__(self, excel_file_name):
        self.excel_file_name = excel_file_name
        self.wb = None
        self.sheet = None

    def load_excel(self):
        self.wb = openpyxl.load_workbook(self.excel_file_name, data_only=True)

        if self.SHEET_NAME not in self.wb.sheetnames:
            raise KeyError(
                f"Sheet '{self.SHEET_NAME}' not found. "
                f"Available: {self.wb.sheetnames}"
            )

        self.sheet = self.wb[self.SHEET_NAME]

    def close(self):
        if self.wb:
            self.wb.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def determine_first_empty_column(self):
        """
        Find the first column where the first 10 cells are all empty.
        Returns the column tuple, or None.
        """
        for col in self.sheet.iter_cols():
            c = 0
            for cell in col:
                if cell.value is not None:
                    break
                c += 1
                if c == 10:
                    return col
        return None

    def get_last_line_value(self, row_number):
        """
        Scan a row and return the last cell value matching [A-Z0-9]{7}.
        """
        value = ""
        for cell in list(self.sheet.rows)[row_number - 1]:
            if (cell.value
                    and str(cell.value).strip()
                    and re.fullmatch(r"[A-Z0-9]{7}", str(cell.value).strip())):
                value = cell.value
        return value

    # ------------------------------------------------------------------
    # Main process
    # ------------------------------------------------------------------

    def start(self, output_path=None):
        """
        Find the first empty column, then for each cell in that column,
        look up the last [A-Z0-9]{7} value on the same row and write it.

        Returns a list of dicts with processing results for the UI.
        Saves the workbook to output_path (or self.excel_file_name if None).
        """
        results = []
        col = self.determine_first_empty_column()

        if col is None:
            return results, output_path or self.excel_file_name

        for cell in col:
            value = self.get_last_line_value(cell.row)
            if value:
                cell.value = value
                results.append({
                    "row": cell.row,
                    "value": str(value),
                    "status": "ok",
                    "message": "Value extracted"
                })

        save_path = output_path or self.excel_file_name
        self.wb.save(save_path)
        return results, save_path


if __name__ == "__main__":
    excel = ExcelParser(
        r"C:\Users\User\OneDrive\Bureau\Sommaire pour contexte test.xlsx"
    )
    excel.load_excel()
    results, _ = excel.start()
    for r in results:
        print(f"Row {r['row']}: {r['value']}")
    excel.close()