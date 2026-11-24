# Model boundaries and M1 handoff

M1 owns Entity identity behavior, failure categories, metadata DomainEvent and
application paging/health/clock/ID/audit/UoW/metrics contracts. Domain depends only
on the standard library and domain modules. Entity roots refer to other aggregates
by UUID; readonly values and DTOs retain no ORM/framework objects.

| Owner | Next models / relation boundary |
| --- | --- |
| M2 | Person may have clinic Patient/Staff profiles and account memberships; DoctorProfile composes staff. Roles/grants live on membership. AuditEntry satisfies AuditRecord. |
| M3 | Clinic owns rooms; Appointment references clinic/patient/doctor/room and TimeSlot. Future common reservations unify surgery/maintenance conflicts. |
| M4 | Appointment links one consultation; finalized history preserves amendments; prescriptions own items; catalogue items supply billing snapshots. |
| M5 | Invoice owns lines and references patient; posted payments/reversals derive debt. Money belongs in domain/shared/money.py. |

Use `@dataclass(eq=False, kw_only=True)` for mutable Entity dataclasses and declare
their ID/version fields. Frozen Entity dataclasses are supported because Entity
itself is not a dataclass. Never compare entire mutable graphs for identity.

AuditRecord is a read-only structural shape approved by Mohamed on 1 November:
M2 does not need to inherit it. Test AuditFixture/ProbeEntity are synthetic test
support, not implementation of M2–M5 classes. Feature owners update their class,
ER/state and port designs as they implement; no speculative inheritance hierarchy
or database schema is frozen by this M1 document.
