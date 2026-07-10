from rapidfuzz import process, fuzz
from .FSCF import fscf_processing

class RefProcessor:
    def __init__(self, xml_obj, fs_obj):
        self.xml_obj = xml_obj
        self.fs_obj = fs_obj
        self.fscf_process = fscf_processing(self.fs_obj)
        self.xml_path = self.xml_obj.xml_file_name
        self.unsured_refs = []   # Changed: list of dicts to track xml_path per entry
        self.sured_ref = {}

    def _score_candidate(self, current_description, candidate_description):
        if not current_description or not candidate_description:
            return 0

        current_text = " ".join(str(current_description).upper().split())
        candidate_text = " ".join(str(candidate_description).upper().split())
        if not current_text or not candidate_text:
            return 0

        return round(fuzz.ratio(current_text, candidate_text), 1)

    def run(self):
        current_references_data = self.xml_obj.get_references()
        existing_refs = [item["ref"] for item in current_references_data]

        for ref_data in current_references_data:
            current_ref = ref_data["ref"]
            old_xml_path = ref_data["old_val"]

            if old_xml_path\
            and ((('DAG' in old_xml_path.upper()) and not('DAD' in old_xml_path.upper())) \
            or ('50-PB' in old_xml_path or '60-PA' in old_xml_path or '62-PRG' in old_xml_path or '67-PRD' in old_xml_path) \
            or ('LHD' in old_xml_path.upper())):
                refs_candidates = self.fscf_process.start(old_xml_path, existing_refs=existing_refs)
                if refs_candidates is None:
                    continue

                # if len(refs) == 1:
                #     chosen_ref = next(iter(refs))
                #     self.sured_ref[current_ref] = chosen_ref
                #     self.fs_obj.context.auto_updates.append({
                #         "xml_path": self.xml_obj.xml_file_name,
                #         "current_ref": current_ref,
                #         "new_ref": chosen_ref,
                #         "old_xml_path": old_xml_path,
                #     })
                # Deduplicate by current_ref across all XML files.
                if current_ref not in self.fs_obj.context.unsured_refs:
                    self.fs_obj.context.unsured_refs[current_ref] = {
                        'candidates': refs_candidates,
                        'xml_paths': set()
                    }
                self.fs_obj.context.unsured_refs[current_ref]['xml_paths'].add(self.xml_path)

        # self.fs_obj.context.sured_ref = self.sured_ref

        return True