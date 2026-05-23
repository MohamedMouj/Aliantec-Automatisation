from pathlib import Path
import re 

class FsHelper:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.fscfai_files=list(Path(self.folder_path).rglob("*.fscfai"))

    def find_fscfai_files(self, ref):
        data_list = dict()
        
        for f in self.fscfai_files:
            if not f.is_file():
                continue
            match = re.search(r"(\d{10})", f.name)
            if match and match.group(1) == ref:
                with open(f, 'r') as file_content: 
                    for line in file_content:
                        if not (line.strip()) : continue
                        if line.startswith("*E"): break
                        if line[0] in ['=', '+', '*', '-', '/', '@', '#', '%', '&', '^', '<', '>', '!', '?']: continue

                        if line.strip().startswith('*') and data_list.get(f.name):
                            data_list[f.name][-1] += "\n"+line
                            continue

                        if line:
                            if f.name not in data_list:
                                data_list[f.name] = []
                            data_list[f.name].append(line)
                            
        return data_list if data_list else None

    def write_to_txt_file(self, list_data, filename):
        output_dir = Path(self.folder_path).parent.parent / "output"
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / filename

        # Clean the lines: keep only actual lines, completely removing "NOT FOUND" placeholders
        cleaned_lines = [line.strip() for line in list_data if "NOT FOUND" not in line]

        with open(str(output_file), "w", encoding='utf-8') as file_content: 
            file_content.write("\n".join(cleaned_lines))
            
        print(output_file)
        


    # def load_fscfai(self):
    #     self.fscfai_files = list(Path(self.folder_path).rglob("*.fscfai"))

# fs=FsHelper("C:\\Users\\User\\OneDrive\\Bureau\\P21\\P21\\FSCFAI")
# for line in fs.find_fscfai_files("9646249380"):
#     print(line) 
