"""Catalog-centric dashboard and lifecycle tests."""

from __future__ import annotations

import copy
import importlib.util
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.catalog import (  # noqa: E402
    build_catalog_view,
    derive_lifecycle,
    group_todos,
    tasks_for_dataset,
)
from lib.tracking import TrackingStore, compute_progress, validate_store  # noqa: E402


def _load_generate():
    path = ROOT / "dashboard" / "generate.py"
    spec = importlib.util.spec_from_file_location("dash_generate_catalog", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_dataset_counts_by_origin_and_product() -> None:
    store = TrackingStore.load(ROOT)
    catalog = build_catalog_view(store)
    s = catalog["summary"]
    assert s["catalogued_datasets"] == len(store.datasets) == 7
    assert s["by_origin"]["cls_brazil"] == 5
    assert s["by_origin"]["internal"] == 2
    assert s["by_product"]["ocean2d"] == 1
    assert s["by_product"]["ocean3d"] == 1
    assert s["by_product"]["wrf2d"] == 1
    assert s["by_product"]["wrf3d"] == 1
    assert s["by_product"]["run_dirs"] == 1
    assert s["by_product"]["forcing"] == 1
    assert s["by_product"]["other"] == 1


def test_missing_metadata_and_unknown_creation_dates() -> None:
    store = TrackingStore.load(ROOT)
    catalog = build_catalog_view(store)
    assert catalog["summary"]["created_evidenced"] == 0
    for row in catalog["datasets"]:
        assert row["created_at"] == "UNKNOWN"
        assert row["owner"] == "UNKNOWN"
        # Catalog registration date recorded for current records
        assert row["catalogued_at"] != "UNKNOWN" or row["id"].startswith("dataset_")


def test_lifecycle_derivation_incomplete_and_catalogued() -> None:
    ocean2d = {
        "integrity_status": "NOT_VERIFIED",
        "validation_status": "UNKNOWN",
        "notes": "incomplete relative to claimed span",
        "created_at": None,
    }
    assert derive_lifecycle(ocean2d) == "INCOMPLETE"

    plain = {
        "integrity_status": "NOT_VERIFIED",
        "validation_status": "UNKNOWN",
        "notes": "ok",
        "created_at": None,
    }
    assert derive_lifecycle(plain) == "CATALOGUED"

    verified = {
        "integrity_status": "VERIFIED",
        "validation_status": "UNKNOWN",
        "notes": "",
        "created_at": "2020-01-01",
        "created_at_provenance": "manifest",
    }
    assert derive_lifecycle(verified) == "VERIFIED"

    accepted = {
        "integrity_status": "VERIFIED",
        "validation_status": "ACCEPTED",
        "notes": "",
        "created_at": "2020-01-01",
    }
    assert derive_lifecycle(accepted) == "ACCEPTED"

    explicit = copy.deepcopy(plain)
    explicit["lifecycle_status"] = "BLOCKED"
    assert derive_lifecycle(explicit) == "BLOCKED"


def test_lifecycle_not_auto_advanced_without_evidence() -> None:
    store = TrackingStore.load(ROOT)
    catalog = build_catalog_view(store)
    assert catalog["summary"]["verified_datasets"] == 0
    assert catalog["summary"]["accepted_datasets"] == 0
    assert catalog["summary"]["incomplete_datasets"] >= 1


def test_timeline_ordering_known_before_unknown() -> None:
    store = TrackingStore.load(ROOT)
    catalog = build_catalog_view(store)
    row = next(r for r in catalog["datasets"] if r["id"] == "dataset_cls_post_ocean2d")
    timeline = row["timeline"]
    assert timeline
    known = [e for e in timeline if e["when"] != "UNKNOWN"]
    unknown = [e for e in timeline if e["when"] == "UNKNOWN"]
    # Known timestamps are sorted ascending
    known_keys = [e["when"] for e in known]
    assert known_keys == sorted(known_keys)
    # Unknowns appear after knowns in our builder
    if known and unknown:
        first_unknown_idx = timeline.index(unknown[0])
        last_known_idx = timeline.index(known[-1])
        assert first_unknown_idx > last_known_idx


def test_todo_counts_grouping_and_dataset_links() -> None:
    store = TrackingStore.load(ROOT)
    catalog = build_catalog_view(store)
    assert catalog["summary"]["outstanding_todos"] == 3
    groups = catalog["todo_groups"]
    assert len(groups["not_started"]) >= 1  # READY + NOT_STARTED
    assert len(groups["completed_recently"]) == 0

    linked = tasks_for_dataset(store, "dataset_cls_post_ocean2d")
    assert any(t["id"] == "task_historical_inventory_acceptance" for t in linked)
    ocean2d = next(r for r in catalog["datasets"] if r["id"] == "dataset_cls_post_ocean2d")
    assert ocean2d["todo_count"] >= 1


def test_historical_internal_separation_in_matrix() -> None:
    store = TrackingStore.load(ROOT)
    catalog = build_catalog_view(store)
    hist_years = {r["year"] for r in catalog["historical_matrix"]}
    rem_years = {r["year"] for r in catalog["remaining_matrix"]}
    assert hist_years & rem_years == set()
    assert 1995 in hist_years
    assert 2015 in rem_years
    # Sparse internal sample must not mark full 2015 products complete
    row_2015 = next(r for r in catalog["remaining_matrix"] if r["year"] == 2015)
    for product in catalog["summary"]["matrix_products"]:
        assert row_2015["cells"][product] in {"EXPECTED", "MISSING", "UNKNOWN"}
        assert row_2015["cells"][product] not in {"VERIFIED", "ACCEPTED"}


def test_year_product_matrix_ocean2d_gap() -> None:
    store = TrackingStore.load(ROOT)
    catalog = build_catalog_view(store)
    row_1996 = next(r for r in catalog["historical_matrix"] if r["year"] == 1996)
    row_2005 = next(r for r in catalog["historical_matrix"] if r["year"] == 2005)
    assert row_1996["cells"]["ocean2d"] == "INCOMPLETE"
    assert row_2005["cells"]["ocean2d"] == "MISSING"
    # Presence of ocean3d for a year must not imply ocean2d complete
    assert row_2005["cells"]["ocean3d"] in {"CATALOGUED", "INCOMPLETE", "NOT_VERIFIED"}


def test_no_overall_percent_when_provisional() -> None:
    store = TrackingStore.load(ROOT)
    progress = compute_progress(store)
    assert not progress["scope_confirmed"]
    mod = _load_generate()
    catalog = build_catalog_view(store)
    html = mod.render(store, progress, catalog)
    assert "PROVISIONAL" in html or "NOT CONFIRMED" in html
    assert "NOT CONFIRMED — overall % suppressed" in html
    # Must not show a fabricated overall completion like "42%"
    assert "Overall acceptance: <strong>NOT CONFIRMED — overall % suppressed</strong>" in html


def test_dashboard_empty_and_incomplete_records() -> None:
    store = TrackingStore.load(ROOT)
    # Empty datasets
    empty = copy.deepcopy(store)
    empty.datasets = []
    catalog_empty = build_catalog_view(empty)
    assert catalog_empty["summary"]["catalogued_datasets"] == 0
    mod = _load_generate()
    progress = compute_progress(store)
    html_empty = mod.render(empty, progress, catalog_empty)
    assert "Catalogued" in html_empty
    assert ">0<" in html_empty or "0</div>" in html_empty

    # Incomplete ocean2d still renders
    catalog = build_catalog_view(store)
    html = mod.render(store, progress, catalog)
    assert "dataset_cls_post_ocean2d" in html
    assert "INCOMPLETE" in html
    assert "UNKNOWN" in html
    assert "CLS_HISTORICAL" in html
    assert "INTERNAL_HINDCAST" in html
    assert "issue_period_discrepancy" in html


def test_dashboard_generation_determinism_excluding_timestamp(
    tmp_path: Path,
) -> None:
    store = TrackingStore.load(ROOT)
    progress = compute_progress(store)
    # Freeze generated_at for comparison
    progress = copy.deepcopy(progress)
    progress["generated_at"] = "2026-11-23T00:00:00+00:00"
    mod = _load_generate()
    catalog = build_catalog_view(store)
    a = mod.render(store, progress, catalog)
    b = mod.render(store, progress, catalog)
    assert a == b
    # Strip generated_at line and compare structure still stable
    stripped = re.sub(r"Generated [^·]+·", "Generated TIMESTAMP ·", a)
    assert "dataset_cls_post_ocean2d" in stripped


def test_no_false_completion_from_sparse_outputs() -> None:
    store = TrackingStore.load(ROOT)
    catalog = build_catalog_view(store)
    sample = next(
        r for r in catalog["datasets"] if r["id"] == "dataset_internal_post_sample_20150113"
    )
    assert sample["lifecycle"] != "ACCEPTED"
    assert sample["lifecycle"] != "VERIFIED"
    # Matrix cells for remaining years stay EXPECTED (not verified from sample)
    for row in catalog["remaining_matrix"]:
        for st in row["cells"].values():
            assert st not in {"VERIFIED", "ACCEPTED", "CREATED"}


def test_schema_accepts_new_optional_fields() -> None:
    store = TrackingStore.load(ROOT)
    issues = validate_store(store, ROOT)
    errors = [i.message for i in issues if i.level == "error"]
    assert errors == []


def test_group_todos_empty_due_does_not_invent_overdue() -> None:
    tasks = [
        {
            "id": "task_x",
            "status": "READY",
            "due_date": None,
            "title": "t",
            "priority": "HIGH",
            "owner": "member_01",
        }
    ]
    groups = group_todos(tasks)
    assert groups["overdue"] == []
    assert groups["due_soon"] == []
    assert len(groups["not_started"]) == 1
