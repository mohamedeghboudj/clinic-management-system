# Transport design — Week 1 specification

Status: DESIGN; no HTTP/GUI implementation. Later public endpoints use `/api/v1`.

UUIDs are canonical strings. Money is an amount decimal string plus explicit
currency, never a binary float or locale-formatted number. Dates are ISO calendar
dates; instants are timezone-aware ISO timestamps, normalized to UTC on writes.
The clinic timezone affects display/day queries and is an explicit clinic setting.

Proposed encoders: `encode_money(value: Money) -> str`,
`encode_timestamp(value: datetime) -> str`, `encode_id(value: UUID) -> str`.
Feature owners implement explicit request/response DTO mappers after their models.
Never serialize entity `__dict__`, ORM relationships or settings automatically.

Requests reject unknown/forbidden fields. Principal, role grants, verified clinic
and assignment are server-derived, not accepted as trusted request facts. Responses
and subscriptions enforce action + clinic + relationship + allowed fields; no
diagnoses in waiting lists or credentials in any DTO/log.

Commands carry a UUID idempotency key; updates carry expected aggregate version.
The server binds command key to clinic/actor/operation and payload hash, stores its
result atomically with writes, and rejects changed-payload reuse. A lost response
means UNKNOWN until queried by the same key; it does not prove the payment failed.

Lists use PageRequest/Page with stable ordering and a unique tie-breaker. Errors
return stable code/message key and correlation ID, without SQL/stack traces.
Socket hints contain event ID/type/entity/version only. Reconnect reloads current
authorized view state; duplicate hints are harmless. Tests must prove HTTP and
socket authorization independently of button visibility.
