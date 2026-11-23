# Security and Data Protection

## Never commit

- Credentials, passwords, API keys, Vault tokens, SSH private keys
- CDS/CMEMS credential files
- Large scientific outputs (`*.nc`, GRIB, binaries such as `coawstM`)
- Full HPC logs that may contain sensitive paths or tokens

## Preferred practice

- Store **path references** and checksum/manifest pointers in YAML
- Use member IDs (`member_01` …) until a privacy-approved roster is provided
- Keep secrets in existing operator credential locations outside this repo

## Repository visibility

Remote is currently a **public** GitHub repository. Assume all committed content is world-readable.

## `.gitignore`

Blocks common scientific/secret patterns. Review `git status` before every commit.

## Incident response

If a secret is committed: rotate the credential immediately, remove from history with owner authorization, and document the incident in an issue record (without re-committing the secret).
