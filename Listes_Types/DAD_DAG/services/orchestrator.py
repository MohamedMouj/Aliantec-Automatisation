import os
import zipfile as zf
from django.conf import settings
from pathlib import Path
from ..helpers.data import SharedData
from ..helpers.file_system import file_system_manipulation
from ..helpers.xml_parser import xml_parser
from ..helpers.excel_parser import excel
from ..helpers.ref_processor import RefProcessor

class Orchestrator:
    def __init__(self, pta_full_path, zip_path, extract_dir, fscfai_data=None, parse_right=False, list_type='dad_dag'):
        self.pta_full_path = pta_full_path
        self.zip_path = zip_path
        self.extract_dir = extract_dir
        self.context = SharedData()
        self.context.fscfai_files = fscfai_data
        self.parse_right = parse_right
        self.list_type = list_type
        
        # The TEMP_DIR is the parent of the extract_dir (the session folder)
        self.TEMP_DIR = os.path.abspath(str(Path(extract_dir).parent))
        if os.name == 'nt' and not self.TEMP_DIR.startswith('\\\\?\\'):
            self.TEMP_DIR = '\\\\?\\' + self.TEMP_DIR

    def detect_new_ref(self):
        to_add_data = []
        if not self.context.fscfai_files:
            return to_add_data
        items = reversed(list(self.context.fscfai_files.items())) if self.parse_right else self.context.fscfai_files.items()
        for ref, file_name in items:
            if ref not in self.context.all_xml_references:
                to_add_data.append({
                    "file_found": file_name,
                    "ref": ref,
                    "action": "To Add",
                })
        return to_add_data

    def process_all(self):
        excel_helper = None
        try:
            fs_helper = file_system_manipulation(self.extract_dir, self.context)
            fs_helper.scan_zip(self.zip_path, self.extract_dir)
            
            if not self.context.xml_files:
                return None, f"Aucun fichier .list trouvé dans le ZIP fourni."

            parsed_xmls = []
            xml_list = self.context.xml_files
            for xml_path in xml_list:
                if xml_path.split('/')[-1].split('_')[1].startswith('D'):
                    continue
                temp_xml = xml_parser(xml_path, self.context)
                temp_xml.parse_xml()
                refs = {r["ref"] for r in temp_xml.get_references()}
                
                xml_name = os.path.basename(xml_path)
                self.context.references_by_xml[xml_name] = refs
                self.context.all_xml_references.update(refs)
                parsed_xmls.append(temp_xml)
                
            excel_helper = excel(self.pta_full_path, self.context)
            excel_helper.load()
            excel_helper.build_refs_desc_mapping()

            all_grid_data = []
            total_summary = {"total": 0, "matches": 0, "updates": 0, "deletes": 0, "new_in_excel": 0}
            all_output_paths = []
            
            xml_to_process = parsed_xmls
            for temp_xml in xml_to_process:
                processor = RefProcessor(excel_helper, temp_xml, fs_helper)
                grid_data, summary, output_path = processor.run()

                all_grid_data.extend(grid_data)

                total_summary["total"] += summary.get("total", 0)
                total_summary["matches"] += summary.get("matches", 0)
                total_summary["updates"] += summary.get("updates", 0)
                total_summary["deletes"] += summary.get("deletes", 0)
                total_summary["new_in_excel"] += summary.get("new_in_excel", 0)
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
                "total_summary": total_summary,
                "download_name": download_name
            }
            return results, None
            
        finally:
            if excel_helper:
                excel_helper.close()
