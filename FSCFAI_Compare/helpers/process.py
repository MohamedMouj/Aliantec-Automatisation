import os
from pathlib import Path
from .excel import ExcelHelper
from .fs import FsHelper
import difflib
import re
from rapidfuzz import process

class CompareProcess:
    def __init__(self, excel_file, old_folder, new_folder, output_dir=None):
        self.excel_file = excel_file
        self.old_folder = old_folder
        self.new_folder = new_folder
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.excel_helper = ExcelHelper(excel_file)
        self.fs_old = FsHelper(old_folder)
        self.fs_new = FsHelper(new_folder)

    def close(self):
        if hasattr(self, 'excel_helper'):
            self.excel_helper.close()
        

    def normalize_line(self, line):
        nor_line = line[0:6] + line[9:15] + line[70:74] + line[90:line.find("\n")] 
        ind=line.find("\n")
        
        if ind!=-1:
            nor_line +='\n' + self.normalize_line(line[ind+2:]) 
        return nor_line 

    def start(self):
        all_refs_couples = self.excel_helper.get_all_ref_couples()
        results = []
        
        
        for data in all_refs_couples:
            new_ref = data.get("NEW")
            old_ref = data.get("OLD")
            
            if not old_ref or not new_ref:
                continue

            old_fscfai = self.fs_old.find_fscfai_files(new_ref)
            new_fscfai = self.fs_new.find_fscfai_files(old_ref)

            if old_fscfai and new_fscfai:
                print(f"DEBUG: Match found for {new_ref} vs {old_ref}")
                list1, list2, f1, f2 = self.match_with_fuzz(new_fscfai, old_fscfai)
                
                diff_table = self.generate_diff_table(list1, list2, f1, f2)
                
                results.append({
                    "new_ref": new_ref,
                    "old_ref": old_ref,
                    "diff_content": diff_table
                })
            else:
                if not old_fscfai:
                    print(f"DEBUG: Missing FSCFAI for NEW ref: {new_ref}")
                if not new_fscfai:
                    print(f"DEBUG: Missing FSCFAI for OLD ref: {old_ref}")
        
        print(f"DEBUG: Total results generated: {len(results)}")
        return results
            
    def generate_diff_table(self, list1, list2, f1, f2):
        differ = difflib.HtmlDiff(tabsize=2)
        # We only need the table part, not the whole HTML document
        return differ.make_table(
            list1,
            list2,
            fromdesc=f"OLD: ({f1})",
            todesc=f"NEW: ({f2})",
            context=True,
            numlines=3
        )

    def match(self, list1, list2):#pop out matched value
        f1, list1_content = next(iter(list1.items()))
        f2, list2_content = next(iter(list2.items()))

        new_lines = [self.normalize_line(l) for l in list1_content]
        old_lines = [self.normalize_line(l) for l in list2_content]

        tmp = []

        for i, item in enumerate(new_lines):
            elems = item.split("  ")
            found = False
            for j, item2 in enumerate(old_lines):
                elems2 = item2.split("  ")
                if len(elems) > 0 and len(elems2) > 0 and elems[0] == elems2[0]:
                    tmp.append(item2)
                    found = True
                    break
            if not found:
                for j, item2 in enumerate(old_lines):
                    elems2 = item2.split("  ")
                    if len(elems) > 5 and len(elems2) > 5 and elems[5] == elems2[5] and elems[-1] == elems2[-1]:
                        tmp.append(item2)
                        break
        return new_lines, tmp, f1, f2

    def match_with_fuzz(self, list1, list2):
        f1, list1_content = next(iter(list1.items()))
        f2, list2_content = next(iter(list2.items()))

        new_lines = [self.normalize_line(l) for l in list1_content]
        old_lines = [self.normalize_line(l) for l in list2_content]

        tmp = []

        for i, item in enumerate(new_lines):
            score = process.extractOne(item, old_lines, score_cutoff=80)
            if score:
                old_lines.pop(old_lines.index(score[0]))
                tmp.append(score[0])
        return new_lines, tmp, f1, f2