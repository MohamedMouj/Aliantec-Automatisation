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
        
        self.html_template_start = """<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Comparison Results - {title}</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
            <style>
                :root {
                    --bg-color: #f8fafc;
                    --surface-color: #ffffff;
                    --border-color: #e2e8f0;
                    --text-primary: #1e293b;
                    --text-secondary: #64748b;
                    --add-bg: #dcfce7;
                    --add-text: #166534;
                    --sub-bg: #fee2e2;
                    --sub-text: #991b1b;
                    --chg-bg: #fef08a;
                    --chg-text: #854d0e;
                }
                
                body {
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                    background-color: var(--bg-color);
                    color: var(--text-primary);
                    padding: 2rem;
                    max-width: 1400px;
                    margin: 0 auto;
                }

                .header {
                    margin-bottom: 2rem;
                    text-align: center;
                }

                .header h1 {
                    font-size: 2.25rem;
                    font-weight: 700;
                    color: var(--text-primary);
                    margin-bottom: 0.5rem;
                }

                table.diff {
                    width: 100%;
                    background: var(--surface-color);
                    border-radius: 12px;
                    border-collapse: separate;
                    border-spacing: 0;
                    box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
                    margin-bottom: 3rem;
                    overflow: hidden;
                    border: 1px solid var(--border-color);
                }

                table.diff thead th {
                    background: #f1f5f9;
                    padding: 1.25rem 1rem;
                    font-size: 0.9rem;
                    font-weight: 600;
                    color: var(--text-primary);
                    text-align: left;
                    border-bottom: 1px solid var(--border-color);
                }

                table.diff tbody td {
                    padding: 0.75rem 1rem;
                    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                    font-size: 0.85rem;
                    line-height: 1.6;
                    vertical-align: top;
                    border-bottom: 1px solid #f1f5f9;
                }

                table.diff td[nowrap="nowrap"] {
                    width: 47%;
                    min-width: 47%;
                    max-width: 47%;
                    white-space: pre-wrap !important;
                    word-break: break-word;
                }

                .diff_header {
                    width: 3%;
                    text-align: right !important;
                    color: var(--text-secondary);
                    background: #f8fafc;
                    border-right: 1px solid var(--border-color);
                    padding-right: 0.75rem !important;
                    user-select: none;
                }

                .diff_add { background-color: var(--add-bg); color: var(--add-text); }
                .diff_sub { background-color: var(--sub-bg); color: var(--sub-text); }
                .diff_chg { background-color: var(--chg-bg); color: var(--chg-text); }
                .diff_next { display: none; }
                colgroup { display: none; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>FSCFAI Compare Report</h1>
                <p>Comparison between {old_ref} and {new_ref}</p>
            </div>
        """

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