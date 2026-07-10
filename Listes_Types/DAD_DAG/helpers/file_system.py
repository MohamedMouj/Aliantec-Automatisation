from pathlib import Path
import re
import os
import zipfile

class file_system_manipulation():  
    def __init__(self, folder_path, context):
        self.folder_path = folder_path
        self.context = context

    def scan_folder(self):
        xml_files = []
        path = Path(self.folder_path)
        
        for file in path.rglob("*"):
            if not file.is_file():
                continue
                
            ext = file.suffix.lower()
            if ext == ".list":
                xml_files.append(str(file.absolute()))
            elif ext == ".fscfai":
                match = re.search(r"(\d{10})", file.name)
                if match:
                    ref = match.group(1)
                    if ref not in self.context.fscfai_files:
                        self.context.fscfai_files.append(file.name)
        
        return xml_files, self.context.fscfai_files

    def scan_zip(self, zip_path, extract_dir):
        os.makedirs(extract_dir, exist_ok=True)
        fscfai_files = []
        extracted_basenames = set()

        with zipfile.ZipFile(zip_path, 'r') as z:
            for member in z.infolist():
                if member.is_dir():
                    continue

                basename = os.path.basename(member.filename)
                if not basename:
                    continue

                ext = os.path.splitext(basename)[1].lower()

                if ext == '.list':
                    if basename not in extracted_basenames:
                        target_path = os.path.join(extract_dir, basename)
                        with z.open(member) as src, open(target_path, 'wb') as dst:
                            dst.write(src.read())
                        self.context.xml_files.append(target_path)
                        extracted_basenames.add(basename)
                elif ext == '.fscfai':
                    match = re.search(r"(\d{10})", basename)
                    if match:  
                        ref = match.group(1)
                        if basename not in fscfai_files:
                            fscfai_files.append(basename)
                    if basename not in extracted_basenames:
                        target_path = os.path.join(extract_dir, basename)
                        with z.open(member) as src, open(target_path, 'wb') as dst:
                            dst.write(src.read())
                        extracted_basenames.add(basename)
        return fscfai_files

    def search_in_folder_for_file_contains_reference(self, reference):
        if not reference:
            return False, None
            
        for fscf in self.context.fscfai_files:
            if reference in fscf:
                return True, fscf
            
        return False, None

    def get_fscf_content(self, fname):
        if not fname:  # BUG FIX: guard against None or empty string passed from get_fn()
            return None
        if len(fname.split('\\'))>1:
            fscfai_file=os.path.join(self.folder_path, fname.split('\\')[1])
        else:
            fscfai_file=os.path.join(self.folder_path, fname)
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
            
                    
             
                fscf_content+=(line.strip())
                    
                    
        return fscf_content if fscf_content else None

    def compare_fscf_content(self, fns: str) -> list[str | None] | None:
        files_content = []
        for i in fns:
            fc = self.get_fscf_content(i)
            if fc is None:
                files_content.append(None)
            else:
               files_content.append(fc)

        return files_content if len(files_content) > 0 else None