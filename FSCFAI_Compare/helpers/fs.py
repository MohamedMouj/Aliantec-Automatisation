from pathlib import Path
import re 

class FsHelper:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.fscfai_files=list(Path(self.folder_path).rglob("*.fscfai"))

    def find_fscfai_files(self, ref):
        data_list = dict()
        aux=False
        found=False
        for f in self.fscfai_files:
            if not f.is_file():
                continue
            match = re.search(r"(\d{10})", f.name)
            if match and match.group(1) == ref:
                found=True
                with open(f, 'r') as file_content: 
                    for line in file_content:
                        startwith=line[0] in ['=', '+', '*', '-', '/', '@', '#', '%', '&', '^', '<', '>', '!', '?']

                        if line.strip().startswith('*') and data_list.get(f.name):
                            data_list[f.name][-1] += "\n"+line
                            continue
                        if line and startwith and aux:
                            break
                        if line and not startwith:
                            if f.name not in data_list:
                                data_list[f.name] = []
                            data_list[f.name].append(line)
                            aux=True
        return data_list if data_list else None

    # def load_fscfai(self):
    #     self.fscfai_files = list(Path(self.folder_path).rglob("*.fscfai"))

# fs=FsHelper("C:\\Users\\User\\OneDrive\\Bureau\\P21\\P21\\FSCFAI")
# for line in fs.find_fscfai_files("9646249380"):
#     print(line) 
