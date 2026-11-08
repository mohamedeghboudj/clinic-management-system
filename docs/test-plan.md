# Foundation and handoff test plan

M1 author verification is permitted by Mohamed but never relabelled independent.
M2 must independently test M1; M3/M4 must review. M1 prepares independent M5
contracts and reviews M3/M4 when their implementations arrive.

| Area | Required failure/invariant evidence |
| --- | --- |
| Entity | Same concrete type/ID equality; different type/ID inequality; no mutable-value hash. |
| Errors | Stable code/key; copied read-only details; default repr/message omit detail values. |
| Paging/events/health | Boundaries, malformed cursor, unknown labels, wrong UUID/version and naive timestamps. |
| Settings | Explicit requirements, finite positive timeouts, secret-safe repr/errors, remote verified TLS, secure desktop URL and explicit local-development exception. |
| Determinism | Supplied UTC clock/unique IDs, advancing time, exhaustion and invalid values. |
| Transactions | Detached reads/writes/snapshots, atomic multi-collection rollback, no audit/outbox after failure, duplicate effects fail, explicit commit, inactive/nested context rejection and stale saves. |
| Logging/metrics | Drop arbitrary messages, exception values and private keys; rotation/config failures; finite durations and registered low-cardinality labels. |
| Future billing | Exact money/rounding, line snapshot immutability, 400/1000 partial payment, excess payment and reversal bounds; tests skip explicitly until required M5 modules exist. |

Coverage measures production modules and M1 test support. Enforce >=80% branches
per module, falling back to statements for modules without branches. Ports have
no artificial executed implementation. Review assertions against independent
expected values rather than implementation-derived expectations.

Next-week remote tests use an isolated project/schema and two synchronized real
connections for overlap/payment races; memory fakes cannot establish SQL isolation,
locking, durable idempotency or authorization. No destructive production tests.
Week 3/4 add direct API/socket denials, reconnect/unknown outcome, two desktops,
clean installer, representative latency run and an isolated remote restore drill.
