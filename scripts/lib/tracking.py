"""Core loaders, validators, and progress metrics for tracking data."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
SCHEMA_DIR = REPO_ROOT / "schemas"

EXECUTION_TRANSITIONS: dict[str, set[str]] = {
    "NOT_STARTED": {"READY", "BLOCKED", "CANCELLED"},
    "READY": {"RUNNING", "BLOCKED", "CANCELLED", "NOT_STARTED"},
    "RUNNING": {"COMPLETED", "FAILED", "BLOCKED", "CANCELLED"},
    "COMPLETED": {"FAILED"},  # correction only with evidence
    "BLOCKED": {"READY", "RUNNING", "CANCELLED", "FAILED"},
    "FAILED": {"READY", "RUNNING", "CANCELLED"},
    "CANCELLED": {"READY", "NOT_STARTED"},
    "UNKNOWN": {"NOT_STARTED", "READY", "RUNNING", "COMPLETED", "BLOCKED", "FAILED", "CANCELLED"},
}

SCIENTIFIC_TRANSITIONS: dict[str, set[str]] = {
    "NOT_VALIDATED": {"NEEDS_REVIEW", "FAILED_VALIDATION"},
    "NEEDS_REVIEW": {"VERIFIED", "FAILED_VALIDATION", "NOT_VALIDATED"},
    "VERIFIED": {"ACCEPTED", "FAILED_VALIDATION", "NEEDS_REVIEW"},
    "ACCEPTED": set(),  # terminal unless explicit correction workflow
    "FAILED_VALIDATION": {"NEEDS_REVIEW", "NOT_VALIDATED"},
    "UNKNOWN": {"NOT_VALIDATED", "NEEDS_REVIEW", "VERIFIED", "ACCEPTED", "FAILED_VALIDATION"},
}

ENTITY_DIRS = {
    "period": DATA_DIR / "periods",
    "run": DATA_DIR / "runs",
    "dataset": DATA_DIR / "datasets",
    "task": DATA_DIR / "tasks",
    "issue": DATA_DIR / "issues",
    "validation": DATA_DIR / "validations",
    "activity": DATA_DIR / "activity_log",
    "hpc_snapshot": DATA_DIR / "hpc_snapshots",
}

SCHEMA_MAP = {
    "project": "project.schema.json",
    "team": "team.schema.json",
    "workflow_stages": "workflow_stages.schema.json",
    "period": "period.schema.json",
    "run": "run.schema.json",
    "dataset": "dataset.schema.json",
    "task": "task.schema.json",
    "issue": "issue.schema.json",
    "validation": "validation.schema.json",
    "activity": "activity.schema.json",
    "hpc_snapshot": "hpc_snapshot.schema.json",
}


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


class _QuotedSafeDumper(yaml.SafeDumper):
    """Dump strings so YAML 1.1 boolean-looking values stay strings."""


def _represent_str(dumper: yaml.SafeDumper, data: str):
    if data in {"YES", "NO", "ON", "OFF", "TRUE", "FALSE", "True", "False"}:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style='"')
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_QuotedSafeDumper.add_representer(str, _represent_str)


def dump_yaml(doc: Any) -> str:
    return yaml.dump(doc, Dumper=_QuotedSafeDumper, sort_keys=False, allow_unicode=True)


def load_schema(name: str) -> dict[str, Any]:
    path = SCHEMA_DIR / SCHEMA_MAP[name]
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def parse_iso_date(value: str) -> date:
    return date.fromisoformat(value)


def validate_transition(axis: str, previous: str, new: str) -> None:
    table = EXECUTION_TRANSITIONS if axis == "execution" else SCIENTIFIC_TRANSITIONS
    if previous == new:
        return
    allowed = table.get(previous)
    if allowed is None:
        raise ValueError(f"Unknown {axis} status: {previous}")
    if new not in allowed:
        raise ValueError(
            f"Illegal {axis} transition {previous} -> {new}; allowed={sorted(allowed)}"
        )


@dataclass
class ValidationIssue:
    level: str
    message: str


@dataclass
class TrackingStore:
    project: dict[str, Any] = field(default_factory=dict)
    team: dict[str, Any] = field(default_factory=dict)
    workflow_stages: dict[str, Any] = field(default_factory=dict)
    periods: list[dict[str, Any]] = field(default_factory=list)
    runs: list[dict[str, Any]] = field(default_factory=list)
    datasets: list[dict[str, Any]] = field(default_factory=list)
    tasks: list[dict[str, Any]] = field(default_factory=list)
    issues: list[dict[str, Any]] = field(default_factory=list)
    validations: list[dict[str, Any]] = field(default_factory=list)
    activities: list[dict[str, Any]] = field(default_factory=list)
    hpc_snapshots: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def load(cls, root: Path | None = None) -> "TrackingStore":
        root = root or REPO_ROOT
        data = root / "data"
        store = cls()
        store.project = load_yaml(data / "project.yaml")
        store.team = load_yaml(data / "team.yaml")
        store.workflow_stages = load_yaml(data / "workflow_stages.yaml")
        store.periods = _load_dir(data / "periods")
        store.runs = _load_dir(data / "runs")
        store.datasets = _load_dir(data / "datasets")
        store.tasks = _load_dir(data / "tasks")
        store.issues = _load_dir(data / "issues")
        store.validations = _load_dir(data / "validations")
        store.activities = _load_dir(data / "activity_log")
        store.hpc_snapshots = _load_dir(data / "hpc_snapshots")
        return store

    def index_by_id(self) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for collection in (
            self.periods,
            self.runs,
            self.datasets,
            self.tasks,
            self.issues,
            self.validations,
            self.activities,
            self.hpc_snapshots,
        ):
            for item in collection:
                out[item["id"]] = item
        out[self.project["id"]] = self.project
        for member in self.team.get("members", []):
            out[member["id"]] = member
        for stage in self.workflow_stages.get("stages", []):
            out[stage["id"]] = stage
        return out


def _load_dir(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    items: list[dict[str, Any]] = []
    for file in sorted(path.glob("*.yaml")):
        if file.name == ".gitkeep":
            continue
        doc = load_yaml(file)
        if doc is None:
            continue
        if not isinstance(doc, dict):
            raise ValueError(f"Expected mapping in {file}")
        items.append(doc)
    return items


def validate_store(store: TrackingStore, root: Path | None = None) -> list[ValidationIssue]:
    root = root or REPO_ROOT
    issues: list[ValidationIssue] = []

    schema_targets = [
        ("project", store.project),
        ("team", store.team),
        ("workflow_stages", store.workflow_stages),
    ]
    for name, doc in schema_targets:
        issues.extend(_schema_issues(name, doc, loc=name))

    typed = [
        ("period", store.periods),
        ("run", store.runs),
        ("dataset", store.datasets),
        ("task", store.tasks),
        ("issue", store.issues),
        ("validation", store.validations),
        ("activity", store.activities),
        ("hpc_snapshot", store.hpc_snapshots),
    ]
    for name, docs in typed:
        for doc in docs:
            issues.extend(_schema_issues(name, doc, loc=doc.get("id", name)))

    # Unique IDs
    seen: dict[str, str] = {}
    for entity_id, entity in store.index_by_id().items():
        if entity_id in seen:
            issues.append(
                ValidationIssue(
                    "error",
                    f"Duplicate id {entity_id} (also in {seen[entity_id]})",
                )
            )
        else:
            kind = entity.get("id", entity_id)
            seen[entity_id] = str(kind)

    member_ids = {m["id"] for m in store.team.get("members", [])}
    stage_ids = {s["id"] for s in store.workflow_stages.get("stages", [])}
    period_ids = {p["id"] for p in store.periods}
    run_ids = {r["id"] for r in store.runs}
    dataset_ids = {d["id"] for d in store.datasets}
    task_ids = {t["id"] for t in store.tasks}

    for mid in store.project.get("team_member_ids", []):
        if mid not in member_ids:
            issues.append(ValidationIssue("error", f"project.team_member_ids unknown: {mid}"))
    if store.project.get("project_owner") not in member_ids:
        issues.append(
            ValidationIssue(
                "error",
                f"project.project_owner unknown: {store.project.get('project_owner')}",
            )
        )

    for period in store.periods:
        _check_member(period.get("owner"), member_ids, period["id"], issues)
        _check_member(period.get("reviewer"), member_ids, period["id"], issues)
        try:
            start = parse_iso_date(period["start_date"])
            end = parse_iso_date(period["end_date"])
            if end < start:
                issues.append(
                    ValidationIssue("error", f"{period['id']}: end_date before start_date")
                )
            if period["calendar_year"] not in (start.year, end.year) and start.year != end.year:
                pass
            if start.year != period["calendar_year"] or end.year != period["calendar_year"]:
                issues.append(
                    ValidationIssue(
                        "error",
                        f"{period['id']}: dates must fall within calendar_year "
                        f"{period['calendar_year']}",
                    )
                )
        except Exception as exc:  # noqa: BLE001
            issues.append(ValidationIssue("error", f"{period['id']}: date error: {exc}"))
        for rid in period.get("related_run_ids", []):
            if rid not in run_ids:
                issues.append(
                    ValidationIssue("error", f"{period['id']}: unknown related_run_ids {rid}")
                )
        for did in period.get("related_dataset_ids", []):
            if did not in dataset_ids:
                issues.append(
                    ValidationIssue(
                        "error", f"{period['id']}: unknown related_dataset_ids {did}"
                    )
                )

    for run in store.runs:
        if run["period_id"] not in period_ids:
            issues.append(
                ValidationIssue("error", f"{run['id']}: unknown period_id {run['period_id']}")
            )
        _check_member(run.get("owner"), member_ids, run["id"], issues)
        try:
            if parse_iso_date(run["simulation_end"]) < parse_iso_date(run["simulation_start"]):
                issues.append(
                    ValidationIssue("error", f"{run['id']}: simulation_end before start")
                )
        except Exception as exc:  # noqa: BLE001
            issues.append(ValidationIssue("error", f"{run['id']}: date error: {exc}"))
        for did in run.get("input_dataset_ids", []) + run.get("output_dataset_ids", []):
            if did not in dataset_ids:
                issues.append(ValidationIssue("error", f"{run['id']}: unknown dataset {did}"))
        if run.get("retry_of") and run["retry_of"] not in run_ids:
            issues.append(
                ValidationIssue("error", f"{run['id']}: unknown retry_of {run['retry_of']}")
            )
        # Completed execution should not be treated as scientifically accepted implicitly
        if run["execution_status"] == "COMPLETED" and not run.get("evidence"):
            issues.append(
                ValidationIssue(
                    "warning",
                    f"{run['id']}: COMPLETED without evidence refs (reported only)",
                )
            )

    for task in store.tasks:
        if task["workflow_stage_id"] not in stage_ids:
            issues.append(
                ValidationIssue(
                    "error",
                    f"{task['id']}: unknown workflow_stage_id {task['workflow_stage_id']}",
                )
            )
        _check_member(task.get("owner"), member_ids, task["id"], issues)
        _check_member(task.get("reviewer"), member_ids, task["id"], issues)
        for dep in task.get("depends_on", []):
            if dep not in task_ids:
                issues.append(ValidationIssue("error", f"{task['id']}: unknown depends_on {dep}"))

    for issue in store.issues:
        _check_member(issue.get("owner"), member_ids, issue["id"], issues)
        for tid in issue.get("related_task_ids", []):
            if tid not in task_ids:
                issues.append(
                    ValidationIssue("error", f"{issue['id']}: unknown related_task_ids {tid}")
                )
        for rid in issue.get("related_run_ids", []):
            if rid not in run_ids:
                issues.append(
                    ValidationIssue("error", f"{issue['id']}: unknown related_run_ids {rid}")
                )
        for pid in issue.get("related_period_ids", []):
            if pid not in period_ids:
                issues.append(
                    ValidationIssue(
                        "error", f"{issue['id']}: unknown related_period_ids {pid}"
                    )
                )

    for val in store.validations:
        _check_member(val.get("reviewer"), member_ids, val["id"], issues)
        if val.get("dataset_id") and val["dataset_id"] not in dataset_ids:
            issues.append(
                ValidationIssue("error", f"{val['id']}: unknown dataset_id {val['dataset_id']}")
            )
        if val.get("run_id") and val["run_id"] not in run_ids:
            issues.append(
                ValidationIssue("error", f"{val['id']}: unknown run_id {val['run_id']}")
            )
        if val.get("period_id") and val["period_id"] not in period_ids:
            issues.append(
                ValidationIssue("error", f"{val['id']}: unknown period_id {val['period_id']}")
            )
        if val.get("pass_fail_status") == "PASS" and not val.get("threshold_definition"):
            issues.append(
                ValidationIssue(
                    "warning",
                    f"{val['id']}: PASS without threshold_definition "
                    "(thresholds must be owner-supplied)",
                )
            )

    # Scope consistency
    if store.project.get("scope", {}).get("confirmed") is None:
        for period in store.periods:
            if period.get("scope_basis") == "confirmed":
                issues.append(
                    ValidationIssue(
                        "error",
                        f"{period['id']}: scope_basis=confirmed but project.scope.confirmed is null",
                    )
                )

    return issues


def _schema_issues(name: str, doc: dict[str, Any], loc: str) -> list[ValidationIssue]:
    schema = load_schema(name)
    validator = Draft202012Validator(schema)
    out: list[ValidationIssue] = []
    for err in sorted(validator.iter_errors(doc), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in err.path) or "(root)"
        out.append(ValidationIssue("error", f"{loc} schema: {path}: {err.message}"))
    return out


def _check_member(
    member_id: str | None,
    member_ids: set[str],
    loc: str,
    issues: list[ValidationIssue],
) -> None:
    if member_id is None:
        return
    if member_id not in member_ids:
        issues.append(ValidationIssue("error", f"{loc}: unknown member {member_id}"))


def is_year_fully_complete(period: dict[str, Any], project: dict[str, Any]) -> str:
    """Return YES / NO / UNKNOWN / NOT_VERIFIED for a period."""
    criteria = project.get("completion_criteria", {})
    if period.get("fully_complete") in {"YES", "NO", "UNKNOWN", "NOT_VERIFIED"}:
        # Prefer explicit field but recompute when YES claimed without evidence layers
        explicit = period["fully_complete"]
    else:
        explicit = "UNKNOWN"

    checks: list[bool | None] = []
    if criteria.get("require_execution_verified"):
        if period.get("execution_status") == "COMPLETED":
            # Without linked verified runs, treat as NOT_VERIFIED rather than YES
            checks.append(None if not period.get("related_run_ids") else True)
        elif period.get("execution_status") in {"NOT_STARTED", "READY", "RUNNING", "FAILED", "BLOCKED", "CANCELLED"}:
            checks.append(False)
        else:
            checks.append(None)

    if criteria.get("require_outputs_verified"):
        # Dataset links required; absence => NOT_VERIFIED
        if not period.get("related_dataset_ids"):
            checks.append(None)
        else:
            checks.append(None)  # integrity not auto-verified here

    if criteria.get("require_validations_verified"):
        if period.get("scientific_status") in {"VERIFIED", "ACCEPTED"}:
            checks.append(True)
        elif period.get("scientific_status") in {"FAILED_VALIDATION"}:
            checks.append(False)
        else:
            checks.append(None)

    if criteria.get("require_human_acceptance"):
        if period.get("scientific_status") == "ACCEPTED":
            checks.append(True)
        else:
            checks.append(False if period.get("scientific_status") != "UNKNOWN" else None)

    if any(c is False for c in checks):
        return "NO"
    if any(c is None for c in checks):
        return "NOT_VERIFIED" if explicit != "UNKNOWN" else "UNKNOWN"
    if checks and all(c is True for c in checks):
        return "YES"
    return explicit


def compute_progress(store: TrackingStore) -> dict[str, Any]:
    scope = store.project.get("scope", {})
    confirmed = scope.get("confirmed")
    provisional = scope.get("provisional", {})

    remaining_periods = [p for p in store.periods if p.get("stream") == "remaining_internal"]
    historical_periods = [p for p in store.periods if p.get("stream") == "historical_baseline"]

    def bucket(periods: list[dict[str, Any]]) -> dict[str, list[int]]:
        out = {
            "NOT_STARTED": [],
            "READY": [],
            "RUNNING": [],
            "COMPLETED": [],
            "FAILED": [],
            "BLOCKED": [],
            "CANCELLED": [],
            "UNKNOWN": [],
        }
        for p in periods:
            status = p.get("execution_status", "UNKNOWN")
            out.setdefault(status, [])
            out[status].append(p["calendar_year"])
        return out

    rem_buckets = bucket(remaining_periods)
    hist_buckets = bucket(historical_periods)

    fully_complete = {
        p["calendar_year"]: is_year_fully_complete(p, store.project) for p in remaining_periods
    }
    accepted_years = [
        y for y, v in fully_complete.items() if v == "YES"
    ]

    open_issues = [i for i in store.issues if i.get("status") in {"OPEN", "IN_PROGRESS", "BLOCKED"}]
    active_runs = [
        r for r in store.runs if r.get("execution_status") in {"READY", "RUNNING"}
    ]

    workload: dict[str, int] = {m["id"]: 0 for m in store.team.get("members", [])}
    for collection in (store.tasks, store.issues, store.periods, store.runs):
        for item in collection:
            owner = item.get("owner")
            if owner in workload:
                status = item.get("status") or item.get("execution_status")
                if status in {
                    "NOT_STARTED",
                    "READY",
                    "RUNNING",
                    "BLOCKED",
                    "OPEN",
                    "IN_PROGRESS",
                    "NEEDS_REVIEW",
                    "FAILED",
                }:
                    workload[owner] += 1

    latest_snapshot = None
    if store.hpc_snapshots:
        latest_snapshot = max(store.hpc_snapshots, key=lambda s: s.get("collected_at", ""))

    result = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "scope_confirmed": confirmed is not None,
        "scope_label": "CONFIRMED" if confirmed is not None else "PROVISIONAL / NOT CONFIRMED",
        "provisional_remaining": provisional.get("remaining_claimed"),
        "provisional_historical": provisional.get("historical_claimed"),
        "confirmed_scope": confirmed,
        "remaining_year_count": len(remaining_periods),
        "historical_year_count": len(historical_periods),
        "remaining_execution_buckets": rem_buckets,
        "historical_execution_buckets": hist_buckets,
        "remaining_fully_complete": fully_complete,
        "accepted_complete_years": accepted_years,
        "metrics": {
            "execution_coverage": _coverage(
                remaining_periods,
                lambda p: p.get("execution_status") == "COMPLETED",
                confirmed is not None,
            ),
            "output_coverage": _coverage(
                remaining_periods,
                lambda p: bool(p.get("related_dataset_ids")),
                confirmed is not None,
            ),
            "validation_coverage": _coverage(
                remaining_periods,
                lambda p: p.get("scientific_status") in {"VERIFIED", "ACCEPTED"},
                confirmed is not None,
            ),
            "acceptance_coverage": _coverage(
                remaining_periods,
                lambda p: is_year_fully_complete(p, store.project) == "YES",
                confirmed is not None,
            ),
        },
        "workflow_stages": store.workflow_stages.get("stages", []),
        "open_issues": open_issues,
        "active_runs": active_runs,
        "workload": workload,
        "latest_hpc_snapshot": latest_snapshot,
        "overall_percent": None
        if confirmed is None
        else _percent(len(accepted_years), len(remaining_periods)),
    }
    return result


def _coverage(
    periods: list[dict[str, Any]],
    predicate,
    scope_confirmed: bool,
) -> dict[str, Any]:
    total = len(periods)
    matched = sum(1 for p in periods if predicate(p))
    return {
        "matched": matched,
        "total": total,
        "ratio": None if total == 0 else matched / total,
        "percent_display": "NOT_CONFIRMED"
        if not scope_confirmed
        else (None if total == 0 else round(100.0 * matched / total, 2)),
        "note": "Denominator provisional until scope.confirmed is set"
        if not scope_confirmed
        else None,
    }


def _percent(num: int, den: int) -> float | None:
    if den == 0:
        return None
    return round(100.0 * num / den, 2)
