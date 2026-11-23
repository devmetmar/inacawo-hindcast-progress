from __future__ import annotations

import copy
from pathlib import Path

import pytest

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.tracking import (  # noqa: E402
    TrackingStore,
    compute_progress,
    is_year_fully_complete,
    validate_store,
    validate_transition,
)


@pytest.fixture(scope="module")
def store() -> TrackingStore:
    return TrackingStore.load(ROOT)


def test_repo_data_validates(store: TrackingStore) -> None:
    issues = validate_store(store, ROOT)
    errors = [i for i in issues if i.level == "error"]
    assert errors == [], errors


def test_unique_period_ids(store: TrackingStore) -> None:
    ids = [p["id"] for p in store.periods]
    assert len(ids) == len(set(ids))
    assert len(store.periods) == 31


def test_scope_unconfirmed_suppresses_overall_percent(store: TrackingStore) -> None:
    progress = compute_progress(store)
    assert progress["scope_confirmed"] is False
    assert progress["overall_percent"] is None
    assert "PROVISIONAL" in progress["scope_label"]
    for metric in progress["metrics"].values():
        assert metric["percent_display"] == "NOT_CONFIRMED"


def test_execution_transition_rules() -> None:
    validate_transition("execution", "NOT_STARTED", "READY")
    validate_transition("execution", "READY", "RUNNING")
    validate_transition("execution", "RUNNING", "COMPLETED")
    with pytest.raises(ValueError):
        validate_transition("execution", "NOT_STARTED", "COMPLETED")


def test_scientific_transition_rules() -> None:
    validate_transition("scientific", "NOT_VALIDATED", "NEEDS_REVIEW")
    validate_transition("scientific", "NEEDS_REVIEW", "VERIFIED")
    validate_transition("scientific", "VERIFIED", "ACCEPTED")
    with pytest.raises(ValueError):
        validate_transition("scientific", "NOT_VALIDATED", "ACCEPTED")


def test_year_not_complete_without_evidence(store: TrackingStore) -> None:
    period = next(p for p in store.periods if p["id"] == "period_2015")
    assert is_year_fully_complete(period, store.project) in {"NO", "NOT_VERIFIED", "UNKNOWN"}
    assert is_year_fully_complete(period, store.project) != "YES"


def test_failed_run_does_not_accept_year(store: TrackingStore) -> None:
    period = copy.deepcopy(next(p for p in store.periods if p["id"] == "period_2016"))
    period["execution_status"] = "FAILED"
    period["scientific_status"] = "NOT_VALIDATED"
    period["related_run_ids"] = ["run_missing"]
    assert is_year_fully_complete(period, store.project) == "NO"


def test_referential_break_detected(store: TrackingStore) -> None:
    broken = copy.deepcopy(store)
    broken.tasks[0]["depends_on"] = ["task_does_not_exist"]
    issues = validate_store(broken, ROOT)
    assert any("unknown depends_on" in i.message for i in issues if i.level == "error")


def test_date_consistency_for_periods(store: TrackingStore) -> None:
    for period in store.periods:
        assert period["start_date"].startswith(str(period["calendar_year"]))
        assert period["end_date"].startswith(str(period["calendar_year"]))


def test_progress_counts_remaining_years(store: TrackingStore) -> None:
    progress = compute_progress(store)
    assert progress["remaining_year_count"] == 11  # provisional 2015-2025 inclusive
    assert progress["historical_year_count"] == 20
    assert len(progress["remaining_execution_buckets"]["NOT_STARTED"]) == 11
