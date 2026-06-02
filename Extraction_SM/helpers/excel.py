import openpyxl
import re

from openpyxl import cell


class ExcelParser:
    SHEET_NAME = "Sommaire"
    SHEET_NAME_EXTRACTION = "Extraction SM"
    def __init__(self, excel_file_name):
        self.excel_file_name = excel_file_name
        self.wb = None
        self.sheet = None

    def load_excel(self):
        self.wb = openpyxl.load_workbook(self.excel_file_name, data_only=True)

        if self.SHEET_NAME not in self.wb.sheetnames or self.SHEET_NAME_EXTRACTION not in self.wb.sheetnames:
            raise KeyError(
                f"Sheet '{self.SHEET_NAME}' or '{self.SHEET_NAME_EXTRACTION}' not found. "
                f"Available: {self.wb.sheetnames}"
            )

        self.sheet = self.wb[self.SHEET_NAME]
        self.sheet_extraction = self.wb[self.SHEET_NAME_EXTRACTION]

    def close(self):
        if self.wb:
            self.wb.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def determine_rows_to_remove(self):
        last_col = self.sheet.max_column
        aux=False
        rows_to_delete=[]
        for cell in list(self.sheet.columns)[last_col - 1]:
            if cell.fill and cell.fill.fill_type == "solid":
                color = cell.fill.fgColor

                if color.type == "theme" and color.theme in (0, 1):
                    if (color.tint and round(color.tint, 2) == -0.25) or  color.type == "rgb" and color.rgb in ("C0C0C0", "FFC0C0C0"):
                        if not aux:
                            aux=True    
                        continue
            if aux and cell.value is None or str(cell.value).strip() == "":
                rows_to_delete.append(cell.row)
        return rows_to_delete

    def delete_rows(self, rows_to_delete):
        for row in sorted(rows_to_delete, reverse=True):
            self.sheet.delete_rows(row)
    
    def create_col_before_last_column(self):
        last_col_index = self.sheet.max_column  
        self.sheet.insert_cols(last_col_index)
        return list(self.sheet.iter_cols(min_col=last_col_index, max_col=last_col_index))[0]
    
    def get_last_line_value(self, row_number):
        value = ""
        for cell in list(self.sheet.rows)[row_number - 1][:-2]:  # Exclude the last column
            if (cell.value
                    and str(cell.value).strip()
                    and re.fullmatch(r"[A-Z0-9]{7}", str(cell.value).strip())):
                value = cell.value
        return value

    def get_description(self, code):
        description = []
        for cell in list(self.sheet_extraction.columns)[1]:
            if (cell.value
                    and str(cell.value).strip()
                    and code in str(cell.value).strip()):
                description.append(cell.offset(column=8).value)
        return description


    # ------------------------------------------------------------------
    # Main process
    # ------------------------------------------------------------------

    def start(self, output_path=None):
        results = []
        rows_to_delete = self.determine_rows_to_remove()

        if not rows_to_delete:
            save_path = output_path or self.excel_file_name
            if output_path:
                self.wb.save(save_path)
            return results, save_path

        self.delete_rows(rows_to_delete)

        for cell in self.create_col_before_last_column():
            value = self.get_last_line_value(cell.row)
            if value:
                cell.value = value
                description = self.get_description(value)
                if description and len(description) > 0:
                    cell.offset(column=2).value = ("; ".join(str(d) for d in description if d is not None))
                results.append({
                    "row": cell.row,
                    "value": str(value),
                    "status": "ok",
                    "message": "Value extracted"
                })

        save_path = output_path or self.excel_file_name
        self.wb.save(save_path)
        return results, save_path


# if __name__ == "__main__":
#     excel = ExcelParser(
#         r"C:\Users\User\OneDrive\Bureau\Sommaire pour contexte test.xlsx"
#     )
#     excel.load_excel()
#     results, _ = excel.start()
#     for r in results:
#         print(f"Row {r['row']}: {r['value']}")
#     excel.close()