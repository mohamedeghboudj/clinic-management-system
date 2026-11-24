# Foundation contract index

Python baseline: 3.14, confirmed by Mohamed. No import-time environment reads,
network calls, global database sessions or production imports from test support.
Use explicit mappings, injected clock/IDs and safe failure categories.

| Contract | Module | Stable public surface |
| --- | --- | --- |
| Identity equality | `domain.shared.entity` | `Entity.id: UUID`, `same_identity(other)`, equality by concrete type and ID; no hash. |
| Error categories | `domain.shared.errors` | `ClinicError(code=..., message_key=..., safe_details=...)` and documented subclasses. |
| Update hints | `domain.shared.events` | Frozen DomainEvent fields/types from the member guide; uppercase allowlisted event names, aware UTC, nonnegative version. |
| Paging | `application.contracts.paging` | `PageRequest(limit=25, cursor=None)`, frozen `Page[T](items=tuple(...), next_cursor=...)`, `has_next()`. |
| Health | `application.contracts.health`, `ports.health` | RuntimeState/HealthStatus enums, ComponentHealth, `HealthCheck.check()`. |
| Clock/IDs | `application.ports.clock`, `identity` | `Clock.now() -> datetime`, `IdGenerator.new_id() -> UUID`; standard-library adapters in infrastructure. |
| Audit | `application.ports.audit` | `AuditRecord` readonly field properties; `AuditWriter.append(entry)`. |
| UoW | `application.ports.unit_of_work` | Enter/commit/rollback, stage_event, stage_audit, exit without suppressing failures. |
| Metrics | `application.ports.metrics` | `increment(name, outcome=...)`, `observe(name, seconds, outcome=...)`. |
| Settings | `config.server`, `desktop` | Frozen ServerSettings/DesktopSettings and explicit mapping loaders. |

## Audit compatibility approved on 1 November

M2's AuditEntry remains M2's implementation. It must expose: `id`, `clinic_id`,
`actor_id`, `action`, `resource_type`, `resource_id`, `outcome`, `occurred_at`,
`correlation_id`, `reason_code`, with the types in `AuditRecord`. The protocol's
readonly properties accept frozen dataclass fields without subclassing it.
M1 supplies an `AuditFixture` only in test support, not a substitute account or
clinical access implementation. Typed Protocol assignment examples are verified.

## Transaction behavior

Enter opens an unfinished transaction. Commit persists changes plus audit/outbox;
exit without commit restores/discards all uncommitted work. Exceptions propagate.
A successful commit is irreversible through a later rollback/context exception.
No network event is published by commit; the future dispatcher consumes durable
outbox entries. Reusing a UoW opens a fresh context and resets prior observations.

`tests.support.MemoryStore` deep-copies collection reads/replacements/snapshots.
Its `save_versioned` helper supports dataclass fixtures and increments a copied
root, rejecting mismatched expected versions. Feature-specific repository fakes
must retain typed ports and reference/clinic checks. Nested fake transactions fail;
no parallel isolation, external durability or offline synchronization is claimed.

## Boundary limits and review changes

Page size 1–100; cursors are bounded printable ASCII containers, interpreted by
the repository, never raw trusted SQL. Event types are registered in one reviewed
allowlist. Health component/code labels and telemetry operations/outcomes are
also registered, avoiding free-form private data/cardinality growth.

Server DB settings currently implement the blueprint's PostgreSQL/TLS baseline:
remote host, explicit credentials/database and `sslmode=verify-full`. The adapter
must configure CA verification and validate actual connectivity later. Desktop
HTTPS defaults secure; localhost HTTP needs an explicit development-only flag.
No authentication algorithm, host, locale or timeout is guessed by constructors;
loaders require explicit settings. Changes affecting consumers require a PR,
updated signature/documentation and their reviewers, not local duplicate types.
