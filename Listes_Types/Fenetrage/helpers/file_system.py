from pathlib import Path
import re
import os
import zipfile

class file_system_manipulation():  
    def __init__(self, folder_path, context):
        self.folder_path = folder_path
        self.context = context

    def scan_folder(self):
        """
        Scans the folder once and separates XML and FSCFAI files.
        Populates the cache for FSCFAI files.
        """
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
                        self.context.fscfai_files[ref] = file.name
        
        return xml_files, self.context.fscfai_files

    def scan_zip(self, zip_path, extract_dir):
        """
        Reads a ZIP file without extracting .fscfai files to disk.
        """
        os.makedirs(extract_dir, exist_ok=True)
        list_counter = 0

        with zipfile.ZipFile(zip_path, 'r') as z:
            for member in z.infolist():
                if member.is_dir():
                    continue

                basename = os.path.basename(member.filename)
                if not basename:
                    continue

                ext = os.path.splitext(basename)[1].lower()

                if ext == '.list':
                    list_counter += 1
                    target_path = os.path.join(extract_dir, basename)
                    with z.open(member) as src, open(target_path, 'wb') as dst:
                        dst.write(src.read())
                    self.context.xml_files.append(target_path)

    def search_in_folder_for_file_contains_reference(self, reference):
        """
        Search folder for a file containing the reference.
        Uses the context cache exclusively for O(1) lookups.
        """
        if not reference:
            return False, None
            
        if reference in self.context.fscfai_files:
            return True, self.context.fscfai_files[reference]
            
        return False, None
