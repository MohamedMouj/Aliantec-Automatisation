"""
audit_manifest.py
-----------------
File-based state persistence layer for the two-stage audit workflow.

No database is used. All state is serialised to a single JSON manifest
written inside the session temp directory.  The manifest is the sole
source of truth between the first processing pass and the user review
round-trip.

Manifest path (relative to the session root that views.py already
creates):
    <session_dir>/
        manifest.json          ← written here by AuditManifest.save()
        e/                     ← extracted .list XML files (existing)
        v/                     ← versioned output files (existing, written by xml_parser)

Status transitions
------------------
    (new)  →  pending_review   written by Orchestrator after first pass
    pending_review → finalized  written by finalize_view after user review
    *      → error             written on unhandled exception
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Sentinel value used in manifest when an item requires user choice ──
NEEDS_REVIEW = "__NEEDS_REVIEW__"

# Fuzzy-match threshold below which a result is flagged for human review
AUDIT_THRESHOLD = 80.0


# ─────────────────────────────────────────────────────────────────────────────
# Manifest data-class (plain dict wrapper so we stay JSON-serialisable)
# ─────────────────────────────────────────────────────────────────────────────

class AuditManifest:
    """
    Wraps the on-disk manifest.json.  Instantiate once per request;
    call save() to persist changes.
    """

    FILENAME = "manifest.json"

    def __init__(self, session_dir: str | Path):
        self.session_dir = Path(session_dir)
        self.path = self.session_dir / self.FILENAME
        self._data: dict[str, Any] = {}

    # ── Constructors ──────────────────────────────────────────────────────────

    @classmethod
    def create_new(cls, session_dir: str | Path, *, session_id: str,
                   pending_dir: str, output_zip_path: str) -> "AuditManifest":
        """Initialise a brand-new manifest for a fresh session."""
        m = cls(session_dir)
        m._data = {
            "schema_version": 1,
            "session_id": session_id,
            "created_at": _utcnow(),
            "updated_at": _utcnow(),
            "status": "pending_review",
            "pending_dir": str(pending_dir),
            "output_zip_path": str(output_zip_path),
            "audit_items": [],           # populated by record_fuzzy_flag()
            "finalized_at": None,
        }
        return m

    @classmethod
    def load(cls, session_dir: str | Path) -> "AuditManifest":
        """Load an existing manifest from disk.  Raises FileNotFoundError."""
        m = cls(session_dir)
        with open(m.path, "r", encoding="utf-8") as fh:
            m._data = json.load(fh)
        return m

    # ── Persistence ───────────────────────────────────────────────────────────

    def save(self) -> None:
        self._data["updated_at"] = _utcnow()
        self.session_dir.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, ensure_ascii=False, indent=2)

    # ── Audit item management ─────────────────────────────────────────────────

    def record_fuzzy_flag(
        self,
        *,
        xml_file: str,
        current_ref: str,
        old_xml_path: str,
        best_candidate: str,
        best_score: float,
        all_candidates: list[dict],   # [{"value": str, "score": float}, ...]
    ) -> str:
        """
        Add one low-confidence match to the manifest.
        Returns the stable item_id so the orchestrator can correlate it
        with the grid_data row.
        """
        item_id = uuid.uuid4().hex
        self._data["audit_items"].append({
            "item_id": item_id,
            "xml_file": xml_file,              # relative basename of the .list file
            "current_ref": current_ref,
            "old_xml_path": old_xml_path,
            "automated_choice": best_candidate,
            "score": round(best_score, 2),
            "candidates": all_candidates,      # top-N for the review UI
            "user_choice": NEEDS_REVIEW,       # overwritten by apply_user_choices()
        })
        return item_id

    def apply_user_choices(self, choices: dict[str, str]) -> list[str]:
        """
        Merge user selections into the manifest.

        Parameters
        ----------
        choices : {item_id: chosen_candidate_value, ...}

        Returns
        -------
        List of item_ids that were NOT present in the manifest (stale POSTs).
        """
        index = {item["item_id"]: item for item in self._data["audit_items"]}
        unknown = []
        for item_id, chosen in choices.items():
            if item_id in index:
                index[item_id]["user_choice"] = chosen
            else:
                unknown.append(item_id)
        return unknown

    # ── Status helpers ────────────────────────────────────────────────────────

    def mark_finalized(self) -> None:
        self._data["status"] = "finalized"
        self._data["finalized_at"] = _utcnow()

    def mark_error(self, message: str) -> None:
        self._data["status"] = "error"
        self._data["error"] = message

    @property
    def status(self) -> str:
        return self._data.get("status", "unknown")

    @property
    def pending_dir(self) -> str:
        return self._data["pending_dir"]

    @property
    def output_zip_path(self) -> str:
        return self._data["output_zip_path"]

    @property
    def session_id(self) -> str:
        return self._data["session_id"]

    @property
    def audit_items(self) -> list[dict]:
        return self._data.get("audit_items", [])

    @property
    def needs_review(self) -> bool:
        """True when at least one item still awaits a user choice."""
        return any(
            item["user_choice"] == NEEDS_REVIEW
            for item in self.audit_items
        )

    def items_by_xml(self) -> dict[str, list[dict]]:
        """Group audit items by xml_file for efficient per-file patching."""
        grouped: dict[str, list[dict]] = {}
        for item in self.audit_items:
            grouped.setdefault(item["xml_file"], []).append(item)
        return grouped

    # ── Serialisation for the Django view context ─────────────────────────────

    def to_review_payload(self) -> list[dict]:
        """
        Returns a list of dicts safe to pass directly into a Django template
        context or JSON response for the audit review form.
        """
        return [
            {
                "item_id":         item["item_id"],
                "xml_file":        item["xml_file"],
                "current_ref":     item["current_ref"],
                "old_xml_path":    item["old_xml_path"],
                "score":           item["score"],
                "automated_choice": item["automated_choice"],
                "candidates":      item["candidates"],
            }
            for item in self.audit_items
            if item["user_choice"] == NEEDS_REVIEW
        ]


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
