# REA integration — scope and limits

REA ("Reverse Engineer Anything", installed by the user separately) was
inspected for this project. Honest findings:

- REA is a **reverse-engineering/analysis toolkit** for apps, binaries and JS
  bundles. It provides **no browser control, no Facebook authentication, and
  no post-extraction capability**.
- Therefore NOVA M3 ships **no REA adapter in v1.0** — inventing one would be
  a fake integration, which this project refuses to do.

## Supported integration points (future, isolated)

If REA integration is wanted later, the safe shape is:

1. **Offline page-source analysis:** export a saved page snapshot via
   `nova extract --file` outputs; analyze the HTML/JS with REA separately to
   understand a *changed* Facebook page structure, then update NOVA's M3
   field rules. REA never touches the live session.
2. **Adapter boundary:** a new module `nova/engines/rea.py` or
   `nova/analysis/rea.py` implementing a narrow, documented interface (input:
   a file path; output: an analysis report) — added only after its real CLI
   surface is verified in the target environment, with tests.
3. **Isolation rules:** REA processes must never receive cookies, session
   files, the NOVA database, or credentials; untrusted scripts from any
   repository are inspected before execution.
