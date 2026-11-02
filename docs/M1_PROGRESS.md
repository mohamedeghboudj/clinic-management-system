# M1 progress — contracts/tooling phase

This first PR replaces the empty scaffold, establishes Python 3.14 Conda/tooling,
and implements identity/errors/events/paging/health values, clock/ID adapters,
configuration and safe telemetry. Primitive fixtures and author verification are
included. Transaction ports/fakes follow in the dependent second PR; demo and
M5-independent contracts follow in the third. See the PR stack for scope.

GitHub main protection, two approvals, required checks, selected Actions,
dependency alerts/fixes and secret scanning/push protection are applied and
read back against the reviewed policy. Original Telegram blob is preserved.

M2 @ahmed-ammiche independently tests this PR; M3 @SamirKor and M4
@MohamedAmine-dash review it. All have verified write access. Their evidence
and approvals remain required; do not substitute bot/author approval. Track acceptance in
[issue #1](https://github.com/mohamedeghboudj/clinic-management-system/issues/1).

No patient/access/scheduling/clinical/billing models, database or GUI are
implemented by this PR. Full integration waits for the actual feature owners.

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
