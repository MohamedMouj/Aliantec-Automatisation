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
            c=0
                
            with open(f, 'r', encoding='utf-8', errors='ignore') as file_content:
                content=file_content.read()
                content=content.split("\n")[28:]
                for line in content:
                    if not (line.strip()) :
                        continue


                    if line.startswith("*E"):                        
                        break
                    if line[0] in ['=', '*', '+', '-', '/', '@', '#', '%', '&', '^', '<', '>', '!', '?']:
                        continue
                        
                    # if (line.startswith("                 ") or line.strip().startswith('*')) and data_list.get(f.name):
                    #     data_list[f.name][-1] += "\n" + line.strip()
                    #     continue
                        
                    
                    if f.name not in data_list:
                        data_list[f.name] = [fuseaux]
                    data_list[f.name].append(line.strip())
                        
                        
        return data_list if data_list else None

   
