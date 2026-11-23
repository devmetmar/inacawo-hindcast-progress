"""Catalog-centric views derived from tracking data (no invented evidence)."""

from __future__ import annotations

from typing import Any

from .tracking import TrackingStore, dataset_covers_year

POSTPROCESSED_PRODUCTS = ("ocean2d", "ocean3d", "wrf2d", "wrf3d")

ORIGIN_LABEL = {
    "cls_brazil": "CLS_HISTORICAL",
    "internal": "INTERNAL_HINDCAST",
    "shared_input": "SHARED_INPUT",
    "unknown": "UNKNOWN",
}


def derive_lifecycle(dataset: dict[str, Any]) -> str:
    """Conservative lifecycle from explicit field or evidenced statuses."""
    explicit = dataset.get("lifecycle_status")
    if explicit:
        return str(explicit)

    notes = (dataset.get("notes") or "").lower()
    if "incomplete" in notes:
        # Catalogued but coverage/integrity incomplete relative to claimed span.
        base = "INCOMPLETE"
    else:
        base = None

    if dataset.get("validation_status") == "ACCEPTED":
        return "ACCEPTED"
    if dataset.get("integrity_status") == "VERIFIED":
        return "VERIFIED"
    if dataset.get("integrity_status") == "FAILED":
        return "NOT_VERIFIED"
    if dataset.get("created_at"):
        # Evidenced creation but not yet verified.
        return base or "CREATED"
    # Presence in data/datasets means the record is catalogued.
    return base or "CATALOGUED"


def display_date(value: Any) -> str:
    if value in (None, "", "null"):
        return "UNKNOWN"
    return str(value)


def tasks_for_dataset(store: TrackingStore, dataset_id: str) -> list[dict[str, Any]]:
    """Link via task.related_dataset_ids or dataset.related_task_ids (no fuzzy match)."""
    by_id = {t["id"]: t for t in store.tasks}
    out: dict[str, dict[str, Any]] = {}
    for task in store.tasks:
        related = task.get("related_dataset_ids") or []
        if dataset_id in related:
            out[task["id"]] = task
    ds = next((d for d in store.datasets if d["id"] == dataset_id), None)
    if ds:
        for tid in ds.get("related_task_ids") or []:
            if tid in by_id:
                out[tid] = by_id[tid]
    return list(out.values())


def open_todo_count(tasks: list[dict[str, Any]]) -> int:
    open_status = {
        "NOT_STARTED",
        "READY",
        "RUNNING",
        "BLOCKED",
        "FAILED",
        "NEEDS_REVIEW",
    }
    return sum(1 for t in tasks if t.get("status") in open_status)


def group_todos(tasks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups = {
        "overdue": [],
        "due_soon": [],
        "in_progress": [],
        "blocked": [],
        "not_started": [],
        "completed_recently": [],
        "other": [],
    }
    # Without inventing "today", overdue/due_soon only if due_date present AND
    # we can compare — leave overdue/due_soon empty unless due_date set; do not invent.
    for task in tasks:
        status = task.get("status")
        due = task.get("due_date")
        if status == "COMPLETED":
            groups["completed_recently"].append(task)
        elif status == "BLOCKED":
            groups["blocked"].append(task)
        elif status in {"RUNNING", "NEEDS_REVIEW"}:
            groups["in_progress"].append(task)
        elif status in {"NOT_STARTED", "READY"}:
            if due:
                # Without wall-clock policy in data, keep as not_started with due noted.
                groups["not_started"].append(task)
            else:
                groups["not_started"].append(task)
        elif status == "FAILED":
            groups["blocked"].append(task)
        else:
            groups["other"].append(task)
    return groups


def dataset_timeline(
    store: TrackingStore, dataset: dict[str, Any]
) -> list[dict[str, str]]:
    """Chronological events from evidenced fields + activity log only."""
    events: list[dict[str, str]] = []
    ds_id = dataset["id"]

    def add(when: str | None, label: str, detail: str) -> None:
        events.append(
            {
                "when": when or "UNKNOWN",
                "label": label,
                "detail": detail,
                "sort_key": when or "",
            }
        )

    if dataset.get("created_at"):
        add(
            dataset.get("created_at"),
            "CREATED",
            dataset.get("created_at_provenance") or "created_at field",
        )
    if dataset.get("catalogued_at"):
        add(dataset.get("catalogued_at"), "CATALOGUED", "catalog record registration")
    else:
        add(None, "CATALOGUED", "record present in data/datasets (registration date UNKNOWN)")
    if dataset.get("last_inventory_scan"):
        add(dataset.get("last_inventory_scan"), "INVENTORY_SCAN", "last_inventory_scan")
    if dataset.get("verified_at"):
        add(dataset.get("verified_at"), "VERIFIED", "verified_at field")
    elif dataset.get("integrity_status") == "VERIFIED":
        add(None, "VERIFIED", "integrity_status=VERIFIED (date UNKNOWN)")
    if dataset.get("accepted_at"):
        add(dataset.get("accepted_at"), "ACCEPTED", "accepted_at field")
    elif dataset.get("validation_status") == "ACCEPTED":
        add(None, "ACCEPTED", "validation_status=ACCEPTED (date UNKNOWN)")

    for act in store.activities:
        if act.get("entity_id") == ds_id or (
            act.get("evidence_reference") and ds_id in str(act.get("evidence_reference"))
        ):
            add(
                act.get("timestamp"),
                act.get("action") or "ACTIVITY",
                f"{act.get('id')}: {act.get('notes') or ''}".strip(),
            )

    # Sort known dates first chronologically; UNKNOWN at end.
    known = [e for e in events if e["sort_key"]]
    unknown = [e for e in events if not e["sort_key"]]
    known.sort(key=lambda e: e["sort_key"])
    return known + unknown


def build_catalog_view(store: TrackingStore) -> dict[str, Any]:
    required = list(
        (store.project.get("completion_criteria") or {}).get("required_products")
        or list(POSTPROCESSED_PRODUCTS)
    )
    # Keep only postprocessed products for the year×product matrix.
    matrix_products = [p for p in required if p in POSTPROCESSED_PRODUCTS]
    if not matrix_products:
        matrix_products = list(POSTPROCESSED_PRODUCTS)

    hist_periods = sorted(
        [p for p in store.periods if p.get("stream") == "historical_baseline"],
        key=lambda p: p["calendar_year"],
    )
    rem_periods = sorted(
        [p for p in store.periods if p.get("stream") == "remaining_internal"],
        key=lambda p: p["calendar_year"],
    )

    rows: list[dict[str, Any]] = []
    for ds in store.datasets:
        todos = tasks_for_dataset(store, ds["id"])
        life = derive_lifecycle(ds)
        rows.append(
            {
                "id": ds["id"],
                "name": ds.get("name"),
                "description": ds.get("description") or ds.get("notes"),
                "origin": ds.get("origin"),
                "origin_label": ORIGIN_LABEL.get(ds.get("origin", ""), ds.get("origin")),
                "product": ds.get("product"),
                "period_start": (ds.get("period_coverage") or {}).get("start"),
                "period_end": (ds.get("period_coverage") or {}).get("end"),
                "period_basis": (ds.get("period_coverage") or {}).get("basis"),
                "lifecycle": life,
                "created_at": display_date(ds.get("created_at")),
                "created_at_provenance": ds.get("created_at_provenance") or "NOT_RECORDED",
                "catalogued_at": display_date(ds.get("catalogued_at")),
                "verified_at": display_date(ds.get("verified_at")),
                "accepted_at": display_date(ds.get("accepted_at")),
                "last_inventory_scan": display_date(ds.get("last_inventory_scan")),
                "file_count": ds.get("file_count"),
                "size_human": ds.get("size_human") or "UNKNOWN",
                "location": ds.get("location"),
                "manifest_ref": ds.get("manifest_ref"),
                "checksum_ref": ds.get("checksum_ref"),
                "integrity_status": ds.get("integrity_status"),
                "validation_status": ds.get("validation_status"),
                "owner": ds.get("owner") or "UNKNOWN",
                "todo_count": open_todo_count(todos),
                "todos": todos,
                "timeline": dataset_timeline(store, ds),
                "notes": ds.get("notes"),
            }
        )

    def count_life(status: str) -> int:
        return sum(1 for r in rows if r["lifecycle"] == status)

    catalogued = len(rows)
    created = sum(1 for r in rows if r["created_at"] != "UNKNOWN" or r["lifecycle"] in {"CREATED", "VERIFIED", "ACCEPTED"})
    # Created with evidence only:
    created_evidenced = sum(1 for r in rows if r["created_at"] != "UNKNOWN")
    verified = sum(1 for r in rows if r["integrity_status"] == "VERIFIED" or r["lifecycle"] == "VERIFIED")
    accepted = sum(1 for r in rows if r["validation_status"] == "ACCEPTED" or r["lifecycle"] == "ACCEPTED")
    incomplete = count_life("INCOMPLETE")
    outstanding_todos = open_todo_count(store.tasks)

    # Expected year×product cells (provisional denominators; not completion %).
    expected_cells = (len(hist_periods) + len(rem_periods)) * len(matrix_products)

    def cell_status(year: int, product: str, origin: str) -> str:
        matches = [
            d
            for d in store.datasets
            if d.get("origin") == origin
            and d.get("product") == product
            and dataset_covers_year(d, year) == "YES"
        ]
        if not matches:
            # No covering catalog record.
            return "MISSING" if origin == "cls_brazil" and year <= 2014 else "EXPECTED"
        # Prefer strongest evidenced lifecycle among matches.
        lives = [derive_lifecycle(d) for d in matches]
        for pref in ("ACCEPTED", "VERIFIED", "INCOMPLETE", "CATALOGUED", "CREATED", "NOT_VERIFIED"):
            if pref in lives:
                return pref
        return lives[0] if lives else "UNKNOWN"

    def matrix_for(periods: list[dict[str, Any]], origin: str) -> list[dict[str, Any]]:
        out = []
        for p in periods:
            year = p["calendar_year"]
            cells = {prod: cell_status(year, prod, origin) for prod in matrix_products}
            out.append({"year": year, "cells": cells, "period_id": p["id"]})
        return out

    # Historical CLS uses cls_brazil; internal remaining uses internal.
    hist_matrix = matrix_for(hist_periods, "cls_brazil")
    rem_matrix = matrix_for(rem_periods, "internal")

    # Coverage counts for expected cells (not overall project %).
    def matrix_counts(matrix: list[dict[str, Any]]) -> dict[str, int]:
        tallies: dict[str, int] = {}
        for row in matrix:
            for st in row["cells"].values():
                tallies[st] = tallies.get(st, 0) + 1
        return tallies

    all_tasks = list(store.tasks)
    return {
        "summary": {
            "catalogued_datasets": catalogued,
            "created_evidenced": created_evidenced,
            "created_or_beyond_lifecycle": created,
            "verified_datasets": verified,
            "accepted_datasets": accepted,
            "incomplete_datasets": incomplete,
            "outstanding_todos": outstanding_todos,
            "expected_year_product_cells": expected_cells,
            "matrix_products": matrix_products,
            "by_origin": {
                origin: sum(1 for r in rows if r["origin"] == origin)
                for origin in sorted({r["origin"] for r in rows})
            },
            "by_product": {
                product: sum(1 for r in rows if r["product"] == product)
                for product in sorted({r["product"] for r in rows if r["product"]})
            },
            "lifecycle_counts": {
                life: count_life(life)
                for life in sorted({r["lifecycle"] for r in rows})
            },
        },
        "datasets": rows,
        "historical_matrix": hist_matrix,
        "remaining_matrix": rem_matrix,
        "historical_matrix_counts": matrix_counts(hist_matrix),
        "remaining_matrix_counts": matrix_counts(rem_matrix),
        "todo_groups": group_todos(all_tasks),
        "all_todos": all_tasks,
        "definitions": {
            "catalogued": "Dataset YAML record present under data/datasets/",
            "created_evidenced": "created_at populated with provenance (never inferred from mtime alone)",
            "verified": "integrity_status=VERIFIED or explicit lifecycle VERIFIED",
            "accepted": "validation_status=ACCEPTED or explicit lifecycle ACCEPTED",
            "expected_cells": (
                "Provisional count of year×required_product cells for historical_baseline "
                "and remaining_internal periods; not an overall completion percentage"
            ),
            "matrix_missing": "No catalog dataset of that origin/product covers the year",
            "matrix_expected": "Internal remaining year with no covering catalog entry yet",
        },
    }
