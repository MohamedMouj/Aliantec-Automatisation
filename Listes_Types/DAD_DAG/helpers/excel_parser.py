import openpyxl
from rapidfuzz import process, fuzz
import re

class excel:
    def __init__(self, filename):
        self.filename = filename
        self.wb = None
    
    def close(self):
        if self.wb:
            self.wb.close()

    def load(self):
        self.wb=openpyxl.load_workbook(self.filename)

    def search_ref(self, ref):
        for ws in self.wb:
            if 'minor harness' in ws.title.lower() or 'harness mineur' in ws.title.lower():
                continue
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value == ref:
                        return cell
        return None

    def get_ref_name(self, ref_cell):
        if ref_cell:
            for row in ref_cell.parent.iter_rows(min_row=ref_cell.row, max_row=ref_cell.row):
                for cell in row:
                    if cell.value is not None and 20 <= len(str(cell.value)):
                        return cell

    def search_sheet(self, cell):
        sheet_title = cell.parent.title
        if "DAD" in sheet_title:
            return sheet_title.replace("DAD", "DAG")
        elif "DAG" in sheet_title:
            return sheet_title.replace("DAG", "DAD")
        else:
            return False
    def contains_forinfo(self, cell):
        
        if cell:
            for row in cell.parent.iter_rows(min_row=cell.row, max_row=cell.row):
                for c in row:
                    if c.value and "forinfo" in str(c.value).lower():
                        return True
        return False
    def find_target_cell_column(self, cell):
        col_idx = cell.column
        # if isinstance(col_idx, str):
        #     from openpyxl.utils import column_index_from_string
        #     col_idx = column_index_from_string(col_idx)
        cell_value = str(cell.value)
        list_desc = []
        map_cell_desc = {}
        worksheet = cell.parent
        column_cells = list(worksheet.iter_cols(min_col=col_idx, max_col=col_idx))[0]
        for col_cell in column_cells:
            next_cell = worksheet.cell(row=col_cell.row + 1, column=col_idx)
            if next_cell.value is not None:
                if cell.coordinate == next_cell.coordinate or self.contains_forinfo(next_cell):
                    continue
                next_value = str(next_cell.value)
                map_cell_desc[next_value] = next_cell
                list_desc.append(next_value)
        best_match = None
        if('DAD' in cell_value.upper()):
            cleaned_list=[i for i in list_desc if 'DAD' not in i]
            best_match = process.extractOne(cell_value, cleaned_list, scorer=fuzz.WRatio)
        elif('DAG' in cell_value.upper()):
            cleaned_list=[i for i in list_desc if 'DAG' not in i]
            best_match = process.extractOne(cell_value, cleaned_list, scorer=fuzz.WRatio)

        if not best_match:
            return None
        return map_cell_desc.get(best_match[0])

    def get_ref_by_desc(self, desc_cell):
        for row in desc_cell.parent.iter_rows(min_row=desc_cell.row, max_row=desc_cell.row):
            for cell in row:
                if cell.value is not None and re.match(r"\d{10}", str(cell.value)):
                    return cell
                
    def find_desc_in_other_sheet(self, desc, sheet_name):
        list_desc = []
        map_cell_desc = {}
        if sheet_name in self.wb.sheetnames:
            column_cells = list(self.wb[sheet_name].iter_cols(min_col=desc.column, max_col=desc.column))[0]
            for cell in column_cells:
                # FIX 1: Ignore empty Excel cells entirely so they don't become the string "None"
                if cell.value is None:
                    continue
                    
                if self.contains_forinfo(cell):
                    continue
                    
                cell_value = str(cell.value)
                map_cell_desc[cell_value] = cell
                list_desc.append(cell_value)

        # FIX 2: Change scorer to token_set_ratio to force a strict word-to-word match
        best_match = process.extractOne(str(desc.value), list_desc, scorer=fuzz.token_set_ratio)

        if not best_match:
            return None
        return map_cell_desc.get(best_match[0])

        
    def start(self, ref):
       
        ref_cell = self.search_ref(ref)
        if not ref_cell:
            return None
        desc_cell = self.get_ref_name(ref_cell)
        if not desc_cell:
            return None
        you_can_find_desc_in_other_sheet = self.search_sheet(desc_cell)
        if you_can_find_desc_in_other_sheet:
            target_cell = self.find_desc_in_other_sheet(desc_cell, you_can_find_desc_in_other_sheet)
            target_ref = self.get_ref_by_desc(target_cell) if target_cell else None
        else:
            target_cell = self.find_target_cell_column(desc_cell)
            target_ref = self.get_ref_by_desc(target_cell) if target_cell else None
        return [ref_cell, desc_cell, target_cell, target_ref]

# excel1= excel()
# print(excel1.start("9871587880", "C:/Users/User/OneDrive/Bureau/OV512  DAG DAD/OV512  DAG DAD/PTA_OV512E MCA_F0226.xlsm"))

    
    


    