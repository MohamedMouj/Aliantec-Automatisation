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

 
    def extract_label(self, cell_value):
        matched=[]
        if cell_value is None:
            return None
        val = str(cell_value).strip()
        if val == "":
            return None
        
        match = re.search(r"\b(?=[A-Z]*[0-9])[A-Z0-9]{5}\b", val)
        if match:
            for mch in re.finditer(r"\b(?=[A-Z]*[0-9])[A-Z0-9]{5}\b", val):
                matched.append(mch.group())
            return matched
        elif "Générique" in val:
            matched.append("DXD00")
            return matched
        else:
            return None

    def search_col_by_label(self, label):
        header_row = self.sheet_to_extract[1] 
        cols=[] 
        for lab in label:
            prefix = lab[:3]
            
            for cell in header_row:
                if cell.value is not None and str(cell.value).strip().startswith(prefix):
                    cols.append(cell.column)
                    continue
        return cols if cols else None

    def find_vin_row(self, cols, label):
        rows=[]
        duplicate_rows=[]

        map_label_col = {col: lab[3:] for col, lab in zip(cols, label)}
       

        for col, label in map_label_col.items():
            if len(label)>1 and label.startswith("0"):
                label = label[1:]
                if len(label)>1 and label.startswith("0"):
                    label = label[1:]
            #--------------------------------------------
            for row in self.sheet_to_extract.iter_rows(
                min_col=col, max_col=col
            ):
                cell = row[0]
                if cell.value is not None and str(cell.value).strip() == label:
                    rows.append(cell.row)
                    if col==cols[-1]:
                            duplicate_rows.append(cell.row)


        
        rows=[r for r in rows if r in duplicate_rows]
        return rows[0] if rows else None

    def get_data(self):
        elec={}
        imp={}
        for row in self.main_sheet.iter_rows(min_row=3):
    
            for cell in row[8:]:
                if cell.value is not None:
                    if cell.column%2!=0:
                        sommaire=str(row[0].value)
                        schema=str(row[1].value)
                        elec[str(cell.value)]=[schema, sommaire]
                    else:
                        sommaire=str(row[0].value)
                        schema=str(row[1].value)
                        imp[str(cell.value)]=[schema, sommaire]

        return [elec,imp]



    def write_elec_data(self, elec):
        self.wb.create_sheet("ELEC")
        ws=self.wb["ELEC"]
        ws.append(["Sommaire", "Schema", "ELEC"])
        for code, data in elec.items():
            ws.append([data[0], data[1], code])


    def write_imp_data(self, imp,):
        self.wb.create_sheet("IMP")
        ws=self.wb["IMP"]
        ws.append(["Sommaire", "Schema", "IMP"])
        for code, data in imp.items():
            ws.append([data[0], data[1], code])


    def find_vin(self, row_idx):
        if row_idx is None:
            return None
        cell = self.sheet_to_extract.cell(row=row_idx, column=4)  
        if cell.value is None or str(cell.value).strip() == "":
            return None
        return str(cell.value).strip()

    def start(self, output_path=None):
        results = []

        for row in self.main_sheet.iter_rows():
            row_number = row[0].row

            if row_number <= 2:
                continue

            d_cell = row[3]  # column D
            lab = self.extract_label(d_cell.value)

            if not lab or len(lab) == 0:
                continue
            
            labels=(", ").join(lab) if isinstance(lab, list) else lab if isinstance(lab, list) else lab
            cols = self.search_col_by_label(lab)
            if cols is None:
                results.append({
                    "row": row_number,
                    "label": labels,
                    "vin": None,
                    "status": "warn",
                    "message": f"No column found for label '{lab}'"
                })
                continue

            vin_row = self.find_vin_row(cols, lab)
            vin = self.find_vin(vin_row)

            if vin:
                self.main_sheet.cell(row=row_number, column=7).value = vin
                results.append({
                    "row": row_number,
                    "label": labels,
                    "vin": vin,
                    "status": "ok",
                    "message": "VIN written"
                })
            # else:
            #     results.append({
            #         "row": row_number,
            #         "label": labels,
            #         "vin": None,
            #         "status": "warn",
            #         "message": f"No VIN found for label '{lab}'"
            #     })

        data=self.get_data()
        self.write_elec_data(data[0])
        self.write_imp_data(data[1])

        save_path = output_path or self.excel_file_name
        self.wb.save(save_path)
        return results, save_path


