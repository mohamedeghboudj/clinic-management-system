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

## Published PR stack and remote verification

| Order | Branch / draft PR | Dependency |
| --- | --- | --- |
| 1 | [Contracts/tooling #5](https://github.com/mohamedeghboudj/clinic-management-system/pull/5) — `feature/w1-foundation-contracts` | main |
| 2 | [Transaction fakes #6](https://github.com/mohamedeghboudj/clinic-management-system/pull/6) — `feature/w1-foundation-fakes` | #5; retarget to main after #5 merges |
| 3 | [Demo and handoff #7](https://github.com/mohamedeghboudj/clinic-management-system/pull/7) — `feature/w1-foundation-demo` | #6; retarget after preceding acceptance |

All new required quality, Linux/Windows unit, dependency-security and CodeQL
checks passed for each PR. The top implementation snapshot is commit
`5bce5ee64f16c03c57c5447b558f6d69d89d54dd`:
[Foundation CI](https://github.com/mohamedeghboudj/clinic-management-system/actions/runs/41291484274),
[dependency security](https://github.com/mohamedeghboudj/clinic-management-system/actions/runs/41291484326),
[CodeQL](https://github.com/mohamedeghboudj/clinic-management-system/actions/runs/41291484208).
A documentation-only evidence update may advance this branch without changing
that verified implementation; required checks also run on the new head.

Consumers may fetch/branch from `origin/feature/w1-foundation-demo` while the
protected-main acceptance gate waits. Do not merge the stack or call independent
acceptance complete until M2's tests and M3/M4's reviews are present.

### Preserved notification failure

The original Telegram workflow remains byte-for-byte unchanged, but its send
step currently fails with `Bad Request: TOPIC_CLOSED`. The action downloads and
secrets are available; the Telegram destination topic needs reopening outside
the repository. This is separate from the successful required implementation
checks. Evidence: [original notification run](https://github.com/mohamedeghboudj/clinic-management-system/actions/runs/41291379306).
No Telegram secret, topic or user-owned workflow was changed.

## Tracked handoff

- [Independent foundation acceptance #1](https://github.com/mohamedeghboudj/clinic-management-system/issues/1)
- [Retry adapter design #2](https://github.com/mohamedeghboudj/clinic-management-system/issues/2)
- [Desktop preference design #3](https://github.com/mohamedeghboudj/clinic-management-system/issues/3)
- [Full demo, M5 verification and M3/M4 reviews #4](https://github.com/mohamedeghboudj/clinic-management-system/issues/4)
