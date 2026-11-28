# Initial requirements baseline

Status: derived from the project blueprint, pending Product Owner/clinic validation.
The Sprint 1 model evidence and remaining release checks appear below. The
[delivery plan](delivery.md) maps each remaining story to its issue and milestone.

| Story | Outcome / acceptance | Subsystem |
| --- | --- | --- |
| S1 | Individual staff login; disabled users denied; clinical fields protected even through direct API calls. | People and access |
| S2 | Register/search patients with validated fields, unique clinic patient number and paged search. | People and access |
| S3 | Book/check in; reject concurrent doctor/room overlaps; allow adjacent intervals. | Scheduling |
| S4 | Assigned doctor drafts/finalizes notes and written prescriptions; preserve amendments/history. | Clinical |
| S5 | Issue exact-decimal invoice with immutable description/price snapshots and no accidental duplicate billing. | Billing |
| S6 | Record payment once per command key; 400/1000 leaves 600 due; reject over-allocation. | Billing |
| S7 | Two clients see authorized changes; stale saves conflict; lost responses recover by command status. | Integration |
| S8 | Clean desktop installation without local DBMS; diagnosable failures and verified remote restoration. | Operations |

Quality constraints: Python 3.14 Conda environment, remote-only authoritative
storage, server-side access, exact decimal money, bounded queries, explicit error
and lifecycle contracts, transaction/audit/outbox atomicity, no secrets or real
patient fixtures, two reviews and independent tests. Performance/recovery targets
in the blueprint remain proposed and unmeasured until representative tests.

The model suite verifies identity, safe settings, transaction rollback and billing invariants. Remote races, API authorization, socket isolation and restore require separate integration evidence.

Deferred: surgeries, labs, admissions/beds, materials/stock, purchasing, expenses,
advance patient credit, broad reports, patient portal and external services. Their
member-owned design notes do not constitute implemented features.


## Sprint 1 increment verification

Run `python -m scripts.demo_model` from the installed development checkout. The Windows and Ubuntu unit
jobs run this command after the tests and coverage gate. The scenario uses
synthetic identities, a deterministic clock and memory transactions.

| Stories | Executable evidence at the model checkpoint | Evidence due later |
| --- | --- | --- |
| S1–S2 | The demo registers a patient, checks an assigned doctor and a cashier, and denies a secretary's clinical write. People and access suites cover validation and denial paths. | Individual login, direct API authorization, clinic-unique numbers and paged remote search. |
| S3 | A bookable room and an open time slot lead to check-in and completion. Scheduling contracts exercise adjacent intervals and early no-show rejection. | Two connections competing for the same doctor or room. |
| S4 | The linked consultation is finalized and its prescription issued. The demo appends a correction while preserving its original entry. Clinical tests cover reconstruction and versioned saves. | Durable clinical history and direct endpoint authorization. |
| S5–S6 | A 1,000 DZD invoice links to the visit. An authorized 400 DZD payment leaves 600 DZD outstanding. The demo rejects an excess payment and an invalid reversal. Billing tests cover immutable line snapshots. | Durable same-key replay and reconciliation after a lost response. |
| S7–S8 | The memory transaction rolls back a rejected edit and preserves the committed payment, audit entry and outbox event. | Two workstations, reconnect, measured latency, installation and a timed remote restore. |

Product Owner validation, assigned human reviews and the release demonstration
are separate acceptance records. The [Sprint 1 increment](https://app.notion.com/p/422016453ab08187ac1fca0617237c68)
tracks team acceptance and [issue #4](https://github.com/mohamedeghboudj/clinic-management-system/issues/4)
tracks integration review.
