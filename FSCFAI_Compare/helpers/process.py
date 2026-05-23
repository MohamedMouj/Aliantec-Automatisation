import os
from pathlib import Path
from .excel import ExcelHelper
from .fs import FsHelper
import difflib
import re
from rapidfuzz import process, fuzz

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
        nor_line = line[0:6] + line[9:15] + " " + line[70:74] + line[90:line.find("\n")] 
        ind=line.find("\n")
        
        if ind!=-1 and line[ind:].strip()!="": 
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

            old_fscfai = self.fs_old.find_fscfai_files(old_ref)
            new_fscfai = self.fs_new.find_fscfai_files(new_ref)

            if old_fscfai and new_fscfai:
                list1, list2, f1, f2 = self.match(old_fscfai, new_fscfai)

                self.fs_old.write_to_txt_file(list1, f1)
                self.fs_new.write_to_txt_file(list2, f2)
                
                diff_table = self.generate_diff_table(list1, list2, f1, f2)
                
                results.append({
                    "new_ref": new_ref,
                    "old_ref": old_ref,
                    "diff_content": diff_table
                })
            else:
                if not old_fscfai:

                    pass
                if not new_fscfai:
                    pass
        return results
            
    def generate_diff_table(self, list1, list2, f1, f2):
        import html as html_lib
        html = [
            '<table class="diff" id="difflib_chg_to0__top" cellspacing="0" cellpadding="0" rules="groups">',
            '<colgroup></colgroup> <colgroup></colgroup> <colgroup></colgroup>',
            '<colgroup></colgroup> <colgroup></colgroup> <colgroup></colgroup>',
            '<thead><tr><th class="diff_next"><br /></th><th colspan="2" class="diff_header">%s</th><th class="diff_next"><br /></th><th colspan="2" class="diff_header">%s</th></tr></thead>' % (f"OLD: ({f1})", f"NEW: ({f2})"),
            '<tbody>'
        ]
        
        for i, (old_str, new_str) in enumerate(zip(list1, list2)):
            if old_str == new_str:
                safe_str = html_lib.escape(old_str).replace('\n', '<br>')
                html.append(f'<tr><td class="diff_next"></td><td class="diff_header">{i+1}</td><td nowrap="nowrap" style="white-space: pre; font-family: Consolas, monospace;">{safe_str}</td><td class="diff_next"></td><td class="diff_header">{i+1}</td><td nowrap="nowrap" style="white-space: pre; font-family: Consolas, monospace;">{safe_str}</td></tr>')
            elif "NOT FOUND" in old_str or "NOT FOUND" in new_str:
                old_html = html_lib.escape(old_str).replace('\n', '<br>')
                new_html = html_lib.escape(new_str).replace('\n', '<br>')
                html.append(f'<tr><td class="diff_next"></td><td class="diff_header">{i+1}</td><td nowrap="nowrap" style="white-space: pre; font-family: Consolas, monospace;">{old_html}</td><td class="diff_next"></td><td class="diff_header">{i+1}</td><td nowrap="nowrap" style="white-space: pre; font-family: Consolas, monospace;">{new_html}</td></tr>')
            else:
                sm = difflib.SequenceMatcher(None, old_str, new_str)
                old_html = ""
                new_html = ""
                for tag, i1, i2, j1, j2 in sm.get_opcodes():
                    if tag == 'equal':
                        old_html += html_lib.escape(old_str[i1:i2])
                        new_html += html_lib.escape(new_str[j1:j2])
                    elif tag == 'replace':
                        old_html += f'<span class="diff_chg">{html_lib.escape(old_str[i1:i2])}</span>'
                        new_html += f'<span class="diff_chg">{html_lib.escape(new_str[j1:j2])}</span>'
                    elif tag == 'delete':
                        old_html += f'<span class="diff_sub">{html_lib.escape(old_str[i1:i2])}</span>'
                    elif tag == 'insert':
                        new_html += f'<span class="diff_add">{html_lib.escape(new_str[j1:j2])}</span>'
                
                old_html = old_html.replace('\n', '<br>')
                new_html = new_html.replace('\n', '<br>')
                html.append(f'<tr><td class="diff_next"></td><td class="diff_header">{i+1}</td><td nowrap="nowrap" style="white-space: pre; font-family: Consolas, monospace;">{old_html}</td><td class="diff_next"></td><td class="diff_header">{i+1}</td><td nowrap="nowrap" style="white-space: pre; font-family: Consolas, monospace;">{new_html}</td></tr>')
        html.append('</tbody></table>')
        return '\n'.join(html)

    def match(self, list1, list2):
        f1, list1_content = next(iter(list1.items())) # OLD
        f2, list2_content = next(iter(list2.items())) # NEW

        old_lines = [self.normalize_line(l) for l in list1_content]
        new_lines = [self.normalize_line(l) for l in list2_content]

        tmp_old = []
        tmp_new = []

        unmatched_old_1 = []
        for item in old_lines:
            elems = item.split("  ")
            elems = [i for i in elems if i.strip() != ""]
            if not elems:
                continue
            
            found = False
            
            for item2 in new_lines:
                elems2 = item2.split("  ")
                elems2 = [i for i in elems2 if i.strip() != ""]
                if not elems2: continue

                if len(elems) > 0 and len(elems2) > 0 and elems[0].strip() == elems2[0].strip():
                    tmp_old.append(item)
                    tmp_new.append(item2)
                    new_lines.remove(item2)
                    found = True
                    break
            
            if not found:
                unmatched_old_1.append(item)


        unmatched_old_2 = []
        for item in unmatched_old_1:
            elems = item.split("  ")
            elems = [i for i in elems if i.strip() != ""]
            
            found = False
            for item2 in new_lines:
                elems2 = item2.split("  ")
                elems2 = [i for i in elems2 if i.strip() != ""]
                if not elems2: continue
                
                if (len(elems) > 4 and len(elems2) > 4 and 
                len(elems[0].strip())>=4 and elems[0].strip()[:4] == elems2[0].strip()[:4]):
                    tmp_old.append(item)
                    tmp_new.append(item2)
                    new_lines.remove(item2)
                    found = True
                    break

            if not found:
                unmatched_old_2.append(item)

        test=[]
        for item in unmatched_old_2:
            elems = item.split("  ")
            elems = [i for i in elems if i.strip() != ""]
            
            found = False
            for item2 in new_lines:
                elems2 = item2.split("  ")
                elems2 = [i for i in elems2 if i.strip() != ""]
                if not elems2: continue
                
                if (len(elems) > 4 and len(elems2) > 4 and 
                (len(elems[0].strip())>=3 and elems[0].strip()[:3] == elems2[0].strip()[:3])):
                    tmp_old.append(item)
                    tmp_new.append(item2)
                    new_lines.remove(item2)
                    found = True
                    break
            if not found:
                test.append(item)
        
        unmatched_old_2 = test

        unmatched_old_3 = []
        for item in unmatched_old_2:
            elems = item.split("  ")
            elems = [i for i in elems if i.strip() != ""]
            
            found = False
            for item2 in new_lines:
                elems2 = item2.split("  ")
                elems2 = [i for i in elems2 if i.strip() != ""]
                if not elems2: continue
                
                if (len(elems) > 4 and len(elems2) > 4 and 
                elems[2].strip() == elems2[2].strip() and 
                elems[4].strip() == elems2[4].strip()):
                    tmp_old.append(item)
                    tmp_new.append(item2)
                    new_lines.remove(item2)
                    found = True
                    break

            if not found:
                unmatched_old_3.append(item)

        unmatched_old_4 = []
        for item in unmatched_old_3:
            elems = item.split("  ")
            elems = [i for i in elems if i.strip() != ""]
            
            found = False
            for item2 in new_lines:
                elems2 = item2.split("  ")
                elems2 = [i for i in elems2 if i.strip() != ""]
                if not elems2: continue
                
                if (len(elems) > 5 and len(elems2) > 5 and 
                elems[5].strip() == elems2[5].strip() and 
                elems[-1].strip() == elems2[-1].strip()):
                    tmp_old.append(item)
                    tmp_new.append(item2)
                    new_lines.remove(item2)
                    found = True
                    break
            
            if not found:
                unmatched_old_4.append(item)
        
        test=[]
        for item in unmatched_old_4:
            elems = item.split("  ")
            elems = [i for i in elems if i.strip() != ""]
            
            found = False
            for item2 in new_lines:
                elems2 = item2.split("  ")
                elems2 = [i for i in elems2 if i.strip() != ""]
                if not elems2: continue
                
                if (len(elems) > 5 and len(elems2) > 5 and 
                elems[2].strip() == elems2[5].strip() and 
                elems[4].strip() == elems2[-1].strip()):
                    tmp_old.append(item)
                    tmp_new.append(item2)
                    new_lines.remove(item2)
                    found = True
                    break
            
            if not found:
                test.append(item)
        
        unmatched_old_4 = test

        unmatched_final = []
        for ritem in unmatched_old_4:
            extracted = process.extractOne(ritem, new_lines)
            if extracted and extracted[0] and extracted[0] != "" and extracted[1] >= 85:
                tmp_new.append(extracted[0])
                tmp_old.append(ritem)
                new_lines.remove(extracted[0])
            else:
                unmatched_final.append(ritem)
                
        for item in unmatched_final:
            tmp_old.append(item)
            tmp_new.append("NOT FOUND IN NEW FILE")

        for item2 in new_lines:
            tmp_new.append(item2)
            tmp_old.append("NOT FOUND IN OLD FILE")
        
        old_list, new_list = self.sorting_by_last(tmp_old, tmp_new) 
                
        return old_list, new_list, f1, f2



    def sorting_by_last(self,old_list, new_list):
        zipped_sorted = sorted(zip(old_list, new_list), key=lambda x: x[1][-5:])
        sorted_old, sorted_new = zip(*zipped_sorted)
        return list(sorted_old), list(sorted_new)

    # def extract_parts(self,text):
    #     """
    #     Extract key components from the string.
    #     You can improve this parser depending on your real data.
    #     """
    #     tokens = text.split()

    #     part_5 = tokens[0] if len(tokens) > 0 else ""
        
    #     # Find numeric like 45 (2-digit number)
    #     num_45 = next((t for t in tokens if t.isdigit() and len(t) <= 3), "")
        
    #     # Find BSI-like code (letters + digits)
    #     code = next((t for t in tokens if any(c.isalpha() for c in t) and any(c.isdigit() for c in t)), "")
        
    #     rest = " ".join(tokens)

    #     return part_5, num_45, code, rest


    # def weighted_similarity(self,s1, s2):
    #     p1_1, n1, c1, r1 = self.extract_parts(s1)
    #     p2_1, n2, c2, r2 = self.extract_parts(s2)

    #     # Compute similarities
    #     score_part5 = fuzz.ratio(p1_1, p2_1)
    #     score_num = fuzz.ratio(n1, n2)
    #     score_code = fuzz.ratio(c1, c2)
    #     score_rest = fuzz.token_sort_ratio(r1, r2)

    #     # Weights (tune these based on your use case)
    #     return (
    #         0.4 * score_part5 +   # first 5 chars (most important)
    #         0.2 * score_num +     # number (45)
    #         0.2 * score_code +    # BSI1A
    #         0.2 * score_rest      # rest
    #     )


    # def find_best_matches(self,query, candidates, top_n=5):
    #     scored = [
    #         (candidate, self.weighted_similarity(query, candidate))
    #         for candidate in candidates
    #     ]

    #     scored.sort(key=lambda x: x[1], reverse=True)
    #     return scored[:top_n]


    # def match_with_fuzz(self, list1, list2):
    #     f1, list1_content = next(iter(list1.items()))
    #     f2, list2_content = next(iter(list2.items()))

    #     new_lines = [self.normalize_line(l) for l in list1_content]
    #     old_lines = [self.normalize_line(l) for l in list2_content]

    #     tmp = []

    #     for i, item in enumerate(new_lines):
    #         best_match_str = None
    #         matches = self.find_best_matches(item, old_lines, top_n=1)
    #         if matches and matches[0][1] >= 80:
    #             best_match_str = matches[0][0]
            
    #         if best_match_str:
    #             old_lines.remove(best_match_str)
    #             tmp.append(best_match_str)
    #         else:
    #             tmp.append("NOT FOUND IN OLD FILE")
    #     return new_lines, tmp, f1, f2
