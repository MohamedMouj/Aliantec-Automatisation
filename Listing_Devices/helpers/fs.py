from pathlib import Path
import re 
import os

class FsHelper:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.fscfai_files=list(Path(self.folder_path).rglob("*.fscfai"))

    def find_fscfai_files(self):
        data_list = dict()
        for f in self.fscfai_files:
            if not f.is_file():
                continue
            fuseaux=f.parent.name
            aux = False
            is_special = True
            # # Fix for Windows Long Paths
            abs_path = str(f.absolute())
            if os.name == 'nt' and not abs_path.startswith('\\\\?\\'):
                abs_path = '\\\\?\\' + abs_path
                
            with open(abs_path, 'r', encoding='utf-8', errors='ignore') as file_content: 
                for line in file_content:
                    if not line.strip():
                        continue
                    if aux:
                        first_char = line[0]
                        is_special = first_char in ['=', '+', '*', '-', '/', '@', '#', '%', '&', '^', '<', '>', '!', '?']
                    else:
                        if line.startswith("============================================================="):
                            is_special = False
                            aux = True
                            continue
                    # if (line.startswith("                 ") or line.strip().startswith('*')) and data_list.get(f.name):
                    #     data_list[f.name][-1] += "\n" + line.strip()
                    #     continue
                        
                    if is_special and aux:
                        break
                        
                    if not is_special:
                        if f.name not in data_list:
                            data_list[f.name] = [fuseaux]
                        data_list[f.name].append(line.strip())
                        
                        
        return data_list if data_list else None

   
