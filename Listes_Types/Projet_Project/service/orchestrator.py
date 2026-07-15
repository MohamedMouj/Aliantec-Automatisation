import os
import zipfile as zf
from django.conf import settings
from pathlib import Path
from ..helpers.data import SharedData
from ..helpers.fs import file_system_manipulation
from ..helpers.xml_parser import xml_parser
from ..helpers.ref_process import RefProcessor

class Orchestrator:
    def __init__(self, extract_dir, zip_path, old_project, new_project):
   
        self.extract_dir = extract_dir
        self.zip_path = zip_path
        self.context = SharedData()
        self.context.old_project = old_project
        self.context.new_project = new_project
        
        # The TEMP_DIR is the parent of the extract_dir (the session folder)
        self.TEMP_DIR = os.path.abspath(str(Path(extract_dir).parent))
        if os.name == 'nt' and not self.TEMP_DIR.startswith('\\\\?\\'):
            self.TEMP_DIR = '\\\\?\\' + self.TEMP_DIR



    def process_all(self):
        try:
            fs_helper = file_system_manipulation(self.extract_dir, self.context)
            self.context.fscfai_files = fs_helper.scan_zip(self.zip_path, self.extract_dir)
            
            if not self.context.xml_files:
                return None, f"Aucun fichier .list trouvé dans le ZIP fourni."

            parsed_xmls = []
            xml_list = self.context.xml_files
            for xml_path in xml_list:
                temp_xml = xml_parser(xml_path, self.context)
                temp_xml.parse_xml()
                refs = {r["ref"] for r in temp_xml.get_references()}
                
                xml_name = os.path.basename(xml_path)
                self.context.references_by_xml[xml_name] = refs
                self.context.all_xml_references.update(refs)
                parsed_xmls.append(temp_xml)
                
            

            all_grid_data = []
            total_summary = {"total": 0, "matches": 0, "updates": 0}
            all_output_paths = []
            
            xml_to_process = parsed_xmls
            for temp_xml in xml_to_process:
                processor = RefProcessor(temp_xml, fs_helper)
                grid_data, summary, output_path = processor.run()

                all_grid_data.extend(grid_data)

                total_summary["total"] += summary.get("total", 0)
                total_summary["matches"] += summary.get("matches", 0)
                total_summary["updates"] += summary.get("updates", 0)
                total_summary["xml_count"] = len(self.context.xml_files)
                if output_path:
                    all_output_paths.append(output_path)

           
            

            download_name = 'N/A'
            if all_output_paths:
                zip_output_name = 'listes_types_v2.zip'
                zip_output_path = os.path.join(self.TEMP_DIR, zip_output_name)
                
                with zf.ZipFile(zip_output_path, 'w', zf.ZIP_DEFLATED) as zout:
                    for path in all_output_paths:
                        zout.write(path, arcname=os.path.basename(path))
                download_name = zip_output_name

           
            results = {
                "all_grid_data": all_grid_data,
                "addition_data": [],
                "deletion_data": [],
                "total_summary": total_summary,
                "download_name": download_name
            }
            return results, None
            
        finally:
            pass
