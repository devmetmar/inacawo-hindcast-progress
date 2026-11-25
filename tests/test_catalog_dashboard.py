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
from lib.coverage import build_year_day_coverage  # noqa: E402
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
    # Primary catalog = ocean2d/3d + wrf2d/3d only (one CLS row each)
    assert s["catalogued_datasets"] == 4
    assert len(catalog["datasets"]) == 4
    assert set(s["by_product"]) == {"ocean2d", "ocean3d", "wrf2d", "wrf3d"}
    assert s["by_product"]["ocean2d"] == 1
    assert s["by_product"]["ocean3d"] == 1
    assert s["by_product"]["wrf2d"] == 1
    assert s["by_product"]["wrf3d"] == 1
    assert s["by_origin"]["cls_brazil"] == 4
    assert s["other_dataset_count"] == 4  # run_dirs, roms_rst, forcing, sample
    assert "dataset_cls_post_ocean2d_with_tm01" not in {d["id"] for d in store.datasets}


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
    # Free-text notes must not flip lifecycle; use explicit field.
    noted = {
        "integrity_status": "NOT_VERIFIED",
        "validation_status": "UNKNOWN",
        "notes": "incomplete relative to claimed span",
        "created_at": None,
    }
    assert derive_lifecycle(noted) == "CATALOGUED"
    noted["lifecycle_status"] = "INCOMPLETE"
    assert derive_lifecycle(noted) == "INCOMPLETE"

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
    # Directory presence alone must not mark VERIFIED/ACCEPTED
    assert all(
        r["lifecycle"] not in {"VERIFIED", "ACCEPTED"} for r in catalog["datasets"]
    )


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


def test_year_product_matrix_ocean2d_split_folders() -> None:
    store = TrackingStore.load(ROOT)
    catalog = build_catalog_view(store)
    row_1996 = next(r for r in catalog["historical_matrix"] if r["year"] == 1996)
    row_2005 = next(r for r in catalog["historical_matrix"] if r["year"] == 2005)
    # Unified ocean2d covers legacy + tm01 trees through 2015-01-31
    assert row_1996["cells"]["ocean2d"] == "CATALOGUED"
    assert row_2005["cells"]["ocean2d"] == "CATALOGUED"
    assert row_2005["cells"]["ocean3d"] in {"CATALOGUED", "INCOMPLETE", "NOT_VERIFIED"}
    ids = {d["id"] for d in store.datasets}
    assert "dataset_cls_post_ocean2d" in ids
    assert "dataset_cls_post_ocean2d_with_tm01" not in ids


def test_dashboard_header_omits_scope_and_acceptance_banner() -> None:
    store = TrackingStore.load(ROOT)
    progress = compute_progress(store)
    assert not progress["scope_confirmed"]
    mod = _load_generate()
    catalog = build_catalog_view(store)
    html = mod.render(store, progress, catalog)
    assert "Hindcast scope:" not in html
    assert "Overall acceptance:" not in html
    assert "overall % suppressed" not in html
    # Must not show a fabricated overall completion percentage in the header
    assert "Overall acceptance: <strong>" not in html


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
    # Sample is tracked as other (not a primary ocean/WRF product)
    sample = next(
        r
        for r in catalog["other_datasets"]
        if r["id"] == "dataset_internal_post_sample_20150113"
    )
    assert sample["lifecycle"] != "ACCEPTED"
    assert sample["lifecycle"] != "VERIFIED"
    assert all(
        r["product"] in {"ocean2d", "ocean3d", "wrf2d", "wrf3d"} for r in catalog["datasets"]
    )
    # Matrix cells for remaining years stay EXPECTED (not verified from sample)
    for row in catalog["remaining_matrix"]:
        for st in row["cells"].values():
            assert st not in {"VERIFIED", "ACCEPTED", "CREATED"}


def test_schema_accepts_new_optional_fields() -> None:
    store = TrackingStore.load(ROOT)
    issues = validate_store(store, ROOT)
    errors = [i.message for i in issues if i.level == "error"]
    assert errors == []


def test_day_coverage_2015_cls_january_and_sparse_internal() -> None:
    cov = build_year_day_coverage(ROOT, 2015)
    assert cov["has_presence_file"] is True
    assert cov["year"] == 2015
    cls_o3 = cov["streams"]["cls_brazil"]["products"]["ocean3d"]
    assert cls_o3["present_count"] == 31
    assert cls_o3["out_count"] == 365 - 31
    jan1 = next(d for d in cls_o3["days"] if d["date"] == "20150101")
    feb1 = next(d for d in cls_o3["days"] if d["date"] == "20150201")
    assert jan1["state"] == "PRESENT"
    assert feb1["state"] == "OUT_OF_SPAN"
    # ocean2d folds on-disk ocean2d_with_tm01 into the single catalog product
    assert set(cov["products"]) == {"ocean2d", "ocean3d", "wrf2d", "wrf3d"}
    assert set(cov["streams"]["cls_brazil"]["products"]) == {
        "ocean2d",
        "ocean3d",
        "wrf2d",
        "wrf3d",
    }
    cls_o2 = cov["streams"]["cls_brazil"]["products"]["ocean2d"]
    assert cls_o2["present_count"] == 31
    internal = cov["streams"]["internal"]["products"]["wrf2d"]
    assert internal["present_count"] == 1
    assert internal["missing_count"] == 364
    sample = next(d for d in internal["days"] if d["date"] == "20150113")
    assert sample["state"] == "PRESENT"
    # Must not treat sparse internal as full-year present
    assert cov["streams"]["internal"]["all_required"]["present_count"] == 1


def test_dashboard_includes_identity_report() -> None:
    store = TrackingStore.load(ROOT)
    progress = compute_progress(store)
    catalog = build_catalog_view(store)
    mod = _load_generate()
    html = mod.render(store, progress, catalog)
    assert 'id="reports"' in html
    assert 'href="#reports"' in html
    assert 'id="report-ft2-cls-20150101-identity"' in html
    assert "not identical" in html
    assert "7.127007" in html
    assert "ft2_cls_20150101_timeseries.png" in html
    assert "ft2_cls_20150101_spatial.png" in html
    assert 'alt="Hourly domain mean' in html
    report = html.split('id="reports"', 1)[1].split('id="matrices"', 1)[0]
    assert "VERIFIED or scientific ACCEPTED" in report
    assert ">ACCEPTED<" not in report


def test_dashboard_includes_daily_progress_panel() -> None:
    store = TrackingStore.load(ROOT)
    progress = compute_progress(store)
    catalog = build_catalog_view(store)
    assert catalog.get("day_coverage") is not None
    mod = _load_generate()
    html = mod.render(store, progress, catalog)
    assert 'id="daily-progress"' in html
    assert "Daily inventory" in html
    assert 'id="day-coverage-data"' in html
    assert 'id="day-product-summary"' in html
    assert "day-present" in html  # CSS class for client-rendered cells
    # display:grid must not defeat HTML hidden (would show CLS + internal calendars)
    assert ".cal-stack[hidden]" in html
    assert "display: none !important" in html
    assert 'id="cal-internal"' in html and "hidden" in html.split('id="cal-internal"', 1)[1][:80]
    assert 'id="cal-stream-label"' in html
    # Daily product filter / summary use catalog products only
    day_section = html.split('id="daily-progress"', 1)[1].split('id="reports"', 1)[0]
    assert "ocean2d_with_tm01" not in day_section
    for p in ("ocean2d", "ocean3d", "wrf2d", "wrf3d"):
        assert f'option value="{p}"' in day_section or f">{p}</option>" in day_section
    assert "Hindcast scope:" not in html
    assert catalog["day_coverage"]["available_years"][0] == 1995
    assert 2015 in catalog["day_coverage"]["available_years"]
    assert 2025 in catalog["day_coverage"]["available_years"]
    assert 'id="day-year"' in html
    assert '<option value="1995"' in html
    assert '<option value="2015"' in html
    assert '<option value="2025"' in html
    # Sparse sample must not imply verified year in matrix
    row_2015 = next(r for r in catalog["remaining_matrix"] if r["year"] == 2015)
    for st in row_2015["cells"].values():
        assert st not in {"VERIFIED", "ACCEPTED"}


def test_dashboard_ux_landmarks_and_stale_chrome() -> None:
    store = TrackingStore.load(ROOT)
    progress = compute_progress(store)
    catalog = build_catalog_view(store)
    mod = _load_generate()
    html = mod.render(store, progress, catalog)

    assert 'class="skip-link"' in html
    assert 'href="#main"' in html
    assert 'aria-label="Catalog sections"' in html
    assert 'id="overview"' in html
    assert 'id="inventory"' in html
    assert 'id="todos"' in html
    assert 'aria-live="polite"' in html

    # Full catalog year dropdown (not a static single-year label)
    assert 'class="year-static"' not in html
    assert 'id="day-year" disabled' not in html
    assert "<select id=\"day-year\">" in html
    assert "Additional years need day_presence" not in html

    # Day cells are non-interactive spans (client-rendered; no day buttons in markup)
    assert 'button type="button" class="day' not in html

    # Todo anchors live on task rows; no hidden placeholder divs
    assert 'id="todo-task_confirm_scope"' in html
    assert '<div id="todo-' not in html

    # Empty TODO groups omitted
    assert "In progress (0)" not in html
    assert "Blocked (0)" not in html
    assert "Completed (0)" not in html
    assert "Not started / Ready" in html

    # Priority CRITICAL uses semantic bad/warn styling, not grey unk
    assert 'class="pill bad">CRITICAL</span>' in html
    assert "filter datasets" in html
    assert "Skip to catalog" in html
    assert "Hindcast Catalog" in html

    # Owner filter hidden when only one distinct owner
    assert "<label>Owner<select id=\"f-owner\">" not in html
    assert 'id="f-owner"' in html

    # Overview chips instead of raw JSON dumps
    assert "chip-row" in html
    overview = html.split("Catalog overview", 1)[1].split("Daily inventory", 1)[0]
    assert "Origins" in overview
    assert "chip-k" in overview
    assert "Origins: {" not in overview


def test_multi_year_day_coverage_from_inventory() -> None:
    cov = build_year_day_coverage(ROOT, 2005)
    assert cov["year"] == 2005
    # Synthesized from inventory when no day_presence_2005.json
    assert cov["has_presence_file"] is False
    assert cov["synthesized"] is True
    cls_o3 = cov["streams"]["cls_brazil"]["products"]["ocean3d"]
    assert cls_o3["present_count"] == 365
    assert cls_o3["missing_count"] == 0
    # ocean2d merges with_tm01 inventory folder for 2005
    assert "ocean2d_with_tm01" not in cov["streams"]["cls_brazil"]["products"]
    cls_o2 = cov["streams"]["cls_brazil"]["products"]["ocean2d"]
    assert cls_o2["present_count"] == 365


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
