from __future__ import annotations

import copy
from pathlib import Path
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.tracking import TrackingStore, compute_progress, validate_store  # noqa: E402
import importlib.util


def _load_generate():
    path = ROOT / "dashboard" / "generate.py"
    spec = importlib.util.spec_from_file_location("dash_generate", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_retry_run_reference(tmp_path: Path) -> None:
    # Build a minimal store-like pair of run docs and validate retry_of linkage via store clone
    store = TrackingStore.load(ROOT)
    run_a = {
        "id": "run_test_a01",
        "period_id": "period_2015",
        "attempt_number": 1,
        "simulation_start": "2015-01-01",
        "simulation_end": "2015-01-02",
        "owner": "member_02",
        "execution_status": "FAILED",
        "exit_code": 1,
        "log_locations": [],
        "input_dataset_ids": [],
        "output_dataset_ids": [],
        "validation_status": "NOT_VALIDATED",
        "evidence": [{"type": "slurm_job_id", "reference": "999"}],
        "failure_info": "synthetic fixture",
        "retry_of": None,
        "notes": "test fixture",
    }
    run_b = copy.deepcopy(run_a)
    run_b["id"] = "run_test_a02"
    run_b["attempt_number"] = 2
    run_b["execution_status"] = "READY"
    run_b["exit_code"] = None
    run_b["failure_info"] = None
    run_b["retry_of"] = "run_test_a01"
    store.runs = store.runs + [run_a, run_b]
    issues = validate_store(store, ROOT)
    errors = [i.message for i in issues if i.level == "error"]
    assert not any("retry_of" in e for e in errors)


def test_stale_hpc_snapshot_listed() -> None:
    store = TrackingStore.load(ROOT)
    store.hpc_snapshots = [
        {
            "id": "hpc_20200101T000000",
            "collected_at": "2020-01-01T00:00:00+00:00",
            "collector": "test",
            "mode": "manual",
            "collection_ok": True,
            "hpc_user": "PLACEHOLDER_HPC_USER_INTERNAL",
            "commands_used": [],
            "jobs": [],
            "notes": "intentionally stale fixture",
        }
    ]
    progress = compute_progress(store)
    assert progress["latest_hpc_snapshot"]["id"] == "hpc_20200101T000000"
    assert progress["latest_hpc_snapshot"]["collected_at"].startswith("2020-")


def test_dashboard_omits_scope_banner_and_shows_years() -> None:
    store = TrackingStore.load(ROOT)
    progress = compute_progress(store)
    mod = _load_generate()
    html = mod.render(store, progress)
    assert "Hindcast scope:" not in html
    assert "Overall acceptance:" not in html
    assert "overall % suppressed" not in html
    assert "period_2015" not in html  # shows years, not necessarily ids
    assert "2015" in html
    assert "issue_period_discrepancy" in html


def test_completed_job_not_automatic_acceptance() -> None:
    store = TrackingStore.load(ROOT)
    period = next(p for p in store.periods if p["calendar_year"] == 2017)
    period = copy.deepcopy(period)
    period["execution_status"] = "COMPLETED"
    period["scientific_status"] = "NOT_VALIDATED"
    period["related_run_ids"] = []
    from lib.tracking import is_year_fully_complete

    assert is_year_fully_complete(period, store.project) != "YES"
