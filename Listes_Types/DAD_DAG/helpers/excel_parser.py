

import openpyxl
from rapidfuzz import process, fuzz
import re
from collections import Counter

class excel:
    def __init__(self, filename, context=None):
        self.filename = filename
        self.wb = None
        self.refs_desc = {}
        self.context = context

    def close(self):
        if self.wb:
            self.wb.close()

    def load(self):
        self.wb=openpyxl.load_workbook(self.filename, data_only=True)


    def detect_desc_col(self, ws):
        cols=[]
        for row in ws:
            for cell in row:
                if cell.value is not None and 20 <= len(str(cell.value)):
                    cols.append(cell.column)
                    break
        most_common_item = None
        if cols:
            most_common_item = Counter(cols).most_common(1)[0][0]
        return most_common_item # Returns 1

    def build_refs_desc_mapping(self):
        refs_desc = {}
        fscf=self.context.fscfai_files.keys()
        for ws in self.wb:
            if ws.title in ["MINOR HARNESS", "Notice utilisation PTA PLM", "Annexe 1", "User manuel PTA PLM", "Annex 1(english)", "Notice d'utilisation HNCT", "SDP (LogicalDiagram)"] :
                continue
            col_number = self.detect_desc_col(ws)
            for row in ws.iter_rows(min_col=col_number, max_col=col_number):
                
                for cell in row:
                    if cell.value==None or self.contains_forinfo(cell):
                        continue

                    ref_cell=self.get_ref_by_desc_cell(cell)
                    if ref_cell:
                        if ref_cell.font.strikethrough:
                            continue
                        if str(ref_cell.value) not in fscf:
                            ref_cell=self.get_ref_by_desc_cell(cell, str(ref_cell.value))
                        if ref_cell:   
                            refs_desc[str(ref_cell.value)] = str(cell.value)
        self.refs_desc=refs_desc
    def search_ref(self, ref):
        for r in self.refs_desc.keys():
            if ref==r:
                return r, self.refs_desc[r]
        return None

    def get_ref_name(self, ref):
        return self.refs_desc.get(ref.value) if ref else None

    # def search_sheet(self, cell):
    #     sheet_title = cell.parent.title
    #     if "DAD" in sheet_title:
    #         return sheet_title.replace("DAD", "DAG")
    #     elif "DAG" in sheet_title:
    #         return sheet_title.replace("DAG", "DAD")
    #     else:
    #         return False
    def contains_forinfo(self, cell):
        
        if cell:
            for row in cell.parent.iter_rows(max_row=cell.row, min_row=cell.row):
                for c in row:
                    if c.value and ("forinfo" in str(c.value).lower() or "cancelled" in str(c.value).lower()):
                        return True
        return False


        PART_ID_RE = re.compile(r'\b[A-Z]{1,5}[0-9]{1,4}[A-Z]?\b')
        

        

    

    
    def find_matched_desc(self, ref, desc, threshold=40):
        if 'DAG' in desc.upper():
            candidates = [
                d.upper() for r, d in self.refs_desc.items() if r != ref and 'DAG' not in d
            ]
        else:
            candidates = [
                d.upper() for r, d in self.refs_desc.items() if r != ref and 'DAG' not in d and 'DAD' not in d
            ]
        if not candidates:
            return None

        desc_upper = desc.upper()

        
        if 'DAG' in desc_upper:
            desc=desc_upper.replace('DAG', 'DAD')
            candidates  = [c for c in candidates if 'DAD' in c.upper()]
           

        if not candidates:
            return None

        query = re.sub(r'\bDAG\b', 'DAD', desc, flags=re.IGNORECASE)
        
        scored=[]
        if 'DAD' not in query.upper():
            scored = sorted(
            ((c, fuzz.token_set_ratio(query.upper(), c)) for c in candidates),
            key=lambda x: -x[1])
        else:
            scored = sorted(
            ((c, fuzz.token_sort_ratio(query.upper(), c)) for c in candidates),
            key=lambda x: -x[1])
    

        best_label, best_score = scored[0]

       
        return best_label if best_score >= threshold else None



    # def find_target_cell_column(self, cell):
    #     col_idx = cell.column
    #     # if isinstance(col_idx, str):
    #     #     from openpyxl.utils import column_index_from_string
    #     #     col_idx = column_index_from_string(col_idx)
    #     cell_value = str(cell.value)
    #     list_desc = []
    #     map_cell_desc = {}
    #     worksheet = cell.parent
    #     column_cells = list(worksheet.iter_cols(min_col=col_idx, max_col=col_idx))[0]
    #     for col_cell in column_cells:
    #         next_cell = worksheet.cell(row=col_cell.row + 1, column=col_idx)
    #         if next_cell.value is not None:
    #             if cell.coordinate == next_cell.coordinate or self.contains_forinfo(next_cell):
    #                 continue
    #             next_value = str(next_cell.value)
    #             map_cell_desc[next_value] = next_cell
    #             list_desc.append(next_value)
    #     best_match = None
    #     if('DAD' in cell_value.upper()):
    #         cleaned_list=[i for i in list_desc if 'DAD' not in i]
    #         best_match = process.extractOne(cell_value, cleaned_list, scorer=fuzz.WRatio)
    #     elif('DAG' in cell_value.upper()):
    #         cleaned_list=[i for i in list_desc if 'DAG' not in i]
    #         best_match = process.extractOne(cell_value, cleaned_list, scorer=fuzz.WRatio)

    #     if not best_match:
    #         return None
    #     return map_cell_desc.get(best_match[0])
    def get_ref_by_desc_cell(self, desc_cell, jump_value=None):
        for row in desc_cell.parent.iter_rows(min_row=desc_cell.row, max_row=desc_cell.row):
            for cell in row:
                if jump_value and str(cell.value)==jump_value:
                    continue
                if cell.value is not None and re.match(r"\d{10}", str(cell.value)):
                    return cell
        return None
    def get_ref_by_desc(self, desc):
        for r, d in self.refs_desc.items():
            if desc==d.upper():
                return r
            
    def get_fus_name(self, desc):
        if desc:
            if desc[:2].upper()=='PR': return desc=='PR'
            if desc[:4].upper()=='EHAB': return desc[:5].upper()
            return None


    # def find_desc_in_other_sheet(self, desc, sheet_name):
    #     list_desc = []
    #     map_cell_desc = {}
    #     if sheet_name in self.wb.sheetnames:
    #         column_cells = list(self.wb[sheet_name].iter_cols(min_col=desc.column, max_col=desc.column))[0]
    #         for cell in column_cells:
    #             # FIX 1: Ignore empty Excel cells entirely so they don't become the string "None"
    #             if cell.value is None:
    #                 continue
                    
    #             if self.contains_forinfo(cell):
    #                 continue
                    
    #             cell_value = str(cell.value)
    #             map_cell_desc[cell_value] = cell
    #             list_desc.append(cell_value)

    #     # FIX 2: Change scorer to token_set_ratio to force a strict word-to-word match
    #     best_match = process.extractOne(str(desc.value), list_desc, scorer=fuzz.token_set_ratio)

    #     if not best_match:
    #         return None
    #     return map_cell_desc.get(best_match[0])

        
    def start(self, ref, old_xml_path=None):
        ref_desc = self.search_ref(ref)
        if ref_desc\
        and ((('DAG' in ref_desc[1].upper()) and not('DAD' in ref_desc[1].upper())) \
        or ('50-PB' in old_xml_path or '60-PA' in old_xml_path) \
        or ('LHD' in ref_desc[1].upper())):
               
        
            target_desc = self.find_matched_desc(ref_desc[0], ref_desc[1]) if ref_desc else None
            target_ref = self.get_ref_by_desc(target_desc) if target_desc else None
            return [ref_desc, target_desc, target_ref]
        return None
# excel1= excel("C:/Users/User/OneDrive/Bureau/OV512  DAG DAD/OV512  DAG DAD/PTA_OV512E MCA_F0226.xlsm")
# print(excel1.start("9872939080"))

    
    


    