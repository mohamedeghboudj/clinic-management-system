# Foundation design and extension boundaries

Implemented: identity equality, safe error categories, paging, health enums/results,
clock/ID and audit/event/UoW/metrics ports, standard-library clock/UUID adapters,
explicit settings, safe operational logging, test clocks/IDs and transaction fakes.
See the contract index and source docstrings for exact typed signatures.

## RetryPolicy — DESIGN

Properties: `max_attempts: int`, `base_delay_seconds: float`,
`max_delay_seconds: float`. Require positive finite limits and a bounded attempt
count. Proposed `delay_for(attempt: int, jitter_sample: float) -> float` computes
capped exponential backoff from explicit jitter in [0,1]; invalid values fail.
`allows_retry(operation: str, has_idempotency_key: bool) -> bool` allows safe reads
and same-key commands only. It never blindly retries a payment after response loss.

Consumers: future HTTP/database/gateway adapters. Cross-record use cases own
idempotency and rollback, not a decorator wrapped around every model method.
Examples: transient read retries within a deadline; unknown payment first queries
command status; exhausted retries return DependencyUnavailableError. Confirm
production deadlines/counts from measurements; no arbitrary loop is implemented.

## DesktopPreferences — DESIGN

Properties: `locale: str`, `window_size: tuple[int,int]`, `theme: str`, file format
version. Proposed `load_preferences(path: Path) -> DesktopPreferences` and
`save_preferences(value: DesktopPreferences, path: Path) -> None`. Validate size,
supported values and version; atomic temporary-file replacement handles crashes.
Invalid preference files can fall back to documented non-sensitive UI defaults.

Consumers: desktop bootstrap/views. Store no patient cache, clinical drafts,
passwords, tokens or database URL. A future encrypted offline clinical feature
needs separate retention/conflict/key design; JSON preferences are not a database.

## Ownership and dependencies

M2 implements Person/access/AuditEntry, M3 TimeSlot/scheduling, M4 clinical/catalogue,
M5 Money/billing. M1's synthetic probes are infrastructure fixtures only. The full
clinic demo and independent M5 contracts cannot establish behavior before those
models exist. Keep explicit pending integration rather than placeholder features.
