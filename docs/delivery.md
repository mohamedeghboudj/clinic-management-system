# Delivery plan

The product goal is a staff-managed clinic visit across two workstations, with clinic-scoped access, recoverable records and accurate billing. Each sprint lasts one week. The team selects work from one ordered product backlog and demonstrates one integrated result at review.

| Sprint | Acceptance decision | GitHub |
| --- | --- | --- |
| 1 · Models and contracts | Merge the reviewed feature branches and integration PR, run the combined suite and the synthetic visit on main, then record the freeze SHA. | [Model milestone](https://github.com/mohamedeghboudj/clinic-management-system/milestone/1) |
| 2 · Connected clinic visit · due 3 Dec 2026 | Two staff desktops complete one visit through a shared Python API and remote PostgreSQL. A 400 DZD payment against 1,000 DZD leaves 600 due, including after a lost response. | [Connected visit milestone](https://github.com/mohamedeghboudj/clinic-management-system/milestone/2) |
| 3 · Release and recovery · due 14 Dec 2026 | Verify a clean Windows installation, measure representative performance and restore an isolated remote backup. Present evidence for the release decision. | [Release milestone](https://github.com/mohamedeghboudj/clinic-management-system/milestone/3) |

## Sprint 2 implementation order

Start from the verified Sprint 1 freeze on `main`. Publish shared contracts first so feature owners can work in parallel. See [requirements](requirements.md) for the S1–S8 acceptance criteria.

| Subsystem | Deliverable and issue | Integration evidence |
| --- | --- | --- |
| Foundation | [Shared API, migrations and transactions #40](https://github.com/mohamedeghboudj/clinic-management-system/issues/40), [S7 two-client sync #47](https://github.com/mohamedeghboudj/clinic-management-system/issues/47) | Two protected sessions, rollback, stale update, reconnect and authorized refetch. |
| People and access | [S1 staff access #41](https://github.com/mohamedeghboudj/clinic-management-system/issues/41), [S2 patients #42](https://github.com/mohamedeghboudj/clinic-management-system/issues/42) | Disabled and cross-clinic access denied, unique patient number, bounded search. |
| Scheduling | [S3 booking and check-in #43](https://github.com/mohamedeghboudj/clinic-management-system/issues/43) | Two connections compete for a doctor or room. One booking succeeds. Adjacent bookings succeed. |
| Clinical | [S4 consultation and prescription #44](https://github.com/mohamedeghboudj/clinic-management-system/issues/44) | Assigned doctor finalizes, stale saves fail and amendments preserve the original note. |
| Billing | [S5 invoice #45](https://github.com/mohamedeghboudj/clinic-management-system/issues/45), [S6 payment #46](https://github.com/mohamedeghboudj/clinic-management-system/issues/46) | Immutable service snapshots, concurrent retry yields one payment, lost acknowledgment reconciled. |

Foundation also coordinates [bounded adapter retries #2](https://github.com/mohamedeghboudj/clinic-management-system/issues/2) in Sprint 2 and non-sensitive [desktop preferences #3](https://github.com/mohamedeghboudj/clinic-management-system/issues/3) in Sprint 3. Test deadline exhaustion and lost acknowledgments during the connected visit. Verify preferences during clean installation.

Proposed checkpoints are contracts at kickoff, remote smoke test, connected visit, two-client fault tests, then review on 3 December. Confirm remote development resources and backend hosting at kickoff. The planning baseline is Supabase Auth and hosted PostgreSQL behind the Python API. Keep database credentials on the server and restrict test environments to synthetic patients.

## Tracking and review

Use the [Notion project home](https://app.notion.com/p/3ef016453ab0804c9a81c309a16e3bb8) for sprint goals, selected work, working agreements and review evidence. Use the [GitHub Project](https://github.com/users/mohamedeghboudj/projects/4) for issues, assignees, changes and milestones. Link the issue and its PR, and update the work item when its status changes. Owners bring blockers to daily Scrum. At review record the tested SHA, environment, observed result and outstanding defects. At retrospective assign an owner to one improvement.

Independent verification, two assigned human reviews and green required checks apply to each PR. A sprint ends with a recorded review decision. A release additionally requires the [S8 release and recovery evidence](https://github.com/mohamedeghboudj/clinic-management-system/issues/48). Earlier design and test records retain their historical identifiers.
