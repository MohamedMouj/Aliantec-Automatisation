import os
from pathlib import Path

from ..helpers.data import SharedData
from ..helpers.file_system import file_system_manipulation
from ..helpers.ref_processor import RefProcessor
from ..helpers.xml_parser import xml_parser

class Orchestrator:
    def __init__(self, zip_path, extract_dir):
        self.zip_path = zip_path
        self.extract_dir = extract_dir
        self.context = SharedData()
        
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
            processed_paths = set()
            xml_list = self.context.xml_files
            for xml_path in xml_list:
                if xml_path in processed_paths:
                    continue
                processed_paths.add(xml_path)
                
                temp_xml = xml_parser(xml_path, self.context)
                temp_xml.parse_xml()
                refs = {r["ref"] for r in temp_xml.get_references()}

                xml_name = os.path.basename(xml_path)
                self.context.references_by_xml[xml_name] = refs
                self.context.all_xml_references.update(refs)
                parsed_xmls.append(temp_xml)

           

            for temp_xml in parsed_xmls:
                processor = RefProcessor(temp_xml, fs_helper)
                processor.run()

            results = {
                "unsured_refs": self.context.unsured_refs,
                "summary": {
                    "total": len(self.context.all_xml_references),
                    "xml_count": len(parsed_xmls),
                    "matches": 0,
                    "updates": 0,
                },
            }
            return results, None

        finally:
            pass
