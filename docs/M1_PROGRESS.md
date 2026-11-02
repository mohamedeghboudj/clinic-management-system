# M1 progress — transaction-fake phase

This second stacked PR adds structural audit/UoW/event/health ports, copy-isolated
memory transaction support, stale-version save checks and protocol/rollback
verification. It depends on the foundation contracts PR and does not merge into
main until the preceding PR is accepted and this PR is retargeted to main.

Author verification for contracts and fakes is included. It does not replace
M2 @ahmed-ammiche's independent foundation tests or approvals from M3
@SamirKor and M4 @MohamedAmine-dash. All have verified write access.
Acceptance is tracked in [issue #1](https://github.com/mohamedeghboudj/clinic-management-system/issues/1).

The third PR adds the explicit foundation demo and prepared M5 contract cases.
Full clinic integration remains dependent on actual M2-M5 models, tracked in
[issue #4](https://github.com/mohamedeghboudj/clinic-management-system/issues/4).

No DB durability, concurrent transaction isolation or live authorization is
claimed by the single-threaded in-memory fake. GitHub safeguards are active
and the original Telegram workflow remains unchanged.

## Confirmed GitHub assignments — 1 November

M2 @ahmed-ammiche and M4 @MohamedAmine-dash have verified write access.
PRs #5–#7 assign M1 implementation and M2 independent testing; review
requests name M3 @SamirKor and M4 @MohamedAmine-dash while PRs stay draft.
Issue #1 assigns M1/M2/M3/M4; #2–#4 assign M1 coordination. These
assignments do not establish completed tests, approvals or merges.

## Active rulesets — 1 November

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
