import os

class RefProcessor:
    def __init__(self, excel_obj, xml_obj, fs_obj, context):
        self.excel_obj = excel_obj
        self.xml_obj = xml_obj
        self.fs_obj = fs_obj
        self.context = context
        self.xml_path = self.xml_obj.xml_file_name

    def run(self):
        """
        Executes the full processing logic for ONE XML file.
        """
        current_references_data = self.xml_obj.get_references()
        total_refs = len(current_references_data)
        
        if total_refs == 0:
            return [], [], {"total": 0, "matches": 0, "updates": 0, "deletes": 0}, None

        to_delete_data = []
        grid_data = []
        update_count = 0
        match_count = 0
        
        for i, ref_data in enumerate(current_references_data):
            current_ref = ref_data["ref"]
            old_xml_path = ref_data["old_val"]
            
            row = {
                "source_xml": os.path.basename(self.xml_path),
                "current_xml_reference": current_ref,
                "exists_in_excel": "No",
                "excel_matched_sheet": "-",
                "excel_matched_cell": "-",
                "new_left_reference_found": "-",
                "chosen_reference_for_folder_search": current_ref,
                "left_source_cell": "-",
                "left_distance": "-",
                "raw_left_value": "-",
                "file_found_in_folder": "No",
                "xml_updated": "No",
                "old_xml_ref_value": old_xml_path,
                "new_xml_ref_value": old_xml_path,
                "status": "",
                "reason": ""
            }
            
            excel_match_cell = self.excel_obj.search_by_ref(current_ref)
            new_ref_detected = None
            
            if excel_match_cell:
                row["exists_in_excel"] = "Yes"
                row["excel_matched_sheet"] = excel_match_cell.parent.title
                row["excel_matched_cell"] = excel_match_cell.coordinate
                
                if self.excel_obj.is_delete_rule_triggered(excel_match_cell):
                    found_fs, matched_fs = self.fs_obj.search_in_folder_for_file_contains_reference(current_ref)
                    self.xml_obj.delete_node_by_ref(current_ref)
                    to_delete_data.append({
                        "source_xml": os.path.basename(self.xml_path),
                        "file_found": matched_fs if found_fs else "No",
                        "ref": current_ref,
                        "action": "To Delete"
                    })
                    continue
                #modify here
                left_info = self.excel_obj.check_left_neighbors_4_cells_detailed(excel_match_cell)
                new_ref_detected = left_info["new_reference_detected"]
                if new_ref_detected:
                    row["new_left_reference_found"] = new_ref_detected
                    row["chosen_reference_for_folder_search"] = new_ref_detected if new_ref_detected else current_ref
                    row["left_source_cell"] = left_info.get("left_neighbor_source_cell", "-")
                    row["left_distance"] = left_info.get("left_neighbor_distance", "-")
                    row["raw_left_value"] = left_info.get("raw_left_neighbor_value", "-")
                   
            else:
                row["status"] = "NOT_IN_EXCEL"
                row["reason"] = "This reference was not found in the Excel file. It is kept without modification."
                # grid_data.append(row)
                # continue

            chosen_ref = row["chosen_reference_for_folder_search"]
            found, matched_filename = self.fs_obj.search_in_folder_for_file_contains_reference(chosen_ref)
            
            if found:
                row["file_found_in_folder"] = "Yes"
                match_count += 1
                
                is_updated, new_xml_path = self.xml_obj.update_reference(current_ref, matched_filename)
                row["new_xml_ref_value"] = new_xml_path
                
                if is_updated:
                    row["xml_updated"] = "Yes"
                    update_count += 1
                    if new_ref_detected:
                        row["status"] = "UPDATED_WITH_NEW_REFERENCE"
                        row["reason"] = "New reference found and corresponding FSCFAI file present."
                    else:
                        row["status"] = "UPDATED_CURRENT_REF"
                        row["reason"] = "Current reference maintained, FSCFAI file updated in XML."
                else:
                    row["status"] = "ALREADY_UP_TO_DATE"
                    row["reason"] = "XML already contains the correct path to the FSCFAI file."
            else:
                if new_ref_detected:
                    row["status"] = "NEW_REF_NO_FILE"
                    row["reason"] = f"New ref {new_ref_detected} proposed but no FSCFAI file found."
                else:
                    row["status"] = "FILE_NOT_FOUND"
                    row["reason"] = f"No FSCFAI file found for {chosen_ref}."
                
            grid_data.append(row)
        
        output_path = self.xml_obj.save_versioned_file()
        
        summary = {
            "total": total_refs,
            "matches": match_count,
            "updates": update_count,
            "deletes": len(to_delete_data)
        }
        
        return grid_data, to_delete_data, summary, output_path

    def detect_new_ref(self):
        to_add_data = []
        for ref, file_name in self.context.fscfai_files.items():
            if ref not in self.context.all_xml_references:
                # found_fs, matched_fs = self.fs_obj.search_in_folder_for_file_contains_reference(ref)
                to_add_data.append({
                    "file_found": file_name,
                    "ref": ref,
                    "action": "To Add",
                })
        return to_add_data