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

TASK_TRANSITIONS: dict[str, set[str]] = {
    "NOT_STARTED": {"READY", "BLOCKED", "CANCELLED"},
    "READY": {"RUNNING", "BLOCKED", "CANCELLED", "NOT_STARTED", "NEEDS_REVIEW"},
    "RUNNING": {"COMPLETED", "FAILED", "BLOCKED", "CANCELLED", "NEEDS_REVIEW"},
    "COMPLETED": set(),
    "BLOCKED": {"READY", "RUNNING", "CANCELLED", "FAILED"},
    "FAILED": {"READY", "RUNNING", "CANCELLED"},
    "CANCELLED": {"READY", "NOT_STARTED"},
    "NEEDS_REVIEW": {"COMPLETED", "FAILED", "READY", "RUNNING"},
}

ISSUE_TRANSITIONS: dict[str, set[str]] = {
    "OPEN": {"IN_PROGRESS", "BLOCKED", "RESOLVED", "CLOSED"},
    "IN_PROGRESS": {"BLOCKED", "RESOLVED", "CLOSED", "OPEN"},
    "BLOCKED": {"IN_PROGRESS", "OPEN", "RESOLVED", "CLOSED"},
    "RESOLVED": {"CLOSED", "OPEN"},
    "CLOSED": set(),
}

# Statuses that may exist without transition history (initial / inventory).
BOOTSTRAP_EXECUTION = frozenset({"NOT_STARTED", "UNKNOWN"})
BOOTSTRAP_SCIENTIFIC = frozenset({"NOT_VALIDATED", "UNKNOWN"})
BOOTSTRAP_TASK = frozenset({"NOT_STARTED", "READY"})
BOOTSTRAP_ISSUE = frozenset({"OPEN"})
BOOTSTRAP_STAGE = frozenset({"NOT_STARTED", "UNKNOWN", "READY"})

DEFAULT_HPC_SNAPSHOT_TTL_HOURS = 24.0

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


def _transition_table(axis: str) -> dict[str, set[str]]:
    tables = {
        "execution": EXECUTION_TRANSITIONS,
        "scientific": SCIENTIFIC_TRANSITIONS,
        "task": TASK_TRANSITIONS,
        "issue": ISSUE_TRANSITIONS,
        "stage": EXECUTION_TRANSITIONS,  # reuse execution vocabulary for stages
    }
    if axis not in tables:
        raise ValueError(f"Unknown transition axis: {axis}")
    return tables[axis]


def validate_transition(axis: str, previous: str, new: str) -> None:
    table = _transition_table(axis)
    if previous == new:
        return
    allowed = table.get(previous)
    if allowed is None:
        raise ValueError(f"Unknown {axis} status: {previous}")
    if new not in allowed:
        raise ValueError(
            f"Illegal {axis} transition {previous} -> {new}; allowed={sorted(allowed)}"
        )


def infer_transition_axis(previous: str, new: str) -> str | None:
    """Return axis name if exactly one table accepts the transition."""
    matches: list[str] = []
    for axis in ("execution", "scientific", "task", "issue"):
        table = _transition_table(axis)
        if previous in table and (previous == new or new in table[previous]):
            matches.append(axis)
    if len(matches) == 1:
        return matches[0]
    if "execution" in matches and previous in EXECUTION_TRANSITIONS:
        # Prefer execution when ambiguous with stage vocabulary.
        return "execution"
    return None


def parse_datetime(value: str) -> datetime:
    """Parse ISO-8601 timestamps; naive values are treated as UTC."""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        from datetime import timezone

        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def get_hpc_ttl_hours(project: dict[str, Any]) -> float:
    raw = project.get("hpc_snapshot_ttl_hours")
    if raw is None:
        raw = (project.get("metadata") or {}).get("hpc_snapshot_ttl_hours")
    if raw is None:
        return DEFAULT_HPC_SNAPSHOT_TTL_HOURS
    return float(raw)


def classify_hpc_snapshot(
    snapshot: dict[str, Any] | None,
    *,
    now: datetime | None = None,
    ttl_hours: float = DEFAULT_HPC_SNAPSHOT_TTL_HOURS,
) -> dict[str, Any]:
    """Classify snapshot as MISSING / MALFORMED / FAILED / STALE / FRESH."""
    if snapshot is None:
        return {
            "state": "MISSING",
            "collected_at": None,
            "age_seconds": None,
            "ttl_hours": ttl_hours,
            "is_current": False,
        }
    if snapshot.get("collection_ok") is False:
        return {
            "state": "FAILED",
            "collected_at": snapshot.get("collected_at"),
            "age_seconds": None,
            "ttl_hours": ttl_hours,
            "is_current": False,
            "snapshot_id": snapshot.get("id"),
        }
    collected_raw = snapshot.get("collected_at")
    if not collected_raw:
        return {
            "state": "MALFORMED",
            "collected_at": None,
            "age_seconds": None,
            "ttl_hours": ttl_hours,
            "is_current": False,
            "snapshot_id": snapshot.get("id"),
        }
    try:
        collected = parse_datetime(str(collected_raw))
    except Exception:  # noqa: BLE001
        return {
            "state": "MALFORMED",
            "collected_at": collected_raw,
            "age_seconds": None,
            "ttl_hours": ttl_hours,
            "is_current": False,
            "snapshot_id": snapshot.get("id"),
        }
    now = now or datetime.now().astimezone()
    age = (now - collected).total_seconds()
    state = "STALE" if age > ttl_hours * 3600.0 else "FRESH"
    return {
        "state": state,
        "collected_at": collected.isoformat(),
        "age_seconds": age,
        "ttl_hours": ttl_hours,
        "is_current": state == "FRESH",
        "snapshot_id": snapshot.get("id"),
    }


def select_latest_usable_snapshot(
    snapshots: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Prefer latest successful snapshot; ignore failed collection records."""
    usable = [s for s in snapshots if s.get("collection_ok", True) is not False]
    if not usable:
        return None
    return max(usable, key=lambda s: s.get("collected_at") or "")


def dataset_covers_year(dataset: dict[str, Any], year: int) -> str:
    """Return YES / NO / UNKNOWN for whether dataset coverage includes year."""
    cov = dataset.get("period_coverage") or {}
    start = cov.get("start")
    end = cov.get("end")
    if not start or not end:
        return "UNKNOWN"
    try:
        start_y = parse_iso_date(str(start)[:10]).year
        end_y = parse_iso_date(str(end)[:10]).year
    except Exception:  # noqa: BLE001
        return "UNKNOWN"
    if start_y <= year <= end_y:
        return "YES"
    return "NO"


def period_output_assessment(
    period: dict[str, Any],
    datasets: list[dict[str, Any]],
    required_products: list[str],
) -> dict[str, Any]:
    """Evidence-based output assessment for one period (no invented thresholds)."""
    by_id = {d["id"]: d for d in datasets}
    related_ids = list(period.get("related_dataset_ids") or [])
    related = [by_id[i] for i in related_ids if i in by_id]
    year = int(period["calendar_year"])

    product_status: dict[str, str] = {}
    for product in required_products:
        candidates = [d for d in related if d.get("product") == product]
        if not candidates:
            product_status[product] = "MISSING"
            continue
        verified = []
        unverified = []
        for d in candidates:
            cover = dataset_covers_year(d, year)
            if cover == "NO":
                continue
            if d.get("integrity_status") == "VERIFIED" and cover == "YES":
                verified.append(d)
            else:
                unverified.append(d)
        if verified:
            product_status[product] = "VERIFIED"
        elif unverified:
            product_status[product] = "NOT_VERIFIED"
        else:
            # Related datasets exist for product but none cover this year.
            same_product = [d for d in related if d.get("product") == product]
            product_status[product] = "NOT_VERIFIED" if same_product else "MISSING"

    verified_count = sum(1 for s in product_status.values() if s == "VERIFIED")
    missing_count = sum(1 for s in product_status.values() if s == "MISSING")
    unverified_count = sum(1 for s in product_status.values() if s == "NOT_VERIFIED")
    if not required_products:
        completeness = "UNKNOWN"
    elif verified_count == len(required_products):
        completeness = "COMPLETE"
    elif verified_count == 0 and missing_count == len(required_products):
        completeness = "MISSING"
    elif verified_count > 0:
        completeness = "PARTIAL"
    else:
        completeness = "NOT_VERIFIED"

    return {
        "completeness": completeness,
        "product_status": product_status,
        "related_dataset_count": len(related),
        "required_products": list(required_products),
    }


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
        for did in task.get("related_dataset_ids", []) or []:
            if did not in dataset_ids:
                issues.append(
                    ValidationIssue(
                        "error", f"{task['id']}: unknown related_dataset_ids {did}"
                    )
                )
        for pid in task.get("related_period_ids", []) or []:
            if pid not in period_ids:
                issues.append(
                    ValidationIssue(
                        "error", f"{task['id']}: unknown related_period_ids {pid}"
                    )
                )

    for dataset in store.datasets:
        _check_member(dataset.get("owner"), member_ids, dataset["id"], issues)
        for tid in dataset.get("related_task_ids", []) or []:
            if tid not in task_ids:
                issues.append(
                    ValidationIssue(
                        "error", f"{dataset['id']}: unknown related_task_ids {tid}"
                    )
                )

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

    # F-01: enforce status transitions via activity-log ledger + bootstrap rules
    issues.extend(_validate_status_transitions(store))

    return issues


def _activity_status_events(
    store: TrackingStore, entity_id: str
) -> list[dict[str, Any]]:
    events = [
        a
        for a in store.activities
        if a.get("entity_id") == entity_id
        and a.get("previous_state")
        and a.get("new_state")
    ]
    return sorted(events, key=lambda a: a.get("timestamp") or "")


def _validate_status_transitions(store: TrackingStore) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    # Validate every recorded previous->new step in the activity log.
    for act in store.activities:
        prev = act.get("previous_state")
        new = act.get("new_state")
        if not prev or not new:
            continue
        axis = infer_transition_axis(str(prev), str(new))
        if axis is None:
            issues.append(
                ValidationIssue(
                    "error",
                    f"{act.get('id')}: illegal or ambiguous status transition "
                    f"{prev} -> {new}",
                )
            )
            continue
        try:
            validate_transition(axis, str(prev), str(new))
        except ValueError as exc:
            issues.append(ValidationIssue("error", f"{act.get('id')}: {exc}"))

    def require_history(
        entity_id: str,
        current: str | None,
        bootstrap: frozenset[str],
        axis: str,
        label: str,
    ) -> None:
        if current is None or current in bootstrap:
            return
        events = _activity_status_events(store, entity_id)
        if not events:
            issues.append(
                ValidationIssue(
                    "error",
                    f"{entity_id}: {label} status {current} is not a bootstrap "
                    f"state and has no activity-log transition history",
                )
            )
            return
        # Each step already validated above; ensure final state matches current.
        if events[-1].get("new_state") != current:
            issues.append(
                ValidationIssue(
                    "error",
                    f"{entity_id}: {label} status {current} does not match latest "
                    f"activity transition result {events[-1].get('new_state')}",
                )
            )
            return
        # Ensure a legal path exists from a bootstrap state through the chain.
        cursor = events[0].get("previous_state")
        if cursor not in bootstrap and cursor != current:
            # Allow chains that start mid-flight only if first previous is known
            # on the axis table (e.g. READY->RUNNING); still require first previous
            # to be reachable conceptually — require bootstrap or UNKNOWN entry.
            if cursor not in _transition_table(axis):
                issues.append(
                    ValidationIssue(
                        "error",
                        f"{entity_id}: {label} transition history starts at unknown "
                        f"status {cursor}",
                    )
                )

    for period in store.periods:
        require_history(
            period["id"],
            period.get("execution_status"),
            BOOTSTRAP_EXECUTION,
            "execution",
            "execution",
        )
        require_history(
            period["id"],
            period.get("scientific_status"),
            BOOTSTRAP_SCIENTIFIC,
            "scientific",
            "scientific",
        )

    for run in store.runs:
        require_history(
            run["id"],
            run.get("execution_status"),
            BOOTSTRAP_EXECUTION,
            "execution",
            "execution",
        )

    for task in store.tasks:
        require_history(
            task["id"],
            task.get("status"),
            BOOTSTRAP_TASK,
            "task",
            "task",
        )

    for issue in store.issues:
        require_history(
            issue["id"],
            issue.get("status"),
            BOOTSTRAP_ISSUE,
            "issue",
            "issue",
        )

    for stage in store.workflow_stages.get("stages", []):
        require_history(
            stage["id"],
            stage.get("status"),
            BOOTSTRAP_STAGE,
            "stage",
            "stage",
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


def is_year_fully_complete(
    period: dict[str, Any],
    project: dict[str, Any],
    datasets: list[dict[str, Any]] | None = None,
) -> str:
    """Return YES / NO / UNKNOWN / NOT_VERIFIED for a period."""
    criteria = project.get("completion_criteria", {})
    if period.get("fully_complete") in {"YES", "NO", "UNKNOWN", "NOT_VERIFIED"}:
        explicit = period["fully_complete"]
    else:
        explicit = "UNKNOWN"

    checks: list[bool | None] = []
    if criteria.get("require_execution_verified"):
        if period.get("execution_status") == "COMPLETED":
            checks.append(None if not period.get("related_run_ids") else True)
        elif period.get("execution_status") in {
            "NOT_STARTED",
            "READY",
            "RUNNING",
            "FAILED",
            "BLOCKED",
            "CANCELLED",
        }:
            checks.append(False)
        else:
            checks.append(None)

    if criteria.get("require_outputs_verified"):
        required = list(criteria.get("required_products") or [])
        assessment = period_output_assessment(period, datasets or [], required)
        if assessment["completeness"] == "COMPLETE":
            checks.append(True)
        elif assessment["completeness"] in {"MISSING", "PARTIAL"}:
            checks.append(False)
        else:
            checks.append(None)

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

    required_products = list(
        (store.project.get("completion_criteria") or {}).get("required_products") or []
    )
    output_assessments = {
        p["calendar_year"]: period_output_assessment(p, store.datasets, required_products)
        for p in remaining_periods
    }
    fully_complete = {
        p["calendar_year"]: is_year_fully_complete(p, store.project, store.datasets)
        for p in remaining_periods
    }
    accepted_years = [y for y, v in fully_complete.items() if v == "YES"]

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

    ttl_hours = get_hpc_ttl_hours(store.project)
    latest_snapshot = select_latest_usable_snapshot(store.hpc_snapshots)
    hpc_classification = classify_hpc_snapshot(
        latest_snapshot, ttl_hours=ttl_hours
    )

    output_complete_years = [
        y
        for y, a in output_assessments.items()
        if a["completeness"] == "COMPLETE"
    ]
    output_partial_years = [
        y
        for y, a in output_assessments.items()
        if a["completeness"] == "PARTIAL"
    ]
    output_unverified_years = [
        y
        for y, a in output_assessments.items()
        if a["completeness"] == "NOT_VERIFIED"
    ]

    by_product: dict[str, dict[str, int]] = {
        product: {"verified": 0, "not_verified": 0, "missing": 0, "total": len(remaining_periods)}
        for product in required_products
    }
    for assessment in output_assessments.values():
        for product, status in assessment["product_status"].items():
            if product not in by_product:
                continue
            if status == "VERIFIED":
                by_product[product]["verified"] += 1
            elif status == "NOT_VERIFIED":
                by_product[product]["not_verified"] += 1
            else:
                by_product[product]["missing"] += 1

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
        "output_assessments": output_assessments,
        "metrics": {
            "execution_coverage": _coverage(
                remaining_periods,
                lambda p: p.get("execution_status") == "COMPLETED",
                confirmed is not None,
            ),
            "output_coverage": {
                **_coverage(
                    remaining_periods,
                    lambda p: output_assessments[p["calendar_year"]]["completeness"]
                    == "COMPLETE",
                    confirmed is not None,
                ),
                "partial_years": output_partial_years,
                "not_verified_years": output_unverified_years,
                "complete_years": output_complete_years,
                "by_product": by_product,
                "definition": (
                    "Period counts as output-complete only when every configured "
                    "required_product has a related dataset with integrity_status=VERIFIED "
                    "whose period_coverage includes that calendar year. "
                    "Sparse links or unverified integrity do not count."
                ),
            },
            "validation_coverage": _coverage(
                remaining_periods,
                lambda p: p.get("scientific_status") in {"VERIFIED", "ACCEPTED"},
                confirmed is not None,
            ),
            "acceptance_coverage": _coverage(
                remaining_periods,
                lambda p: is_year_fully_complete(p, store.project, store.datasets) == "YES",
                confirmed is not None,
            ),
        },
        "workflow_stages": store.workflow_stages.get("stages", []),
        "open_issues": open_issues,
        "active_runs": active_runs,
        "workload": workload,
        "latest_hpc_snapshot": latest_snapshot,
        "hpc_snapshot_status": hpc_classification,
        "hpc_snapshot_ttl_hours": ttl_hours,
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
