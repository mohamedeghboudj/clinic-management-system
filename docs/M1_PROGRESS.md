# M1 progress — transaction-fake phase

This second stacked PR adds structural audit/UoW/event/health ports, copy-isolated
memory transaction support, stale-version save checks and protocol/rollback
verification. It depends on the foundation contracts PR and does not merge into
main until the preceding PR is accepted and this PR is retargeted to main.

Author verification for contracts and fakes is included. It does not replace
M2 independent foundation tests or M3/M4 human approvals; M2/M4 have not joined.
Acceptance is tracked in [issue #1](https://github.com/mohamedeghboudj/clinic-management-system/issues/1).

The third PR adds the explicit foundation demo and prepared M5 contract cases.
Full clinic integration remains dependent on actual M2-M5 models, tracked in
[issue #4](https://github.com/mohamedeghboudj/clinic-management-system/issues/4).

No DB durability, concurrent transaction isolation or live authorization is
claimed by the single-threaded in-memory fake. GitHub safeguards are active
and the original Telegram workflow remains unchanged.
