import os
from pathlib import Path
from .excel import ExcelHelper
from .fs import FsHelper
import difflib
import re

class CompareProcess:
    def __init__(self, excel_file, folder_path, output_dir=None):
        self.excel_file = excel_file
        self.folder_path = folder_path
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.excel_helper = ExcelHelper(excel_file)
        self.fs_helper = FsHelper(folder_path)

    def close(self):
        if hasattr(self, 'excel_helper'):
            self.excel_helper.close()
        

    def normalize_line(self, line):
        tokens = re.split(r"\s\s+", line)
        return "  ".join(tokens)

    def start(self):
        all_refs_couples = self.excel_helper.get_all_ref_couples()
        results = []
        
        
        for data in all_refs_couples:
            old_ref = data.get("OLD")
            new_ref = data.get("NEW")
            
            if not old_ref or not new_ref:
                continue

            old_fscfai = self.fs_helper.find_fscfai_files(old_ref)
            new_fscfai = self.fs_helper.find_fscfai_files(new_ref)

            if old_fscfai and new_fscfai:
                print(f"DEBUG: Match found for {old_ref} vs {new_ref}")
                list1, list2, f1, f2 = self.match(old_fscfai, new_fscfai)
                diff_table = self.generate_diff_table(list1, list2, f1, f2)
                
                results.append({
                    "old_ref": old_ref,
                    "new_ref": new_ref,
                    "diff_content": diff_table
                })
            else:
                if not old_fscfai:
                    print(f"DEBUG: Missing FSCFAI for OLD ref: {old_ref}")
                if not new_fscfai:
                    print(f"DEBUG: Missing FSCFAI for NEW ref: {new_ref}")
        
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

    def match(self, list1, list2):
        f1, list1_content = next(iter(list1.items()))
        f2, list2_content = next(iter(list2.items()))

        old_lines = [self.normalize_line(l) for l in list1_content]
        new_lines = [self.normalize_line(l) for l in list2_content]

        tmp = []

        for i, item in enumerate(old_lines):
            elems = item.split("  ")
            found = False
            for j, item2 in enumerate(new_lines):
                elems2 = item2.split("  ")
                if len(elems) > 0 and len(elems2) > 0 and elems[0] == elems2[0]:
                    tmp.append(item2)
                    found = True
                    break
            if not found:
                for j, item2 in enumerate(new_lines):
                    elems2 = item2.split("  ")
                    if len(elems) > 5 and len(elems2) > 5 and elems[5] == elems2[5] and elems[-1] == elems2[-1]:
                        tmp.append(item2)
                        break
        return old_lines, tmp, f1, f2