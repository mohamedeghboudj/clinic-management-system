# Domain model boundaries

The staff visit joins a clinic patient to a booked doctor and room. A consultation produces immutable history, prescriptions and billable service references. Invoice line snapshots and the payment ledger determine the current balance.

Domain types depend on the standard library and other domain types. Aggregate boundaries use UUIDs. Application workflows depend on repository protocols. A request-scoped transaction binds the concrete repositories to one connection.

- [Relational model and ER diagram](design/database.md)
- [Shared workflow interfaces](contracts/connected-visit.md)
- [Foundation types and transaction behavior](contracts/foundation.md)
