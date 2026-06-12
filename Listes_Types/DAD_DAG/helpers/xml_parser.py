import lxml.etree as etree
import re
import os
from django.conf import settings
from pathlib import Path
from datetime import date

class xml_parser():
    def __init__(self, xml_file_name, context):
        self.xml_file_name = xml_file_name
        self.context = context
        self.tree = None
        self.root = None
      
    def load_tree(self):
        if self.tree is None:
            # For etree, we need to handle the long path prefix carefully
            file_to_parse = self.xml_file_name
            self.tree = etree.parse(file_to_parse)
            self.root = self.tree.getroot()
            
    def parse_xml(self):
        if self.root is None:
            self.load_tree()
        return self.root

    def get_beamref_tags(self):
        if self.root is None:
            self.load_tree()
        return self.root.findall("./beamref")

    def get_beamfile_tags(self, beamref_tag):
        return beamref_tag.findall("./beamfile")

    def get_references(self):
        if self.root is None:
            self.load_tree()
        references_data = []
        for beamref_tag in self.get_beamref_tags():
            beamfile_tags = self.get_beamfile_tags(beamref_tag)
            for beamfile_tag in beamfile_tags:
                full_path = beamfile_tag.get("ref", "")
                filename = full_path.split("\\")[-1]
                match = re.match(r"^(\d{10})", filename)
                if match:
                    references_data.append({
                        "ref": match.group(1),
                        "old_val": full_path
                    })
        return references_data
    
    def update_reference(self, reference, full_matched_filename):
        if self.root is None:
            self.load_tree()
        updated = False
        new_final_path = ""
        for elem in self.root.iter():
            if 'ref' not in elem.attrib:
                continue
            old_val = elem.attrib['ref']
            if reference in old_val:
                parts = old_val.split('\\')
                if len(parts) > 1:
                    new_final_path = parts[0] + '\\' + full_matched_filename
                else:
                    parent = elem.getparent()
                    prefix = ""
                    if parent is not None and parent.tag == 'beamref':
                        for sibling in parent.findall('./beamfile'):
                            s_ref = sibling.get('ref', '')
                            if '\\' in s_ref:
                                prefix = s_ref.split('\\')[0] + '\\'
                                break
                    new_final_path = prefix + full_matched_filename
                if new_final_path != old_val:
                    elem.set("ref", new_final_path)
                    updated = True
        return updated, new_final_path

    def save_versioned_file(self):
        if self.tree is None:
            return None
        original_basename = os.path.basename(self.xml_file_name)
        # Handle the long path prefix for os.path.basename if it exists
        if original_basename.startswith('\\\\?\\'):
             original_basename = os.path.basename(original_basename[4:])
        clean_basename = re.sub(r'[<>:"/\\|?*]', '_', original_basename)
        indx=clean_basename.find('20')

        filename = clean_basename.replace(clean_basename[indx:indx+4], date.today().strftime("%Y")) + ".list"

        # App-specific temp directory - shortened to 't' and 'v'
        # Path is: Listes_Types / t / session_id / v
        # We derive the session folder from the xml_file_name path
        session_dir = Path(self.xml_file_name).parent.parent
        v2_dir = os.path.abspath(str(session_dir / 'v'))
        
        if os.name == 'nt' and not v2_dir.startswith('\\\\?\\'):
            v2_dir = '\\\\?\\' + v2_dir
        os.makedirs(v2_dir, exist_ok=True)
        
        new_file_path = os.path.join(v2_dir, filename)
        
        # Write using binary mode
        with open(new_file_path, 'wb') as f:
            self.tree.write(f, encoding="utf-8", xml_declaration=True)
        return new_file_path

    def is_ref_exist(self, ref):
        if not ref:
            return False
        xml_basename = os.path.basename(self.xml_file_name)
        if xml_basename in self.context.references_by_xml:
            if ref in self.context.references_by_xml[xml_basename]:
                return True
        self.load_tree()
        for elem in self.root.iter():
            for value in elem.attrib.values():
                if ref in value:
                    return True
        return False

    def delete_node_by_ref(self, ref):
        if not self.is_ref_exist(ref):
            return None
        for elem in self.root.iter():
            if 'ref' not in elem.attrib:
                continue
            old_val = elem.attrib['ref']
            if ref in old_val:
                parent = elem.getparent()
                if parent is not None:
                    parent.remove(elem)