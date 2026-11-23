## Summary

- 

## Type of change

- [ ] Tracking data update
- [ ] Schema / validator change
- [ ] Dashboard / docs
- [ ] Other

## Evidence

- Evidence references added for any verified/accepted claims: [ ] Yes [ ] N/A
- No secrets / NetCDF / sensitive logs included: [ ] Confirmed

## Validation

```bash
python scripts/validate_data.py
python scripts/compute_progress.py
python dashboard/generate.py
pytest -q
```

- [ ] Local checks passed
