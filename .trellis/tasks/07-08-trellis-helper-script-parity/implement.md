# Implementation Plan: Extensible project quality hooks

## Checklist

1. Restore all modified Trellis library/configuration files.
2. Create typed project hook contracts, registry, changed-file discovery, and
   the CLI runner under `hooks/`.
3. Move backend validation into a project hook that uses root `.venv` on
   Windows and the maintained backend script on POSIX.
4. Move frontend component validation into a project hook using the existing
   component specification and `components.json` alias.
5. Add isolated project-hook unit tests for pass, failure, skip, policy
   violations, registered UI imports, and registry validation.
6. Update the project hook contract and task artifacts with CLI usage and the
   no-library-modification boundary.
7. Add a Codex Stop adapter that maps quality-hook CLI failures to the Stop
   continuation protocol, then register it in `.codex/hooks.json`.
8. Validate with `python -m unittest discover hooks/tests -v`,
   `python hooks/run_quality_hooks.py --list`, compilation, and a no-diff check
   for protected Trellis library files.
