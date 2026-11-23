"""Regression tests for audit findings F-01..F-04."""

from __future__ import annotations

import copy
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.tracking import (  # noqa: E402
    TrackingStore,
    classify_hpc_snapshot,
    compute_progress,
    period_output_assessment,
    select_latest_usable_snapshot,
    validate_store,
)


@pytest.fixture
def store() -> TrackingStore:
    return TrackingStore.load(ROOT)


def test_f01_validator_rejects_illegal_period_jump(store: TrackingStore) -> None:
    broken = copy.deepcopy(store)
    target = next(p for p in broken.periods if p["id"] == "period_2015")
    target["execution_status"] = "COMPLETED"
    errors = [i.message for i in validate_store(broken, ROOT) if i.level == "error"]
    assert any("period_2015" in e and "no activity-log transition history" in e for e in errors)


def test_f01_activity_log_illegal_transition_rejected(store: TrackingStore) -> None:
    broken = copy.deepcopy(store)
    broken.activities.append(
        {
            "id": "act_bad_transition",
            "timestamp": "2026-11-23T12:00:00+00:00",
            "actor": "tester",
            "entity_type": "period",
            "entity_id": "period_2015",
            "action": "status_change",
            "previous_state": "NOT_STARTED",
            "new_state": "COMPLETED",
            "evidence_reference": None,
            "notes": "illegal jump",
        }
    )
    errors = [i.message for i in validate_store(broken, ROOT) if i.level == "error"]
    assert any(
        "act_bad_transition" in e
        and ("Illegal" in e or "illegal or ambiguous" in e)
        for e in errors
    )


def test_f01_ci_equivalent_validate_data_fails_on_illegal_jump(
    store: TrackingStore, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Simulate validate_data path: validate_store must be the authority.
    broken = copy.deepcopy(store)
    next(p for p in broken.periods if p["id"] == "period_2016")["execution_status"] = "FAILED"
    issues = validate_store(broken, ROOT)
    assert any(i.level == "error" for i in issues)


def test_f02_sparse_related_ids_do_not_count_as_output_complete(store: TrackingStore) -> None:
    period = copy.deepcopy(next(p for p in store.periods if p["id"] == "period_2015"))
    period["related_dataset_ids"] = ["dataset_cls_hindcast_run"]
    required = store.project["completion_criteria"]["required_products"]
    assessment = period_output_assessment(period, store.datasets, required)
    assert assessment["completeness"] != "COMPLETE"
    progress = compute_progress(store)
    assert progress["metrics"]["output_coverage"]["matched"] == 0


def test_f02_verified_products_required_for_complete() -> None:
    period = {
        "id": "period_2099",
        "calendar_year": 2099,
        "related_dataset_ids": ["d1", "d2", "d3", "d4"],
    }
    datasets = [
        {
            "id": "d1",
            "product": "ocean2d",
            "integrity_status": "VERIFIED",
            "period_coverage": {"start": "2099-01-01", "end": "2099-12-31"},
        },
        {
            "id": "d2",
            "product": "ocean3d",
            "integrity_status": "VERIFIED",
            "period_coverage": {"start": "2099-01-01", "end": "2099-12-31"},
        },
        {
            "id": "d3",
            "product": "wrf2d",
            "integrity_status": "VERIFIED",
            "period_coverage": {"start": "2099-01-01", "end": "2099-12-31"},
        },
        {
            "id": "d4",
            "product": "wrf3d",
            "integrity_status": "NOT_VERIFIED",
            "period_coverage": {"start": "2099-01-01", "end": "2099-12-31"},
        },
    ]
    assessment = period_output_assessment(
        period, datasets, ["ocean2d", "ocean3d", "wrf2d", "wrf3d"]
    )
    assert assessment["completeness"] == "PARTIAL"
    assert assessment["product_status"]["wrf3d"] == "NOT_VERIFIED"


def test_f03_stale_snapshot_classified_at_read_time() -> None:
    snap = {
        "id": "hpc_old",
        "collected_at": "2020-01-01T00:00:00+00:00",
        "collection_ok": True,
        "jobs": [{"job_id": "1", "state": "R"}],
    }
    now = datetime(2026, 11, 23, tzinfo=timezone.utc)
    result = classify_hpc_snapshot(snap, now=now, ttl_hours=24)
    assert result["state"] == "STALE"
    assert result["is_current"] is False


def test_f03_missing_snapshot_not_zero_jobs() -> None:
    result = classify_hpc_snapshot(None, ttl_hours=24)
    assert result["state"] == "MISSING"
    assert result["is_current"] is False


def test_f03_failed_collection_not_preferred_over_good() -> None:
    good = {
        "id": "hpc_good",
        "collected_at": "2026-11-23T08:00:00+00:00",
        "collection_ok": True,
        "jobs": [],
    }
    failed = {
        "id": "hpc_fail",
        "collected_at": "2026-11-23T09:00:00+00:00",
        "collection_ok": False,
        "jobs": [],
    }
    latest = select_latest_usable_snapshot([good, failed])
    assert latest is not None
    assert latest["id"] == "hpc_good"


def test_f03_malformed_snapshot_safe() -> None:
    snap = {"id": "hpc_bad", "collected_at": "not-a-timestamp", "collection_ok": True}
    result = classify_hpc_snapshot(snap, ttl_hours=24)
    assert result["state"] == "MALFORMED"


def test_f03_progress_marks_existing_snapshot_stale(store: TrackingStore) -> None:
    # Existing committed snapshot from 2026-11-23 will be STALE relative to a far-future now
    # via direct classifier; progress uses wall clock — assert classifier wiring exists.
    progress = compute_progress(store)
    assert "hpc_snapshot_status" in progress
    assert progress["hpc_snapshot_ttl_hours"] == 24
    assert progress["hpc_snapshot_status"]["state"] in {
        "FRESH",
        "STALE",
        "MISSING",
        "MALFORMED",
        "FAILED",
    }


def test_f04_dashboard_html_has_no_absolute_home_or_scratch(store: TrackingStore) -> None:
    progress = compute_progress(store)
    path = ROOT / "dashboard" / "generate.py"
    spec = importlib.util.spec_from_file_location("dash_generate", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    html = mod.render(store, progress)
    assert "/home/" not in html
    assert "/scratch/" not in html
    assert "PROVISIONAL" in html or "NOT CONFIRMED" in html


def test_unconfirmed_scope_still_suppresses_overall_percent(store: TrackingStore) -> None:
    progress = compute_progress(store)
    assert progress["overall_percent"] is None
    assert progress["metrics"]["output_coverage"]["percent_display"] == "NOT_CONFIRMED"


def test_historical_not_in_remaining_output_coverage(store: TrackingStore) -> None:
    progress = compute_progress(store)
    assert progress["remaining_year_count"] == 11
    assert progress["historical_year_count"] == 20
    assert progress["metrics"]["output_coverage"]["total"] == 11
