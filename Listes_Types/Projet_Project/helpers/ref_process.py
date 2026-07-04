import os
import re
import math
from rapidfuzz import process, fuzz


# Threshold constants
SCORE_MIN          = 50   # minimum acceptable fuzzy score
SCORE_HIGH         = 80   # score above which a single top match is trusted
SCORE_CLOSE_TOL    = 5    # absolute tolerance for "too-close" top-two scores
CONTENT_MATCH_MIN  = 70   # minimum content-similarity score to accept a result
TOP_CANDIDATES     = 9 # number of candidates fed to compare_content


class RefProcessor:
    def __init__(self, xml_obj, fs_obj):
        
        self.xml_obj   = xml_obj
        self.fs_obj    = fs_obj
        self.xml_path  = xml_obj.xml_file_name
        self.old_project=self.fs_obj.context.old_project
        self.new_project=self.fs_obj.context.new_project
        # populated in run(); declared here for clarity
        self.cleaned_list: dict[str, str] = {}  # description → full filename

    def _build_cleaned_list(self, existing_refs: list[str]) -> dict[str, str]:
        return {
            filename: filename
            for filename, ref in self.fs_obj.context.fscfai_files.items()
            if ref not in existing_refs and self.old_project not in filename.upper()
        }

    def get_fn(self, desc: str) -> str | None:
        desc_upper = desc.upper()
        for d, f in self.cleaned_list.items():
            if d.upper() == desc_upper:
                return f
        return None

    def _make_row(self, old_xml_path: str, current_ref: str) -> dict:
        return {
            "source_xml":                      os.path.basename(self.xml_path),
            "current_xml_reference":           current_ref,
            "new_reference_found":             "-",
            "chosen_reference_for_folder_search": current_ref,
            "file_found_in_folder":            "No",
            "xml_updated":                     "No",
            "old_xml_ref_value":               old_xml_path,
            "new_xml_ref_value":               old_xml_path,
            "percentage_of_matching":          "-",
            "status":                          "",
            "reason":                          "",
        }

    # ------------------------------------------------------------------
    # Content-based tie-breaking
    # ------------------------------------------------------------------

    def compare_content(
        self,
        *fns
    ) -> tuple[str, float]:
        f = (
            self.fs_obj.compare_fscf_content(
                list(fns)
            )
        )
        if f is None:
            return (None, 0.0)
        content_to_fn = dict()

        for filename, con in zip(fns, f):
            if con is not None:
                content_to_fn[con] = filename  # BUG FIX: was `fns` (the whole tuple)

        # f[0] is the reference content (old_xml_path's content); f[1:] are the candidates
        ref_content = f[0]
        candidates = [c for c in f[1:] if c is not None]

        if ref_content is None or not candidates:
            return (None, 0.0)

        top2 = process.extract(ref_content, candidates, scorer=fuzz.ratio, limit=2)

        if top2 and top2[0][1] >= CONTENT_MATCH_MIN:
            best_content  = top2[0][0]
            best_score    = top2[0][1]
            # BUG FIX: content_to_fn now maps content->filename (string), not->fns (tuple)
            best_filename = content_to_fn.get(best_content, fns[1] if len(fns) > 1 else fns[0])
        else:
            # No confident content match; keep the original reference (first filename arg)
            best_filename = fns[0]
            best_score    = 0.0

        return (best_filename, float(best_score))

    def _resolve(self, old_xml_path: str, row: dict) -> str | None:
        candidates = list(self.cleaned_list.keys())
        cs="".join(old_xml_path.split("_")[-3:]).replace(self.old_project, self.new_project)
        extracted = process.extract(
            cs,
            candidates,
            scorer=fuzz.ratio,
            limit=TOP_CANDIDATES,
        )
        # extracted=[i for i in extracted if i[0][:3] == cs[:3]]
        if not extracted:
            row["status"] = "NO_MATCH"
            row["reason"] = "No candidates returned by search."
            return None

        top_score = extracted[0][1]

        # Below minimum — or FSCF content unavailable
        if top_score < SCORE_MIN or self.fs_obj.get_fscf_content(self.get_fn(extracted[0][0])) is None:
            row["status"] = "NO_MATCH"
            row["reason"] = "Score below 75% or FSCF content unavailable."
            return None

       

        # if top_score > SCORE_HIGH and (len(extracted) < 2 or not math.isclose(extracted[0][1], extracted[1][1], abs_tol=SCORE_CLOSE_TOL)):
        #     # Clear single winner
        #     new_ref = extracted[0][0]
        #     row["new_xml_ref_value"]      = self.cleaned_list[new_ref]
        #     row["percentage_of_matching"] = f"{top_score:.2f}%"
        #     row["new_reference_found"]    = new_ref

        else: 
            
            filenames = [self.cleaned_list.get(e[0], e[0]) for e in extracted]
            result = self.compare_content(old_xml_path.split("\\")[-1], *filenames)

            best_fn, best_score = result if result is not None else (None, 0.0)

            if best_fn is not None and best_score > SCORE_HIGH:
                row["new_xml_ref_value"]      = best_fn
                row["percentage_of_matching"] = f"{best_score:.2f}%"
                row["new_reference_found"]    = best_fn
                new_ref = best_fn

            else:
                row["status"] = "NO_MATCH"
                row["reason"] = "No FSCFAI Content match."
                return None

        return row["new_xml_ref_value"]

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self) -> tuple[list[dict], dict, str]:
        current_references_data = self.xml_obj.get_references()
        total_refs   = len(current_references_data)
        existing_refs = [item["old_val"] for item in current_references_data]

        self.cleaned_list = self._build_cleaned_list(existing_refs)

        grid_data    = []
        update_count = 0
        match_count  = 0

        for ref_data in current_references_data:
            current_ref  = ref_data["ref"]
            old_xml_path = ref_data["old_val"]

            row = self._make_row(old_xml_path, current_ref)

            if self.old_project not in old_xml_path.upper():
                grid_data.append(row)
                continue

            new_ref_detected = self._resolve(old_xml_path, row)

            if row["status"] == "NO_MATCH":
                grid_data.append(row)
                continue

            # Determine the reference string used for the folder search
            chosen_ref = new_ref_detected or current_ref
            match = re.search(r"(\d{10})", chosen_ref)
            if match:
                chosen_ref = match.group(1)

            row["chosen_reference_for_folder_search"] = chosen_ref

            # ── Folder search ────────────────────────────────────────────
            found, matched_filename = self.fs_obj.search_in_folder_for_file_contains_reference(chosen_ref)
            matched_filename=new_ref_detected
            if found:
                row["file_found_in_folder"] = "Yes"
                match_count += 1

                is_updated, new_xml_path = self.xml_obj.update_reference(current_ref, matched_filename)
                row["new_xml_ref_value"] = new_xml_path

                if is_updated:
                    row["xml_updated"] = "Yes"
                    update_count += 1
                    if new_ref_detected:
                        row["status"] = "UPDATED_NEW_REF"
                        row["reason"] = f"Replaced by matched file ({row['percentage_of_matching']})."
                    else:
                        row["status"] = "UPDATED_CURRENT_REF"
                        row["reason"] = "Current reference maintained; FSCFAI file updated in XML."
                else:
                    row["status"] = "ALREADY_UP_TO_DATE"
                    row["reason"] = "XML already contains the correct path to the FSCFAI file."
            else:
                if new_ref_detected:
                    row["status"] = "NEW_REF_NO_FILE"
                    row["reason"] = f"New ref '{new_ref_detected}' proposed but no FSCFAI file found."
                else:
                    row["status"] = "FILE_NOT_FOUND"
                    row["reason"] = f"No FSCFAI file found for reference '{chosen_ref}'."

            grid_data.append(row)

        output_path = self.xml_obj.save_versioned_file()

        summary = {
            "total":   total_refs,
            "matches": match_count,
            "updates": update_count,
        }

        return grid_data, summary, output_path