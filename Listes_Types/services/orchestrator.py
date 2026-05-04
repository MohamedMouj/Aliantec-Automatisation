import os
import zipfile as zf
from django.conf import settings
from pathlib import Path
from ..helpers.data import SharedData
from ..helpers.file_system import file_system_manipulation
from ..helpers.xml_parser import xml_parser
from ..helpers.excel_parser import excel_parser
from ..helpers.ref_processor import RefProcessor

class Orchestrator:
    def __init__(self, pta_full_path, zip_path, extract_dir, fscfai_data=None):
        self.pta_full_path = pta_full_path
        self.zip_path = zip_path
        self.extract_dir = extract_dir
        self.fscfai_data = fscfai_data
        self.context = SharedData()
        
        # The TEMP_DIR is the parent of the extract_dir (the session folder)
        # We use abspath and ensure it's handled safely
        self.TEMP_DIR = os.path.abspath(str(Path(extract_dir).parent))
        if os.name == 'nt' and not self.TEMP_DIR.startswith('\\\\?\\'):
            self.TEMP_DIR = '\\\\?\\' + self.TEMP_DIR

    def process_all(self):
        excel_helper = None
        try:
            if self.fscfai_data:
                self.context.fscfai_files = self.fscfai_data
            
            fs_helper = file_system_manipulation(self.extract_dir, self.context)
            fs_helper.scan_zip(self.zip_path, self.extract_dir)
            
            if not self.context.xml_files:
                return None, f"Aucun fichier .list trouvé dans le ZIP fourni."

            parsed_xmls = []
            for xml_path in self.context.xml_files:
                temp_xml = xml_parser(xml_path, self.context)
                temp_xml.parse_xml()
                refs = {r["ref"] for r in temp_xml.get_references()}
                
                xml_name = os.path.basename(xml_path)
                self.context.references_by_xml[xml_name] = refs
                self.context.all_xml_references.update(refs)
                parsed_xmls.append(temp_xml)
                
            excel_helper = excel_parser(self.pta_full_path, self.context)
            excel_helper.load_excel()
            excel_helper.build_index()

            all_grid_data = []
            all_to_delete = []
            total_summary = {"total": 0, "matches": 0, "updates": 0, "deletes": 0, "new_in_excel": 0}
            all_output_paths = []
            
            for temp_xml in parsed_xmls:
                processor = RefProcessor(excel_helper, temp_xml, fs_helper, self.context)
                grid_data, to_delete, summary, output_path = processor.run()

                all_grid_data.extend(grid_data)
                all_to_delete.extend(to_delete)

                total_summary["total"] += summary["total"]
                total_summary["matches"] += summary["matches"]
                total_summary["updates"] += summary["updates"]
                total_summary["deletes"] += summary["deletes"]
                total_summary["xml_count"] = len(self.context.xml_files)
                if output_path:
                    all_output_paths.append(output_path)

            if parsed_xmls:
                processor = RefProcessor(excel_helper, parsed_xmls[-1], fs_helper, self.context)
                all_to_add = processor.detect_new_ref()
            else:
                all_to_add = []
            
            total_summary["new_in_excel"] = len(all_to_add)

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
                "all_to_delete": all_to_delete,
                "all_to_add": all_to_add,
                "total_summary": total_summary,
                "download_name": download_name
            }
            return results, None
            
        finally:
            if excel_helper:
                excel_helper.close()
