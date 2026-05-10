import os
from pathlib import Path
from .excel import ExcelHelper
from .fs import FsHelper
import re

class DevicesProcess:
    def __init__(self, folder_path, output_file="output.xlsx"):
        self.folder_path = folder_path
        self.output_file = output_file
        self.fs_helper = FsHelper(folder_path)
        self.excel_helper = ExcelHelper(self.output_file)

    def normalize_line(self, line):
        tokens=[]
        line=line[-38:].strip()
        token = re.split(r"\s+", line.strip())#len(token[1].strip())==2 and token[1]!="PT"
   
        tokens.append(token[0].strip())
        tokens.append(token[1].strip() if line.find(token[1].strip())<6   else "")
        tokens.append(token[-1].strip())
 
        return tokens#[t for t in tokens if t and t != '\n' and t!='*']
        # tokens=dict()
        # tokens["numero"]=line[0:7].strip()
        # tokens["type_fil"]=line[7:10].strip()
        # tokens["color"]=line[10:15].strip()
        # tokens["section/longeur"]=line[15:27].strip()
        
        # tokens["dest"]=line[27:36].strip()
        # tokens["ref"]=line[36:47].strip()
        # tokens["conn"]=line[47:64].strip()
        # tokens["matiere"]=line[36:47].strip()

        

    def start(self):      
        data = self.fs_helper.find_fscfai_files()
        if not data:
            return False
            
        normalized_data = []
        for filename, lines in data.items():
            for line in lines:
                if line.strip():
                    nor = self.normalize_line(line)
                    if nor:
                        normalized_data.append([filename, nor])
        # c=0
        # for i in normalized_data:
        #     c+=1
        #     if c==45:
        #         break
        #     print(i)
        self.excel_helper.write_data_to_excel(normalized_data)
        return True
