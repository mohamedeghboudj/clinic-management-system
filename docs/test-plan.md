# Foundation and handoff test plan

Record author verification and independent verification separately. Review the final head and run billing contracts against the actual models.

| Area | Required failure/invariant evidence |
| --- | --- |
| Entity | Same concrete type/ID equality; different type/ID inequality; no mutable-value hash. |
| Errors | Stable code/key; copied read-only details; default repr/message omit detail values. |
| Paging/events/health | Boundaries, malformed cursor, unknown labels, wrong UUID/version and naive timestamps. |
| Settings | Explicit requirements, finite positive timeouts, secret-safe repr/errors, remote verified TLS, secure desktop URL and explicit local-development exception. |
| Determinism | Supplied UTC clock/unique IDs, advancing time, exhaustion and invalid values. |
| Transactions | Detached reads/writes/snapshots, atomic multi-collection rollback, no audit/outbox after failure, duplicate effects fail, explicit commit, inactive/nested context rejection and stale saves. |
| Logging/metrics | Drop arbitrary messages, exception values and private keys; rotation/config failures; finite durations and registered low-cardinality labels. |
| Billing | Exact money/rounding, line snapshot immutability, 400/1000 partial payment, excess payment and reversal bounds; the integrated suite exercises the real models. |

Coverage measures production modules and transaction test support. Enforce >=80% branches
per module, falling back to statements for modules without branches. Ports have
no artificial executed implementation. Review assertions against independent
expected values rather than implementation-derived expectations.

Both CI operating systems also run the [connected Sprint 1 demo](requirements.md#sprint-1-increment-verification).

Sprint 2 remote tests use an isolated project/schema and two synchronized real
connections for overlap/payment races; memory fakes cannot establish SQL isolation,
locking, durable idempotency or authorization. No destructive production tests.
Sprint 2 also checks direct API and socket denials, reconnect after an unknown outcome,
and two desktops. Sprint 3 verifies the clean installer, representative latency and
an isolated remote restore. Record the environment and results with each increment.
