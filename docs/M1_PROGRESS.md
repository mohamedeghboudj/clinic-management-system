# M1 progress and required independent handoff

## M1 contribution Â· 25â€“27 November 2026

Mohamed coordinated the cross-feature audit, reproduced the failures and contributed
the following repairs on the original developersâ€™ branches. Feature ownership stays
with M2â€“M5.

| Contribution | Review evidence |
| --- | --- |
| Protected finalized consultation state and validated status/timestamp pairs on rehydration. Propagated the fix through the prescription and design branches. | [#15](https://github.com/mohamedeghboudj/clinic-management-system/pull/15), [#16](https://github.com/mohamedeghboudj/clinic-management-system/pull/16), [#17](https://github.com/mohamedeghboudj/clinic-management-system/pull/17) |
| Repaired the scanner baseline and dependency check. Added a relocation test demonstrating that a new finding in the same file still fails the gate. | [#21](https://github.com/mohamedeghboudj/clinic-management-system/pull/21) |
| Added clinic validation and failure-atomicity tests, diagnosed the hosted Windows timezone failure, and pinned the IANA data in the runtime and hash lock. | [#22](https://github.com/mohamedeghboudj/clinic-management-system/pull/22) |
| Built the connected in-memory visit, added it to CI, reconciled S1â€“S8 with the sprint backlog, and rehearsed the squash sequence against main. | [Increment evidence](requirements.md#sprint-1-increment-verification) Â· [Integration issue #4](https://github.com/mohamedeghboudj/clinic-management-system/issues/4) |

The combined Python 3.14.10 suite passed **794 tests with zero skips**. All five
feature heads were included. The merge rehearsal applied #21, #22, #15, #16 and #17
as separate squash commits before the [integration PR #39](https://github.com/mohamedeghboudj/clinic-management-system/pull/39).
Human approvals and final acceptance are tracked on GitHub.

Reviewers can run `python -m scripts.demo_model` to verify the 1,000/400/600 DZD
scenario and rollback. The records below are dated handoffs.

## Handoff on 23 November 2026

Foundation contracts (#5) and transaction support (#6) have merged into
`main`. PR #7 now targets `main` and adds the foundation demo, billing
contract tests and handoff material. Run `python -m scripts.demo_model
--foundation-only` for the offline transaction demo. Running without the
flag reports pending integration and exits with status 2.

The foundation suite passed 88 tests. Its 13 billing cases require M5's
billing models. With those models at `ff808da`, the combined suite passed
all 208 tests. M2's independent foundation evidence and the assigned M3/M4
reviews are tracked in [issue #1](https://github.com/mohamedeghboudj/clinic-management-system/issues/1#issuecomment-7108746007).
The full clinic demo is tracked in [issue #4](https://github.com/mohamedeghboudj/clinic-management-system/issues/4).

The sections below record the original 1 November handoff. Test counts,
branch targets and workflow observations there refer to that earlier snapshot.

## Implementation scope

- M1 foundation contracts, configuration, operational telemetry and deterministic
  transaction support are implemented on the foundation branch.
- Python 3.14 fresh project Conda environment created; root metadata/dependency
  locks, CI/security workflows and docs are prepared and being verified.
- Original Telegram workflow preserved; old scaffold replaced without rewriting
  main history. Guide and original nonempty charter are outside the repo.
- Read-only AuditRecord compatibility was explicitly approved by Mohamed.

## Mandatory external dependencies

- M2 is @ahmed-ammiche with verified write access; independent tests for M1
  remain pending. M1's committed tests are author verification only.
- Assigned reviewers are M3 @SamirKor and M4 @MohamedAmine-dash, both with
  verified write access. Their final approvals remain required; never use an
  author/bot approval to replace either assigned review.
- M2â€“M5 models are not present: the full clinic workflow demo cannot yet run.
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

Contracts/tooling â†’ transaction fakes â†’ demo/design/handoff. Dependent PRs may be
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
| 1 | [Contracts/tooling #5](https://github.com/mohamedeghboudj/clinic-management-system/pull/5) â€” `feature/w1-foundation-contracts` | main |
| 2 | [Transaction fakes #6](https://github.com/mohamedeghboudj/clinic-management-system/pull/6) â€” `feature/w1-foundation-fakes` | #5; retarget to main after #5 merges |
| 3 | [Demo and handoff #7](https://github.com/mohamedeghboudj/clinic-management-system/pull/7) â€” `feature/w1-foundation-demo` | #6; retarget after preceding acceptance |

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

## Confirmed GitHub assignments â€” 1 November

M2 @ahmed-ammiche and M4 @MohamedAmine-dash have verified write access.
PRs #5â€“#7 assign M1 implementation and M2 independent testing; review
requests name M3 @SamirKor and M4 @MohamedAmine-dash while PRs stay draft.
Issue #1 assigns M1/M2/M3/M4; #2â€“#4 assign M1 coordination. These
assignments do not establish completed tests, approvals or merges.

## Active rulesets â€” 1 November

Main ruleset 26311417 requires PR-only updates, two current approvals, code-owner
review, resolved conversations, current app-bound CI and squash merging; it blocks
force pushes/deletion and configures no bypass actors. Working-branch ruleset
26311418 blocks force pushes while preserving normal commits and merged-branch
deletion. Classic protection remains active. Live full-policy readback passed.
Four administration regression tests verify idempotent named updates, ambiguous
name rejection, required-check app identity and bypass detection. The current
complete stack passes 85 author-verification tests; nine M5 cases remain pending.
Production/test-support coverage remains 98.99%; M2 independent evidence and
M3/M4 approvals are still required. See `docs/github-administration.md` for scope.
