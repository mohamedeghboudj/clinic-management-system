# Initial requirements baseline

Status: derived from the project blueprint, pending Product Owner/clinic validation.
The M1 foundation implements shared contracts, not these complete staff features.

| Story | Outcome / acceptance | Feature owner |
| --- | --- | --- |
| S1 | Individual staff login; disabled users denied; clinical fields protected even through direct API calls. | M2 |
| S2 | Register/search patients with validated fields, unique clinic patient number and paged search. | M2 |
| S3 | Book/check in; reject concurrent doctor/room overlaps; allow adjacent intervals. | M3 |
| S4 | Assigned doctor drafts/finalizes notes and written prescriptions; preserve amendments/history. | M4 |
| S5 | Issue exact-decimal invoice with immutable description/price snapshots and no accidental duplicate billing. | M5 |
| S6 | Record payment once per command key; 400/1000 leaves 600 due; reject over-allocation. | M5 |
| S7 | Two clients see authorized changes; stale saves conflict; lost responses recover by command status. | M1 + feature owners |
| S8 | Clean desktop installation without local DBMS; diagnosable failures and verified remote restoration. | M1 + team |

Quality constraints: Python 3.14 Conda environment, remote-only authoritative
storage, server-side access, exact decimal money, bounded queries, explicit error
and lifecycle contracts, transaction/audit/outbox atomicity, no secrets or real
patient fixtures, two reviews and independent tests. Performance/recovery targets
in the blueprint remain proposed and unmeasured until representative tests.

M1 verification traces to identity/typing/layer boundaries, safe settings/logging,
transaction copy/rollback/staging and portability. M2 independently tests M1;
M1's billing contracts independently test M5 once its code exists. Remote races,
authorization, sockets and real restore require integration evidence later.

Deferred: surgeries, labs, admissions/beds, materials/stock, purchasing, expenses,
advance patient credit, broad reports, patient portal and external services. Their
member-owned design notes do not constitute implemented features.
