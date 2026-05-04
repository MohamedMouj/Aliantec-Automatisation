import os

class RefProcessor:
    def __init__(self, excel_obj, xml_obj, fs_obj, context):
        self.excel_obj = excel_obj
        self.xml_obj = xml_obj
        self.fs_obj = fs_obj
        self.context = context
        self.xml_path = self.xml_obj.xml_file_name

    def run(self, progress_callback=None):
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
                "exists_in_excel": "Non",
                "excel_matched_sheet": "-",
                "excel_matched_cell": "-",
                "new_left_reference_found": "-",
                "chosen_reference_for_folder_search": current_ref,
                "left_source_cell": "-",
                "left_distance": "-",
                "raw_left_value": "-",
                "file_found_in_folder": "Non",
                "xml_updated": "Non",
                "old_xml_ref_value": old_xml_path,
                "new_xml_ref_value": old_xml_path,
                "status": "",
                "reason": ""
            }
            
            excel_match_cell = self.excel_obj.search_by_ref(current_ref)
            new_ref_detected = None
            
            if excel_match_cell:
                row["exists_in_excel"] = "Oui"
                row["excel_matched_sheet"] = excel_match_cell.parent.title
                row["excel_matched_cell"] = excel_match_cell.coordinate
                
                if self.excel_obj.is_delete_rule_triggered(excel_match_cell):
                    found_fs, matched_fs = self.fs_obj.search_in_folder_for_file_contains_reference(current_ref)
                    self.xml_obj.delete_node_by_ref(current_ref)
                    to_delete_data.append({
                        "source_xml": os.path.basename(self.xml_path),
                        "file_found": matched_fs if found_fs else "Non",
                        "ref": current_ref,
                        "action": "À Supprimer"
                    })
                    continue

                left_info = self.excel_obj.check_left_neighbors_4_cells_detailed(excel_match_cell)
                new_ref_detected = left_info["new_reference_detected"]
                if new_ref_detected:
                    row["new_left_reference_found"] = new_ref_detected
                    row["chosen_reference_for_folder_search"] = new_ref_detected
                    row["left_source_cell"] = left_info.get("left_neighbor_source_cell", "-")
                    row["left_distance"] = left_info.get("left_neighbor_distance", "-")
                    row["raw_left_value"] = left_info.get("raw_left_neighbor_value", "-")
                   
            else:
                row["status"] = "NON_DANS_EXCEL"
                row["reason"] = "Cette référence n'a pas été trouvée dans le fichier Excel. Elle est conservée sans modification."
                grid_data.append(row)
                continue

            chosen_ref = row["chosen_reference_for_folder_search"]
            found, matched_filename = self.fs_obj.search_in_folder_for_file_contains_reference(chosen_ref)
            
            if found:
                row["file_found_in_folder"] = "Oui"
                match_count += 1
                
                is_updated, new_xml_path = self.xml_obj.update_reference(current_ref, matched_filename)
                row["new_xml_ref_value"] = new_xml_path
                
                if is_updated:
                    row["xml_updated"] = "Oui"
                    update_count += 1
                    if new_ref_detected:
                        row["status"] = "MIS_À_JOUR_AVEC_NOUVELLE_RÉFÉRENCE"
                        row["reason"] = "Nouvelle référence trouvée et fichier FSCFAI correspondant présent."
                    else:
                        row["status"] = "MIS_À_JOUR_RÉF_ACTUELLE"
                        row["reason"] = "Référence actuelle maintenue, fichier FSCFAI mis à jour dans le XML."
                else:
                    row["status"] = "DÉJÀ_À_JOUR"
                    row["reason"] = "Le XML contient déjà le bon chemin vers le fichier FSCFAI."
            else:
                if new_ref_detected:
                    row["status"] = "NOUVELLE_RÉF_SANS_FICHIER"
                    row["reason"] = f"Nouvelle réf {new_ref_detected} proposée mais aucun fichier FSCFAI trouvé."
                else:
                    row["status"] = "FICHIER_NON_TROUVÉ"
                    row["reason"] = f"Aucun fichier FSCFAI trouvé pour {chosen_ref}."
                
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
        for ref in self.context.new_refs:
            if ref in self.context.fscfai_files:
                found_fs, matched_fs = self.fs_obj.search_in_folder_for_file_contains_reference(ref)
                to_add_data.append({
                    "file_found": matched_fs if found_fs else "Non",
                    "ref": ref,
                    "action": "À Ajouter",
                })
        return to_add_data