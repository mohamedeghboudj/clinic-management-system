# M1 progress and required independent handoff

Date: 2026-11-01. This ledger distinguishes implemented work, author verification
and external acceptance; it must not be read as independent approval.

## Implementation scope

- M1 foundation contracts, configuration, operational telemetry and deterministic
  transaction support are implemented on the foundation branch.
- Python 3.14 fresh project Conda environment created; root metadata/dependency
  locks, CI/security workflows and docs are prepared and being verified.
- Original Telegram workflow preserved; old scaffold replaced without rewriting
  main history. Guide and original nonempty charter are outside the repo.
- Read-only AuditRecord compatibility was explicitly approved by Mohamed.

## Mandatory external dependencies

- M2 has not joined: independent tests for M1 are pending. M1's committed tests
  are author verification only, as explicitly permitted.
- M4 has not joined: second assigned human review is pending. M3 is SamirKor;
  never use an author/bot approval to replace either assigned review.
- M2–M5 models are not present: the full clinic workflow demo cannot yet run.
  `--foundation-only` exercises actual implemented transaction contracts; default
  invocation reports pending integration instead of fake success.
- M5 billing implementation is not present: prepared independent contracts are
  pending execution; M1 has not implemented M5's business classes.
- GitHub administration was applied using the authenticated CLI. Full readback
  matches the policy: protected main, two approvals, five required checks, strict
  Actions permissions, dependency alerts/fixes and secret scanning/push protection.
- Backend host/provider project/production settings and remote restoration remain
  explicit deployment decisions; no real services or patient data are provisioned.

## Review sequence

Contracts/tooling → transaction fakes → demo/design/handoff. Dependent PRs may be
stacked but cannot bypass the two-review/independent-test gate. Other members can
branch from the appropriate reviewed foundation ref while main acceptance waits;
record that temporary dependency and retarget after its PR merges.

## Verified local evidence

- Fresh project Conda interpreter: Python 3.14.10; team baseline 3.14.
- 81 author-verification tests pass; nine independent M5 cases explicitly skip
  because M5's Money/billing implementation does not exist yet.
- Combined statement/branch coverage 98.99%; all measured modules satisfy their
  per-module branch/statement threshold. This is author evidence, not M2 approval.
- Ruff, strict mypy, source/import/physical-line contracts, workflow preservation,
  dependency declaration/import checks, secret scan and duplication check pass.
- No known vulnerabilities reported for the locked developer and empty runtime
  requirements. Hash-locked install validation passes.
- Foundation-only demo passes; sdist and wheel build successfully.
- No live database/backend/GUI is deployed. The full clinic demo remains pending.

Remote PR links and actual Linux/Windows CI results follow publication.

## Tracked handoff

- [Independent foundation acceptance #1](https://github.com/mohamedeghboudj/clinic-management-system/issues/1)
- [Retry adapter design #2](https://github.com/mohamedeghboudj/clinic-management-system/issues/2)
- [Desktop preference design #3](https://github.com/mohamedeghboudj/clinic-management-system/issues/3)
- [Full demo, M5 verification and M3/M4 reviews #4](https://github.com/mohamedeghboudj/clinic-management-system/issues/4)
