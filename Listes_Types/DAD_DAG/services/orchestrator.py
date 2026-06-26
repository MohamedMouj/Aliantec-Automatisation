"""
services/orchestrator.py  (MODIFIED – audit workflow added)
------------------------------------------------------------
Drop-in replacement for the original orchestrator.

What changed vs the original
─────────────────────────────
1.  process_all() no longer re-zips immediately.
    Instead it returns an AuditManifest when low-confidence matches exist,
    leaving modified .list files in the 'v/' sub-directory as a draft state.

2.  A new finalize() method reads the manifest, applies user choices via
    xml_parser.update_reference(), re-saves the touched XML files, then
    packages everything into the output ZIP.

3.  The existing RefProcessor is called unchanged.  Fuzzy-score exposure
    is handled by a thin wrapper around excel.find_matched_desc() inside
    _run_with_audit() – the internal logic of excel_parser is untouched.

4.  No database calls anywhere.
"""

from __future__ import annotations

import os
import zipfile as zf
from pathlib import Path

from django.conf import settings

from ..helpers.data import SharedData
from ..helpers.file_system import file_system_manipulation
from ..helpers.xml_parser import xml_parser
from ..helpers.excel_parser import excel
from ..helpers.ref_processor import RefProcessor
from ..helpers.audit_manifest import (
    AuditManifest,
    AUDIT_THRESHOLD,
    NEEDS_REVIEW,
)


class Orchestrator:
    """
    Identical constructor signature as the original – no calling-code changes
    are required in views.py for the first-pass call.
    """

    def __init__(
        self,
        pta_full_path,
        zip_path,
        extract_dir,
        fscfai_data=None,
        parse_right=False,
        list_type="dad_dag",
    ):
        self.pta_full_path = pta_full_path
        self.zip_path = zip_path
        self.extract_dir = extract_dir
        self.context = SharedData()
        self.context.fscfai_files = fscfai_data or {}
        self.parse_right = parse_right
        self.list_type = list_type

        # TEMP_DIR = parent of extract_dir = session root
        self.TEMP_DIR = os.path.abspath(str(Path(extract_dir).parent))
        if os.name == "nt" and not self.TEMP_DIR.startswith("\\\\?\\"):
            self.TEMP_DIR = "\\\\?\\" + self.TEMP_DIR

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────────────────────────

    def process_all(self):
        """
        Phase 1 – automated processing pass.

        Returns
        -------
        (results, error, manifest_or_None)

        manifest_or_None is an AuditManifest when ≥1 low-confidence match was
        flagged; None when everything passed the threshold automatically.

        The caller (views.index) checks manifest_or_None to decide whether to
        render the review form or the final results table.
        """
        excel_helper = None
        try:
            # ── Scan ZIP and extract .list files ─────────────────────────────
            fs_helper = file_system_manipulation(self.extract_dir, self.context)
            fs_helper.scan_zip(self.zip_path, self.extract_dir)

            if not self.context.xml_files:
                return None, "Aucun fichier .list trouvé dans le ZIP fourni.", None

            # ── Parse all XML files ───────────────────────────────────────────
            parsed_xmls = []
            for xml_path in self.context.xml_files:
                if xml_path.split("/")[-1].split("_")[1].startswith("D"):
                    continue
                temp_xml = xml_parser(xml_path, self.context)
                temp_xml.parse_xml()
                refs = {r["ref"] for r in temp_xml.get_references()}
                xml_name = os.path.basename(xml_path)
                self.context.references_by_xml[xml_name] = refs
                self.context.all_xml_references.update(refs)
                parsed_xmls.append(temp_xml)

            # ── Load Excel ────────────────────────────────────────────────────
            excel_helper = excel(self.pta_full_path, self.context)
            excel_helper.load()
            excel_helper.build_refs_desc_mapping()

            # ── Prepare manifest (written to session root) ─────────────────
            output_zip_path = os.path.join(self.TEMP_DIR, "listes_types_v2.zip")
            manifest = AuditManifest.create_new(
                session_dir=self.TEMP_DIR,
                session_id=os.path.basename(self.TEMP_DIR),
                pending_dir=self.extract_dir,
                output_zip_path=output_zip_path,
            )

            # ── Run per-XML processing with audit interception ─────────────
            all_grid_data = []
            total_summary = {
                "total": 0, "matches": 0,
                "updates": 0, "deletes": 0, "new_in_excel": 0,
            }
            all_output_paths = []

            for temp_xml in parsed_xmls:
                grid_data, summary, output_path, flagged = self._run_with_audit(
                    excel_helper, temp_xml, fs_helper, manifest
                )
                all_grid_data.extend(grid_data)
                total_summary["total"]      += summary.get("total", 0)
                total_summary["matches"]    += summary.get("matches", 0)
                total_summary["updates"]    += summary.get("updates", 0)
                total_summary["deletes"]    += summary.get("deletes", 0)
                total_summary["xml_count"]   = len(self.context.xml_files)
                if output_path:
                    all_output_paths.append(output_path)

            # ── Persist draft output paths in manifest ─────────────────────
            manifest._data["draft_output_paths"] = all_output_paths
            manifest._data["all_grid_data"] = all_grid_data
            manifest._data["total_summary"] = total_summary
            manifest.save()

            # ── Branch: review needed vs. can finalize immediately ─────────
            if manifest.needs_review:
                # Return without zipping; view will render the review form.
                results = {
                    "all_grid_data": all_grid_data,
                    "total_summary": total_summary,
                    "download_name": "N/A",
                    "addition_data": [],
                    "deletion_data": [],
                }
                return results, None, manifest

            # No flags – finalize in one shot (same behaviour as original).
            download_name = self._package_zip(all_output_paths)
            manifest.mark_finalized()
            manifest.save()

            results = {
                "all_grid_data": all_grid_data,
                "total_summary": total_summary,
                "download_name": download_name,
                "addition_data": [],
                "deletion_data": [],
            }
            return results, None, None

        finally:
            if excel_helper:
                excel_helper.close()

    def finalize(self, manifest: AuditManifest):
        """
        Phase 2 – apply user choices and produce the final ZIP.

        Called by views.finalize_review() after the user submits the audit
        form.  Reads the draft .list files that xml_parser already wrote in
        the 'v/' sub-directory, patches only the flagged references that the
        user overrode, re-saves those files, then re-zips everything.

        Returns
        -------
        (results, error)
        """
        try:
            items_by_xml = manifest.items_by_xml()
            draft_paths: list[str] = manifest._data.get("draft_output_paths", [])

            patched_paths = []
            for draft_path in draft_paths:
                xml_name = os.path.basename(draft_path)
                pending_items = items_by_xml.get(xml_name, [])

                if pending_items:
                    # Re-open the already-saved draft file and apply overrides.
                    temp_xml = xml_parser(draft_path, self.context)
                    temp_xml.parse_xml()

                    for item in pending_items:
                        chosen = item["user_choice"]
                        if chosen == NEEDS_REVIEW:
                            # User skipped → keep automated_choice
                            chosen = item["automated_choice"]

                        # Resolve chosen ref → FSCFAI filename via fs context
                        fscfai_filename = self.context.fscfai_files.get(chosen)
                        if fscfai_filename:
                            temp_xml.update_reference(
                                item["current_ref"], fscfai_filename
                            )

                    # Overwrite the draft file in-place (save_versioned_file
                    # produces a new path in the same 'v/' directory; we use
                    # the returned path so the zip picks it up correctly).
                    saved_path = temp_xml.save_versioned_file()
                    patched_paths.append(saved_path or draft_path)
                else:
                    # No audit items for this file – use draft as-is.
                    patched_paths.append(draft_path)

            download_name = self._package_zip(patched_paths)
            manifest.mark_finalized()
            manifest.save()

            results = {
                "all_grid_data": manifest._data.get("all_grid_data", []),
                "total_summary": manifest._data.get("total_summary", {}),
                "download_name": download_name,
                "addition_data": [],
                "deletion_data": [],
            }
            return results, None

        except Exception as exc:  # noqa: BLE001
            manifest.mark_error(str(exc))
            manifest.save()
            return None, str(exc)

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _run_with_audit(
        self,
        excel_helper: excel,
        temp_xml: xml_parser,
        fs_helper: file_system_manipulation,
        manifest: AuditManifest,
    ):
        """
        Thin wrapper around RefProcessor.run() that intercepts the
        find_matched_desc() call to capture the fuzzy score and flag
        low-confidence results into the manifest.

        The RefProcessor internals are NOT modified.  Instead we patch the
        excel_helper temporarily with a score-capturing variant of
        find_matched_desc() for the duration of this XML file's processing.
        """

        flagged_items: list[str] = []   # item_ids added to manifest this call
        xml_basename = os.path.basename(temp_xml.xml_file_name)

        # ── Monkey-patch: wrap find_matched_desc to intercept scores ─────────
        _original_fmd = excel_helper.find_matched_desc

        def _audited_find_matched_desc(ref, desc, threshold=AUDIT_THRESHOLD):
            """
            Calls the real find_matched_desc but also records the full
            scored candidate list when the best score is below threshold.
            """
            from rapidfuzz import process as rp, fuzz
            import re

            candidates = [
                d for r, d in excel_helper.refs_desc.items()
                if r in excel_helper.context.fscfai_files
            ]

            if not candidates:
                return _original_fmd(ref, desc, threshold)

            # Re-run the same scoring logic the original uses (mirrored from
            # excel_parser so we can capture the raw scored list).
            desc_upper = desc.upper() if desc else ""
            query = re.sub(r"\bDAG\b", "DAD", desc_upper, flags=re.IGNORECASE)

            if "DAD" not in query.upper():
                scored = rp.extract(query, candidates, scorer=fuzz.partial_ratio, limit=10)
            else:
                scored = rp.extract(query, candidates, scorer=fuzz.ratio, limit=10)

            if not scored:
                return _original_fmd(ref, desc, threshold)

            best_value, best_score, _ = scored[0]

            if best_score < AUDIT_THRESHOLD:
                # Flag this item in the manifest and return None so the
                # RefProcessor marks the row as FILE_NOT_FOUND (consistent
                # with original behaviour for no-match).
                all_candidates = [
                    {"value": v, "score": round(s, 2)}
                    for v, s, _ in scored
                ]
                # Retrieve the ref that corresponds to best_value
                best_ref = excel_helper.get_ref_by_desc(best_value) or ""
                item_id = manifest.record_fuzzy_flag(
                    xml_file=xml_basename,
                    current_ref=ref,
                    old_xml_path="",   # filled below after RefProcessor row
                    best_candidate=best_ref,
                    best_score=best_score,
                    all_candidates=all_candidates,
                )
                flagged_items.append(item_id)
                return None   # tells RefProcessor: no match found

            return _original_fmd(ref, desc, threshold)

        # Apply patch
        excel_helper.find_matched_desc = _audited_find_matched_desc

        try:
            processor = RefProcessor(excel_helper, temp_xml, fs_helper)
            grid_data, summary, output_path = processor.run()
        finally:
            # Always restore the original method
            excel_helper.find_matched_desc = _original_fmd

        return grid_data, summary, output_path, flagged_items

    def _package_zip(self, output_paths: list[str]) -> str:
        """Zip all output .list files into the session-level output ZIP."""
        if not output_paths:
            return "N/A"
        zip_name = "listes_types_v2.zip"
        zip_path = os.path.join(self.TEMP_DIR, zip_name)
        with zf.ZipFile(zip_path, "w", zf.ZIP_DEFLATED) as zout:
            for path in output_paths:
                if path and os.path.exists(path):
                    zout.write(path, arcname=os.path.basename(path))
        return zip_name
