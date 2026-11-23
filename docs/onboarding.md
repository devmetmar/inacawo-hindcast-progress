# Team Onboarding

1. Clone this repository (tracking only).
2. Read `PROJECT_CHARTER.md`, `OPEN_QUESTIONS.md`, and `docs/security.md`.
3. Ensure access to companion repos and scratch paths as needed for evidence gathering (read-only unless you are the ops owner of those systems).
4. Activate the hindcast Python environment used for validators:

```bash
export PATH="$HOME/inacawo-deps/miniforge3/envs/hindcast/bin:$PATH"
```

5. Ask the project lead to map you to a `member_XX` ID in `data/team.yaml` (placeholders until Q4 is resolved).
6. Practice a dry-run update on a branch:
   - create a task or issue with helpers
   - run `validate_data.py` and `pytest`
7. Do not push to GitHub unless authorized.

## Role cheat sheet (placeholders)

| ID | Focus |
|----|-------|
| member_01 | Scope, acceptance, charter decisions |
| member_02 | HPC runs / SLURM evidence |
| member_03 | Inputs / postprocess / dataset inventory |
| member_04 | Validation methods and review |
