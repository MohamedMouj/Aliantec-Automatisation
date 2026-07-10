from rapidfuzz import process, fuzz
import os
import re
import math

class fscf_processing:
    def __init__(self, fs_obj):
        self.fs_obj = fs_obj
        self.file_content_mapping={}

    def compare_content(self, fns) -> tuple[str, float]:
        f = (
            self.compare_fscf_content(
                list(fns)
            )
        )
        if f is None:
            return (None, 0.0)
        content_to_fn = dict()

        for filename, con in zip(fns, f):
            if con is not None:
                content_to_fn[con] = filename  # BUG FIX: was `fns` (the whole tuple)

        ref_content = f[0]
        candidates = [c for c in f[1:] if c is not None]

        if ref_content is None or not candidates:
            return (None, 0.0)

        top2 = process.extract(ref_content, candidates, scorer=fuzz.partial_ratio, limit=10)

        reviews = []
        # if not math.isclose(top2[0][1], top2[1][1], abs_tol=10):
        #     refs.append(content_to_fn[top2[0][0]])
        # else:
        for i in top2:
            reviews.append((content_to_fn[i[0]], i[1]))

        return (fns[0], reviews)


    def _build_cleaned_list(self, existing_refs: list[str]) -> dict[str, str]:
        return {
            filename
            for filename in self.fs_obj.context.fscfai_files
            if re.search(r"(\d{10})", filename).group(1) not in existing_refs and "DAG" not in filename.upper() and "LHD" not in filename.upper()
        }

    
    def get_fscf_content(self, fname):
        if not fname:  
            return None
        if len(fname.split('\\'))>1:
            fscfai_file=os.path.join(self.fs_obj.folder_path, fname.split('\\')[1])
        else:
            fscfai_file=os.path.join(self.fs_obj.folder_path, fname)
        if not os.path.isfile(fscfai_file):
            return None
                
        fscf_content = ""
        with open(fscfai_file, 'r', encoding='utf-8', errors='ignore') as file_content:
            content=file_content.read()
            content=content.split("\n")[28:]
            for line in content:
                if not (line.strip()) :
                    continue


                if line.startswith("*E"):                        
                    break
                if line[0] in ['=', '*', '+', '-', '/', '@', '#', '%', '&', '^', '<', '>', '!', '?']:
                    continue
            
                    
             
                fscf_content+=(line.split("  ")[-1].strip())
                    
                    
        return fscf_content if fscf_content else None

    def compare_fscf_content(self, fns: str) -> list[str | None] | None:
        # BUG FIX 5: Standardized list naming (files_content vs file_content)
        files_content = []
        for i in fns:
            fc = self.get_fscf_content(i)
            if fc is None:
                files_content.append(None)
            else:
                fc=fc.replace(" ", "")
                files_content.append(fc)

        return files_content if len(files_content) > 0 else None

    def start(self, old_xml_path: str, existing_refs: list[str]) -> str | None:

        self.cleaned_list = self._build_cleaned_list(existing_refs)
        candidates = list(self.cleaned_list)
        old_xml_path=old_xml_path.split('\\')[-1]
        cs="".join(old_xml_path).replace("DAG", "DAD")
        cs = cs.replace("LHD", "RHD")
        extracted = process.extract(
            cs,
            candidates,
            scorer=fuzz.partial_ratio,
            limit=20,
        )
        if not extracted:
            return None

        reviews = []
        for i in extracted:
            reviews.append((i[0], i[1]))

        return (old_xml_path, reviews)
