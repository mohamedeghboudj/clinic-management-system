# Independent M1 design assessment — PR #10

**Date:** 1 November 2026. **Tester:** @mohamedeghboudj.
**Author:** @ayyoubbouchama. **Reviewers:** @ahmed-ammiche and @SamirKor.
**Submitted design:** `cdcbaabf70a3f65d43ecd3ef48121a2fa40d71e4`.
Scope: `docs/design/billing-procurement.md` against the Week 1 member guide.

**Outcome: design changes required before acceptance.** This is a manual contract
and failure-scenario assessment. Deferred Python services/models do not exist;
there are no executable unit tests that prove their behavior today.

## Coverage of the assigned design scope

The document supplies fields/signatures, relationships, states or immutability,
errors, transaction/security intent and examples for all 14 deferred entries.
The named future issue identifiers are placeholders; see the follow-up below.

| Entry | Acceptance scenarios to retain for future implementation |
| --- | --- |
| CreditNote | 200 on a 1000 charge leaves 800; cumulative credits over the charge fail; charge adjustment and cash return stay distinct. |
| PatientCredit | 500 less a 200 allocation leaves 300; zero/negative sources and foreign scope fail. |
| PaymentAllocation | 300 credit against 600 debt leaves 300 debt; over-allocation or another clinic/patient fails; both affected roots are serialized. |
| ExpenseCategory | Supported controlled categories parse; unknown categories fail through a safe error. |
| Expense | A cost can be marked paid once; payment before incurrence or repeated payment fails; supplier-linked cost is not counted twice. |
| FinancialSummary | 120000 received less 45000 paid yields 75000 net cash; invalid intervals fail; billed revenue/cash/debt remain separate measures. |
| Supplier | Active vendor/positive terms succeeds; negative terms fail; deactivation prevents new orders. |
| PurchaseOrderLine | 10 units at 850 totals 8500; quantity/unit/currency/price constraints are explicit. |
| PurchaseOrder | Nonempty DRAFT can be sent; partial receipt changes derived progress; received orders cannot be cancelled as unreceived. |
| GoodsReceiptLine | Positive quantity with optional lot succeeds; zero/negative quantity fails. |
| GoodsReceipt | Two receipts of five fulfill ten; five followed by six fails atomically with stock movement. |
| SupplierInvoice | 20000 less 8000 leaves 12000 payable; blank number, foreign payment or excess settlement fails. |
| SupplierPayment | Exact remaining 12000 settles debt; 12001 fails; retries must not create another cash outflow. |
| PricingPolicy | Calculations preserve supported currency/nonnegative result; no unneeded Week 1 strategy implementation. |

The RecordPayment/receipt, invoice projection and formatting signatures are also
present. The design separates display strings from money arithmetic and connects
stock receipt to M3's catalogue/movements rather than duplicating material models.
These are documented intentions, not verified remote accounting behavior.

## Required correction: concurrent idempotent payment replay

Tracked in [issue #14](https://github.com/mohamedeghboudj/clinic-management-system/issues/14),
assigned to M5. Section 2.1 checks the idempotency key before locking the invoice.
It does not reserve the command or specify a check after serialization.

| Step | Request A | Request B: same key and same 400 DZD command |
| --- | --- | --- |
| 1 | Key is absent. | Key is also absent. |
| 2 | Locks a 1000 DZD invoice and posts 400. | Waits for the invoice lock. |
| 3 | Commits payment, receipt, audit/outbox and command result. | Obtains the lock and sees 600 debt. |
| 4 | Returns the receipt. | Another 400 still passes balance validation; the design gives no replay recheck or unique-claim loser path. |

A unique command row may roll back B's transaction, but the design must explain
how B returns A's original receipt safely. State a unique command-claim/recheck
protocol and atomic loser recovery rather than relying only on the balance lock.
The choice belongs to M5's reviewed Week 2 design; this assessment does not select
or implement an adapter for the team.

Before design acceptance, specify these future integration cases:

1. Same key/payload delivered concurrently produces one payment, one result and
   one set of audit/outbox facts; both callers receive the original receipt.
2. Same key/different semantic payload conflicts without a second posting.
3. Lost commit acknowledgement uses the same key/status lookup; it never becomes
   a new cashier payment while the original outcome is unknown.
4. Command result, money, audit and outbox all commit or roll back together.
5. Trusted principal/clinic/resource scope is checked on initial and replay paths;
   canonical payload fields and authorization behavior are explicitly documented.

## Other completion and handoff actions

- Replace or map `ISSUE-S2-BILL-*`, `ISSUE-S2-FIN-*` and `ISSUE-S2-PROC-*`
  placeholders to real linked GitHub follow-up issues. The inspected repository
  did not contain those implementation tasks. The Week 1 guide requires a future
  issue for each DESIGN item; group related entries with explicit acceptance
  checklists if that is the agreed backlog organization.
- Keep inventory receipt, supplier liability, expense recognition and cash
  settlement distinctions explicit. Define report aggregation/correction examples
  before implementation; no legal/accounting-policy compliance is inferred here.
- Keep deferred models as documentation. Do not create passing placeholder Python
  classes or assert that this document proves SQL race safety.
- M5 updates the specification and issue links; M1 reassesses the scenarios;
  M2/M3 provide the required final reviews. PR #10 currently depends on the
  foundation contracts branch and must be retargeted to main after acceptance.

No Money/invoice unit tests are attributed to this docs-only branch. Executable
evidence belongs to PR #8/#9's separate reports and cannot certify these future
services. Real concurrency testing must use isolated remote PostgreSQL in Week 2.
