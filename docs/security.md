# Security and Data Protection

## Never commit

- Credentials, passwords, API keys, Vault tokens, SSH private keys
- CDS/CMEMS credential files
- Large scientific outputs (`*.nc`, GRIB, binaries such as `coawstM`)
- Full HPC logs that may contain sensitive paths or tokens

## Preferred practice

- Store **portable path placeholders** (`$CAWO_HINDCAST_BASE`, `$SCRATCH_HISTORICAL`, `$HOME/...`) rather than absolute `/home/...` or `/scratch/...` paths
- Store checksum/manifest pointers in YAML, not file contents
- Use member IDs (`member_01` …) until a privacy-approved roster is provided
- Keep secrets in existing operator credential locations outside this repo

## Repository visibility

Remote is currently a **public** GitHub repository. Assume all committed content is world-readable.

**History note:** Cleaning the working tree does not remove previously committed absolute paths from Git history. History rewrite/force-push requires explicit owner authorization and is out of scope for ordinary tracking updates.

## `.gitignore`

Blocks common scientific/secret patterns. Review `git status` before every commit.

## Incident response

If a secret is committed: rotate the credential immediately, remove from history with owner authorization, and document the incident in an issue record (without re-committing the secret).
