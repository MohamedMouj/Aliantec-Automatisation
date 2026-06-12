import os

class RefProcessor:
    def __init__(self, excel_obj, xml_obj, fs_obj):
        self.excel_obj = excel_obj
        self.xml_obj = xml_obj
        self.fs_obj = fs_obj
        # self.context = context
        self.xml_path = self.xml_obj.xml_file_name

    def run(self):
        """
        Executes the full processing logic for ONE XML file.
        """
        current_references_data = self.xml_obj.get_references()
        total_refs = len(current_references_data)
        
        # if total_refs == 0:
        #     return [], [], {"total": 0, "matches": 0, "updates": 0, "deletes": }, None

        to_delete_data = []
        grid_data = []
        update_count = 0
        match_count = 0
        
        # Determine iteration order
        # self.excel_obj.load()
        for i, ref_data in enumerate(current_references_data):
            current_ref = ref_data["ref"]
            old_xml_path = ref_data["old_val"]
            
            row = {
                "source_xml": os.path.basename(self.xml_path),
                "current_xml_reference": current_ref,
                "exists_in_excel": "No",
                "excel_matched_sheet": "-",
                "excel_matched_cell": "-",
                "description_in_excel": "-",
                "new_reference_found": "-",
                "chosen_reference_for_folder_search": current_ref,
                "neighbor_source_cell": "-",
                "neighbor_distance": "-",
                "neighbour_description": "-",
                "file_found_in_folder": "No",
                "xml_updated": "No",
                "old_xml_ref_value": old_xml_path,
                "new_xml_ref_value": old_xml_path,
                "status": "",
                "reason": ""
            }
            
            new_ref_detected = None
            chosen_ref = current_ref
            
            excel_match_cell = self.excel_obj.start(current_ref, old_xml_path)
           
            
            if excel_match_cell:
                row["exists_in_excel"] = "Yes"
                row["excel_matched_sheet"] = "r"
                row["excel_matched_cell"] = "r"
                
                # if self.excel_obj.is_delete_rule_triggered(excel_match_cell):
                #     found_fs, matched_fs = self.fs_obj.search_in_folder_for_file_contains_reference(current_ref)
                #     self.xml_obj.delete_node_by_ref(current_ref)
                #     to_delete_data.append({
                #         "source_xml": os.path.basename(self.xml_path),
                #         "file_found": matched_fs if found_fs else "No",
                #         "ref": current_ref,
                #         "action": "To Delete"
                #     })
                #     continue

                if excel_match_cell[0]:
                    row["description_in_excel"] = excel_match_cell[0]
                if excel_match_cell[1]:
                    row["neighbour_description"] = excel_match_cell[1]

                new_ref_detected = excel_match_cell[2]
                if new_ref_detected:
                    row["new_reference_found"] = new_ref_detected
                    row["neighbor_source_cell"]="p"
                    row["chosen_reference_for_folder_search"] = "p"
                    chosen_ref = new_ref_detected
                   
            else:
                row["status"] = "NOT_IN_EXCEL"
                row["reason"] = "This reference was not found in the Excel file. It is kept without modification."

            found=False
            if row["new_reference_found"] != "-":
                chosen_ref = row["new_reference_found"]
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
        
        return grid_data, summary, output_path