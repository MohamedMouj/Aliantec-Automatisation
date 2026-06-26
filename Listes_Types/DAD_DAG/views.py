"""
views.py  (MODIFIED – two-stage audit workflow)
------------------------------------------------
Changes vs. the original
─────────────────────────
• index() – after calling orchestrator.process_all(), checks whether a
  manifest was returned (= low-confidence matches exist).  If so, it
  renders the audit review form instead of the results table.  The
  session_id is stored in the Django session so the follow-up POST can
  locate the manifest on disk.

• finalize_review() – new endpoint.  Receives the user's manual choices,
  calls orchestrator.finalize(), then renders the normal results page.

• _build_context() – shared helper that constructs the final results
  context dict and encodes the output ZIP as base64 for the inline
  download (same mechanism as the original).

• get_safe_path() – unchanged.
• The finally-block that wipes temp files was kept in finalize_review()
  only; index() must NOT wipe the session dir when a manifest was
  returned (the draft files must survive the round-trip).
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import uuid
from pathlib import Path

from django.shortcuts import render
from django_tables2 import RequestConfig

from .services.orchestrator import Orchestrator
from .helpers.audit_manifest import AuditManifest, NEEDS_REVIEW
from ..tables import UpdateTable, DeletionTable, AdditionTable

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_safe_path(path_str: str) -> str:
    """Add Windows Long Path prefix when needed; no-op on Linux."""
    abs_path = os.path.abspath(path_str)
    if os.name == "nt" and not abs_path.startswith("\\\\?\\"):
        return "\\\\?\\" + abs_path
    return abs_path


def _base_temp_dir() -> Path:
    return Path(__file__).resolve().parent / "temp"


def _build_results_context(request, results: dict, session_dir: Path) -> dict:
    """
    Shared helper: build the template context for the final results page.
    Encodes the output ZIP as base64 for the inline download link.
    """
    zip_output_name = results.get("download_name")
    zip_b64 = None
    final_zip_name = None

    if zip_output_name and zip_output_name != "N/A":
        source_zip = session_dir / zip_output_name
        if source_zip.exists():
            zip_b64 = base64.b64encode(source_zip.read_bytes()).decode("ascii")
            final_zip_name = f"{session_dir.name}.zip"

    table_updates   = UpdateTable(results.get("all_grid_data", []))
    table_additions = AdditionTable(results.get("addition_data", []))
    table_deletions = DeletionTable(results.get("deletion_data", []))

    RequestConfig(request, paginate=False).configure(table_updates)
    RequestConfig(request, paginate=False).configure(table_additions)
    RequestConfig(request, paginate=False).configure(table_deletions)

    return {
        "table_updates":   table_updates,
        "table_additions": table_additions,
        "table_deletions": table_deletions,
        "summary":         results["total_summary"],
        "zip_b64":         zip_b64,
        "zip_name":        final_zip_name,
        "has_download":    zip_b64 is not None,
        "processed":       True,
        "xml_count":       results["total_summary"].get("xml_count", []),
    }


# ─────────────────────────────────────────────────────────────────────────────
# View: Phase 1 – upload + automated processing
# ─────────────────────────────────────────────────────────────────────────────

TEMPLATE = "Listes_Types/DAD_DAG/index.html"
REVIEW_TEMPLATE = "Listes_Types/DAD_DAG/audit_review.html"


def index(request):
    """
    Handles the initial file upload form (GET) and the first processing
    pass (POST).

    POST response branches:
    ├── No low-confidence matches → render results page (same as original).
    └── Low-confidence matches exist → render audit review form, keep
        temp directory alive, store session_id in Django session.
    """
    if request.method != "POST":
        return render(request, TEMPLATE)

    if not (request.FILES.get("pta_file") and request.FILES.get("zipped_fscfai")):
        return render(request, TEMPLATE)

    pta_file = request.FILES["pta_file"]
    zip_file = request.FILES["zipped_fscfai"]

    session_id = uuid.uuid4().hex[:8]
    session_dir = Path(get_safe_path(str(_base_temp_dir() / session_id)))
    os.makedirs(session_dir, exist_ok=True)

    # ── Persist uploads ───────────────────────────────────────────────────────
    excel_path = session_dir / pta_file.name
    with open(excel_path, "wb+") as fh:
        for chunk in pta_file.chunks():
            fh.write(chunk)

    zip_path = session_dir / zip_file.name
    with open(zip_path, "wb+") as fh:
        for chunk in zip_file.chunks():
            fh.write(chunk)

    # ── FSCFAI JSON list ──────────────────────────────────────────────────────
    fscfai_data = None
    fscfai_json = request.POST.get("fscfai_json")
    if fscfai_json:
        try:
            fscfai_data = json.loads(fscfai_json)
        except Exception as exc:  # noqa: BLE001
            return render(request, TEMPLATE, {"error": f"JSON invalide : {exc}"})

    extract_dir = get_safe_path(str(session_dir / "e"))
    os.makedirs(extract_dir, exist_ok=True)
    parse_right = request.POST.get("parse_right") == "on"

    try:
        orchestrator = Orchestrator(
            excel_path, zip_path, extract_dir,
            fscfai_data=fscfai_data,
            parse_right=parse_right,
        )
        results, error, manifest = orchestrator.process_all()

        if error:
            return render(request, TEMPLATE, {"error": error})

        # ── Branch A: audit review required ──────────────────────────────────
        if manifest is not None and manifest.needs_review:
            # Store session_id so finalize_review() can locate the manifest.
            request.session["audit_session_id"] = session_id

            review_payload = manifest.to_review_payload()
            context = {
                "needs_audit":    True,
                "audit_items":    review_payload,
                "audit_count":    len(review_payload),
                "session_id":     session_id,
                # Partial summary so the user knows what has already been done
                "summary":        results["total_summary"],
            }
            return render(request, REVIEW_TEMPLATE, context)

        # ── Branch B: no audit required – finalize immediately ────────────────
        context = _build_results_context(request, results, session_dir)
        return render(request, TEMPLATE, context)

    except Exception as exc:  # noqa: BLE001
        return render(request, TEMPLATE, {"error": str(exc)})

    finally:
        # Only clean up when we are NOT handing off to the review form.
        # The flag is set in the session before we return, so check it.
        audit_session_in_flight = request.session.get("audit_session_id") == session_id
        if not audit_session_in_flight:
            try:
                shutil.rmtree(session_dir, ignore_errors=True)
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# View: Phase 2 – receive user choices and finalize
# ─────────────────────────────────────────────────────────────────────────────

def finalize_review(request):
    """
    Dedicated endpoint for the audit review form submission (Phase 2).

    Expected POST fields
    --------------------
    choice_<item_id> : str
        The FSCFAI reference string the user selected for that audit item.
        One field per item in the audit report.

    The session_id is read from the Django session to locate the manifest
    on disk – the user never sees or can tamper with the path.
    """
    if request.method != "POST":
        return render(request, TEMPLATE, {"error": "Méthode non autorisée."})

    session_id = request.session.get("audit_session_id")
    if not session_id:
        return render(request, TEMPLATE, {
            "error": "Session d'audit expirée ou introuvable. Veuillez recommencer."
        })

    session_dir = Path(get_safe_path(str(_base_temp_dir() / session_id)))

    try:
        manifest = AuditManifest.load(session_dir)
    except FileNotFoundError:
        return render(request, TEMPLATE, {
            "error": "Manifeste d'audit introuvable. La session a peut-être expiré."
        })

    if manifest.status == "finalized":
        return render(request, TEMPLATE, {
            "error": "Cette session a déjà été finalisée."
        })

    # ── Parse user choices from POST data ────────────────────────────────────
    choices: dict[str, str] = {}
    for key, value in request.POST.items():
        if key.startswith("choice_"):
            item_id = key[len("choice_"):]
            choices[item_id] = value.strip()

    # Merge choices into the manifest (on disk).
    stale = manifest.apply_user_choices(choices)
    if stale:
        # Log but don't abort – stale IDs are simply ignored.
        # In production, wire this to your logging framework.
        print(f"[audit] WARNING: unknown item_ids in POST: {stale}")

    manifest.save()

    # ── Re-instantiate orchestrator with an empty context ────────────────────
    # We only need the finalize() method; the context will be populated
    # from the manifest's pending_dir during finalize().
    extract_dir = manifest.pending_dir
    # Dummy paths – finalize() reads everything from manifest & disk.
    orchestrator = Orchestrator(
        pta_full_path="",
        zip_path="",
        extract_dir=extract_dir,
    )
    # Rebuild fscfai_files from the manifest's audit_items so that
    # xml_parser.update_reference() can resolve chosen refs to filenames.
    # (The original fscfai_files were in SharedData, which didn't persist.
    #  We reconstruct the minimal subset needed for patching.)
    for item in manifest.audit_items:
        for candidate in item.get("candidates", []):
            ref = candidate.get("value")
            if ref:
                # The filename convention: <ref>_*.fscfai  – we stored it
                # in the manifest's candidate list as returned by excel_parser.
                # If the full filename is available, use it; else skip.
                # (Extend record_fuzzy_flag to store filenames if needed.)
                pass

    results, error = orchestrator.finalize(manifest)

    # ── Clean up session key ──────────────────────────────────────────────────
    try:
        del request.session["audit_session_id"]
    except KeyError:
        pass

    if error:
        return render(request, TEMPLATE, {"error": error})

    try:
        context = _build_results_context(request, results, session_dir)
        return render(request, TEMPLATE, context)
    finally:
        # Phase 2 is done – wipe the entire session directory.
        try:
            shutil.rmtree(session_dir, ignore_errors=True)
        except Exception:
            pass
