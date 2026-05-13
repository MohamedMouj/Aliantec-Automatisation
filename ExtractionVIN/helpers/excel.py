import openpyxl
import re
import os


class ExcelParser:
    MAIN_SHEET    = "Validation Web"
    EXTRACT_SHEET = "Extraction VIN"

    def __init__(self, excel_file_name):
        self.excel_file_name = excel_file_name
        self.wb = None
        self.main_sheet = None
        self.sheet_to_extract = None

    def load_excel(self):
        self.wb = openpyxl.load_workbook(self.excel_file_name, data_only=True)

        if self.MAIN_SHEET not in self.wb.sheetnames:
            raise KeyError(
                f"Sheet '{self.MAIN_SHEET}' not found. "
                f"Available: {self.wb.sheetnames}"
            )
        if self.EXTRACT_SHEET not in self.wb.sheetnames:
            raise KeyError(
                f"Sheet '{self.EXTRACT_SHEET}' not found. "
                f"Available: {self.wb.sheetnames}"
            )

        self.main_sheet = self.wb[self.MAIN_SHEET]
        self.sheet_to_extract = self.wb[self.EXTRACT_SHEET]

    def close(self):
        if self.wb:
            self.wb.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def extract_label(self, cell_value):
        """Return a 5-char label from a cell, or None."""
        if cell_value is None:
            return None
        val = str(cell_value).strip()
        if val == "":
            return None
        match = re.search(r"[A-Z0-9]{5}", val)
        if match:
            return match.group(0)
        if "Générique" in val:
            return "DXD00"
        return None

    def search_col_by_label(self, label):
        """
        Search the header row (row 1) of sheet_to_extract for a column
        whose header starts with the first 3 chars of label.
        Returns the 1-based column index, or None.
        """
        prefix = label[:3]
        header_row = self.sheet_to_extract[1]  # openpyxl row 1 = first row
        for cell in header_row:
            if cell.value is not None and str(cell.value).strip().startswith(prefix):
                return cell.column  # 1-based
        return None

    def find_vin_row(self, col_idx, label):
        """
        Search column col_idx (1-based) in sheet_to_extract for the
        row whose value matches label[3:], stripping a leading '0' if present.
        Returns the 1-based row index, or None.
        """
        suffix = label[3:]
        if suffix.startswith("0"):
            suffix = suffix[1:]

        for row in self.sheet_to_extract.iter_rows(
            min_col=col_idx, max_col=col_idx
        ):
            cell = row[0]
            if cell.value is not None and str(cell.value).strip() == suffix:
                return cell.row  # 1-based
        return None

    def find_vin(self, row_idx):
        """
        Read column D (column 4, 1-based) of sheet_to_extract at row_idx.
        Returns the VIN string, or None.
        """
        if row_idx is None:
            return None
        cell = self.sheet_to_extract.cell(row=row_idx, column=4)  # col D
        if cell.value is None or str(cell.value).strip() == "":
            return None
        return str(cell.value).strip()

    # ------------------------------------------------------------------
    # Main process
    # ------------------------------------------------------------------

    def start(self, output_path=None):
        """
        Iterate column D (col 4) of main_sheet.
        For each label found, look up its VIN and write it into
        column G (col 7) of the same row, skipping the first 2 rows.

        Returns a list of dicts with processing results for the UI.
        Saves the workbook to output_path (or self.excel_file_name if None).
        """
        results = []

        for row in self.main_sheet.iter_rows():
            row_number = row[0].row

            # openpyxl rows are 1-based; skip header rows 1 and 2
            if row_number <= 2:
                continue

            # Column D = index 3 in the row tuple (0-based)
            d_cell = row[3]  # column D
            lab = self.extract_label(d_cell.value)

            if not lab:
                continue

            col = self.search_col_by_label(lab)
            if col is None:
                results.append({
                    "row": row_number,
                    "label": lab,
                    "vin": None,
                    "status": "warn",
                    "message": f"No column found for label '{lab}'"
                })
                continue

            vin_row = self.find_vin_row(col, lab)
            vin = self.find_vin(vin_row)

            if vin:
                # Write VIN into column G (col 7) of main_sheet
                self.main_sheet.cell(row=row_number, column=7).value = vin
                results.append({
                    "row": row_number,
                    "label": lab,
                    "vin": vin,
                    "status": "ok",
                    "message": "VIN written"
                })
            else:
                results.append({
                    "row": row_number,
                    "label": lab,
                    "vin": None,
                    "status": "warn",
                    "message": f"No VIN found for label '{lab}'"
                })

        save_path = output_path or self.excel_file_name
        self.wb.save(save_path)
        return results, save_path


# if __name__ == "__main__":
#     excel = ExcelParser(
#         r"C:\Users\User\OneDrive\Bureau\Validation Web (OV64 RHD - F10-2025).....xlsx"
#     )
#     excel.load_excel()
#     results, _ = excel.start()
#     for r in results:
#         print(f"Row {r['row']}: [{r['status']}] {r['label']} → {r['vin'] or r['message']}")
#     excel.close()