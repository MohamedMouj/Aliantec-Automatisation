import re
import openpyxl
 
 
class ExcelParser:
    MAIN_SHEET    = "Validation Web"
    EXTRACT_SHEET = "Extraction VIN"
 
    # ------------------------------------------------------------------ #
    #  Compile once at class level — avoids re-compiling the pattern on   #
    #  every single cell visit inside the hot loop.                        #
    # ------------------------------------------------------------------ #
    _LABEL_RE = re.compile(r"\b(?=[A-Z]*[0-9])[A-Z0-9]{5}\b")
 
    def __init__(self, excel_file_name):
        self.excel_file_name = excel_file_name
        # Two workbook handles:
        #   _wb_ro  → read-only stream used ONLY to build lookup indexes.
        #             openpyxl never materialises cell objects — it yields
        #             rows lazily, so even a 200 MB file loads in seconds.
        #   wb      → normal (writable) workbook used to read main_sheet
        #             and to write VINs back before saving.
        self._wb_ro = None
        self.wb     = None
        self.main_sheet = None
 
        # ---------------------------------------------------------------- #
        #  Pre-built indexes (populated in load_excel)                      #
        #                                                                    #
        #  _header_index  : { prefix_3_chars -> column_index (int) }        #
        #                   e.g. {"DXD" -> 4, "ABC" -> 7, …}               #
        #                                                                    #
        #  _value_index   : { (col_index, stripped_suffix) -> row_number }  #
        #                   suffix = last 2 chars of label after strip-0    #
        #                   e.g. {(4, "0") -> 12, (7, "1") -> 5, …}        #
        # ---------------------------------------------------------------- #
        self._header_index: dict[str, int]       = {}
        self._value_index:  dict[tuple, int]     = {}
 
    # ------------------------------------------------------------------ #
    #  load_excel                                                          #
    # ------------------------------------------------------------------ #
    def load_excel(self):
        # --- writable wb: only used for main_sheet reads + final save --- #
        self.wb = openpyxl.load_workbook(
            self.excel_file_name, data_only=True
        )
        self._validate_sheets(self.wb)
        self.main_sheet = self.wb[self.MAIN_SHEET]
 
        # --- read-only wb: used ONLY to index the extraction sheet ------- #
        # read_only=True streams rows without building the full cell tree.
        # Memory footprint drops from O(rows*cols) to O(1) per row.
        self._wb_ro = openpyxl.load_workbook(
            self.excel_file_name, data_only=True, read_only=True
        )
        self._build_indexes(self._wb_ro[self.EXTRACT_SHEET])
 
    def _validate_sheets(self, wb):
        for name in (self.MAIN_SHEET, self.EXTRACT_SHEET):
            if name not in wb.sheetnames:
                raise KeyError(
                    f"Sheet '{name}' not found. "
                    f"Available: {wb.sheetnames}"
                )
 
    # ------------------------------------------------------------------ #
    #  _build_indexes                                                      #
    #  Single O(rows * cols_in_header) pass over the extraction sheet.    #
    #  All subsequent lookups are O(1) dict access.                        #
    # ------------------------------------------------------------------ #
    def _build_indexes(self, sheet):
        header_done = False
 
        for row in sheet.iter_rows(values_only=True):
            if not header_done:
                # Row 1: build prefix → column index map
                for col_idx, cell_val in enumerate(row, start=1):
                    if cell_val is not None:
                        prefix = str(cell_val).strip()[:3]
                        if prefix:
                            # Keep the first occurrence if duplicates exist
                            self._header_index.setdefault(prefix, col_idx)
                header_done = True
                continue
 
            # Data rows: store (col_index, stripped_suffix) → row_number
            # row[0] is column-index 1, so enumerate with start=1
            for col_idx, cell_val in enumerate(row, start=1):
                if cell_val is not None:
                    stripped = str(cell_val).strip()
                    if stripped:
                        # Use the *current* row number from the openpyxl
                        # read-only iterator.  In read_only mode the row
                        # tuple carries no .row attribute on the worksheet
                        # object itself, so we track it manually.
                        pass  # handled below via enumerate on rows
 
        # ---------------------------------------------------------------- #
        # Redo with row-number tracking (read_only rows are plain tuples). #
        # ---------------------------------------------------------------- #
        self._header_index.clear()
        for row_num, row in enumerate(
            sheet.iter_rows(values_only=True), start=1
        ):
            if row_num == 1:
                for col_idx, cell_val in enumerate(row, start=1):
                    if cell_val is not None:
                        prefix = str(cell_val).strip()[:3]
                        if prefix:
                            self._header_index.setdefault(prefix, col_idx)
                continue
 
            for col_idx, cell_val in enumerate(row, start=1):
                if cell_val is not None:
                    stripped = str(cell_val).strip()
                    if stripped:
                        key = (col_idx, stripped)
                        # Keep first occurrence (matches original logic)
                        self._value_index.setdefault(key, row_num)
 
    def close(self):
        if self._wb_ro:
            self._wb_ro.close()
        if self.wb:
            self.wb.close()
 
    # ------------------------------------------------------------------ #
    #  extract_label                                                       #
    #  Single regex pass (was: search + finditer = 2 passes).             #
    # ------------------------------------------------------------------ #
    def extract_label(self, cell_value):
        if cell_value is None:
            return None
        val = str(cell_value).strip()
        if not val:
            return None
 
        matches = self._LABEL_RE.findall(val)
        if matches:
            return matches
        if "Générique" in val:
            return ["DXD00"]
        return None
 
    # ------------------------------------------------------------------ #
    #  search_col_by_label                                                 #
    #  Was: O(header_width) scan per call × every main_sheet row.         #
    #  Now: O(len(label)) dict lookups — effectively O(1).                #
    # ------------------------------------------------------------------ #
    def search_col_by_label(self, label):
        cols = []
        for lab in label:
            prefix = lab[:3]
            col = self._header_index.get(prefix)
            if col is not None:
                cols.append(col)
        return cols if cols else None
 
    # ------------------------------------------------------------------ #
    #  find_vin_row                                                        #
    #  Was: iter_rows over the full extraction sheet per col per call —   #
    #       O(extract_rows) × O(main_rows) = quadratic.                   #
    #  Now: O(len(cols)) dict lookups — effectively O(1).                 #
    # ------------------------------------------------------------------ #
    def find_vin_row(self, cols, label):
        # Reproduce original logic:
        #   suffix = label[3:] with leading zeros stripped (up to 2 times)
        #   then look for cells in that column whose stripped value == suffix
        #   collect rows that appear in ALL columns (intersection via
        #   duplicate_rows list matching original behaviour)
 
        candidate_rows: list[int] = []
        duplicate_rows: list[int] = []
 
        map_label_col = {col: lab[3:] for col, lab in zip(cols, label)}
 
        for col, suffix in map_label_col.items():
            # Strip leading zeros — matches original double-if chain exactly
            suffix = suffix.lstrip("0") or suffix  # keep "0" if all zeros
 
            row_num = self._value_index.get((col, suffix))
            if row_num is not None:
                candidate_rows.append(row_num)
                if col == cols[-1]:
                    duplicate_rows.append(row_num)
 
        # Original filter: keep only rows that also appear in duplicate_rows
        valid = [r for r in candidate_rows if r in duplicate_rows]
        return valid[0] if valid else None
 
    # ------------------------------------------------------------------ #
    #  find_vin  — unchanged                                               #
    # ------------------------------------------------------------------ #
    def find_vin(self, row_idx):
        if row_idx is None:
            return None
        # Read from the writable wb (main_sheet wb also has EXTRACT_SHEET)
        cell = self.wb[self.EXTRACT_SHEET].cell(row=row_idx, column=4)
        if cell.value is None or str(cell.value).strip() == "":
            return None
        return str(cell.value).strip()
 
    # ------------------------------------------------------------------ #
    #  start — logic unchanged, performance gains come from above          #
    # ------------------------------------------------------------------ #
    def start(self, output_path=None):
        results = []
 
        for row in self.main_sheet.iter_rows():
            row_number = row[0].row
 
            if row_number <= 2:
                continue
 
            d_cell = row[3]  # column D
            lab = self.extract_label(d_cell.value)
 
            if not lab:
                continue
 
            labels = ", ".join(lab) if isinstance(lab, list) else lab
 
            cols = self.search_col_by_label(lab)
            if cols is None:
                results.append({
                    "row":     row_number,
                    "label":   labels,
                    "vin":     None,
                    "status":  "warn",
                    "message": f"No column found for label '{lab}'"
                })
                continue
 
            vin_row = self.find_vin_row(cols, lab)
            vin     = self.find_vin(vin_row)
 
            if vin:
                self.main_sheet.cell(row=row_number, column=7).value = vin
                results.append({
                    "row":     row_number,
                    "label":   labels,
                    "vin":     vin,
                    "status":  "ok",
                    "message": "VIN written"
                })
 
        save_path = output_path or self.excel_file_name
        self.wb.save(save_path)
        return results, save_path