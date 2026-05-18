import openpyxl
import re

class ExcelHelper:
    def __init__(self, excel_file):
        self.excel_file = excel_file
        self.wb = openpyxl.load_workbook(self.excel_file, read_only=True, data_only=True)
        self.data=None

    def close(self):
        if hasattr(self, 'wb'):
            self.wb.close()

    def get_all_ref_couples(self):
        data_list=[]
        for sheet in self.wb.worksheets:
            for row in sheet.iter_rows():
                data=dict()
                ref=self.find_first_valid_ref_from_left(row)
                if ref is None:
                    continue
                data["OLD"]=self.extract_reference_from_cell(ref)    
                ref=self.find_first_valid_ref_from_left(row, [data.get("OLD")])
                if ref is not None:
                    data["NEW"]=self.extract_reference_from_cell(ref) 
                else:
                    data["NEW"]=None
                
                data_list.append(data.copy())
        return data_list
            
    def extract_reference_from_cell(self, cell):
       
       
        # if re.fullmatch(r"\d{10}", value):
        #     return value
        # match = re.match(r"^(\d{10})[-_*/.\\\\s]\d{2}", value)
        # if match:
        #     return match.group(1)
        # return None
        if cell is None or cell.value is None:
            return None
        value = str(cell.value).strip()
        match = re.search(r"\d{10}", value)
        if match:
            return match.group(0)
        return None

    def find_first_valid_ref_from_left(self, row, jump_values=None):
        aux=True
        for cell in row:
            cur = self.extract_reference_from_cell(cell)
            if jump_values and cur in jump_values and aux:
                aux=False
                continue
            if cur is not None:
                return cell
        return None