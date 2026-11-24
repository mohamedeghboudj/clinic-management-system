# ADR 0001: modular backend, thin desktop and remote persistence

Status: implemented M1 foundation; human review and feature integration pending.
Date: 2026-11-01. Sources: supplied Sommerville ch. 5–7, 17, 24–25 and the
project's Meeting and Delivery Blueprint / Week 1 Member Implementation Guide.

## Context and decisions

Five members must build independently without distributing database credentials
to staff desktops. Use one `src/clinic_management` package: pure domain,
application contracts/ports, inward-dependent infrastructure/API, thin desktop,
and explicit composition roots. One backend deployment and remote PostgreSQL
support shared transactions; do not introduce microservices or offline writes.

The team confirmed Python 3.14 in a fresh Conda environment. M1's current runtime
is standard-library only. Add Qt/FastAPI/SQLAlchemy/Alembic/driver packages when
their Week 2 adapters are implemented and tested, not as unused dependencies now.

Entity is a non-dataclass behavior base. Subclasses declare `id: UUID` and use
`eq=False` if dataclasses; equality is concrete type plus identity. Mutable and
frozen dataclass entities can coexist. Aggregate version fields are explicit.
Value objects are immutable and equality-by-value. Shared models are not a
reason to invent generic CRUD services or deep role inheritance.

AuditWriter/UoW accept the approved read-only structural `AuditRecord` protocol,
with M2's planned AuditEntry fields. This avoids importing or implementing M2's
missing class. M2's immutable dataclass will satisfy the protocol naturally.
The user explicitly approved this contract adjustment on 1 November.

Domain methods change model state. Application use cases construct metadata
events/audit and stage them alongside writes; a durable outbox delivers only
committed events. Push hints invalidate authorized views; reconnect refetches
state. Delivery is at least once, and hints contain no clinical narrative.

## Verification and consequences

Static import checks, strict types and contract tests protect module boundaries.
In-memory copies prove deterministic rollback/state rules, not DB isolation.
Real PostgreSQL constraints/version checks, transaction tests with two connections,
server-side permissions and socket authorization remain required next week.

No database account, provider project or backend host is invented/configured by
this foundation. Provider/region, pilot currency/timezone, clinical correction
policy, production keys and retention/recovery objectives require the team's
recorded decisions before deployment. Current timestamp envelopes use UTC; no
clinic-local timezone is assumed.

The old scaffold is removed on a feature branch; main history remains intact.
The original Telegram workflow is preserved byte-for-byte. New workflows are
least-privilege and pinned, with a reviewed administration policy applied only
through authenticated repository administration.
