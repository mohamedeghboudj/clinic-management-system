# Billing, Credit, Finance and Procurement Design Specification (M5)

**Owner:** M5 (`@ayyoubbouchama`) · **Reviewers:** M2, M3 (`@SamirKor`) · **Independent Tester:** M1 (`@mohamedeghboudj`)

This document specifies the Week 2+ application use cases, transport mappers, desktop formatting helpers, and the 14 deferred credit, financial reporting, and procurement domain models defined in Section 6 of the Week 1 Member Implementation Guide. No Python classes are created for DESIGN items in Week 1.

---

## 1. Accounting Boundaries and Core Financial Principles

Before combining figures in clinic reports, the domain enforces four strict distinctions:

1. **Received Stock Cost vs. Supplier Liability:** Receiving physical materials (`GoodsReceipt`) increases inventory asset value and records a movement in M3's `StockMovement` ledger, whereas recording a `SupplierInvoice` establishes an accounts-payable liability in `DZD`.
2. **Supplier Liability vs. Expense Recognition:** Recording an operating `Expense` or a `SupplierInvoice` recognizes cost on an accrual basis (`incurred_on`), whereas settling that bill via `SupplierPayment` is a cash outflow (`paid_at`). An `Expense` linked to a `supplier_invoice_id` must never be double-counted alongside the settlement of that supplier invoice.
3. **Billed Revenue vs. Cash Received:** Issuing a patient `Invoice` recognizes `billed_revenue`, whereas posting a `Payment` (minus `PaymentReversal`) records `cash_received` and reduces `receivables`.
4. **Single Currency & Rounding Baseline:** All Sprint 1 calculations use `DZD` quantized to `0.01` with `ROUND_HALF_UP`. Line calculations follow `gross = quantize(quantity * unit_price)`, `subtotal = gross - discount_amount`, `tax = quantize(subtotal * tax_rate)`, and `total = subtotal + tax`.

---

## 2. Application Use Cases, Transport Mappers and Formatting (Week 2/3)

### 2.1 `RecordPayment.execute`
- **Signature:** `RecordPayment.execute(self, command: RecordPaymentCommand, principal: Principal) -> PaymentReceipt`
- **Command DTO (`RecordPaymentCommand`):** `clinic_id: UUID`, `invoice_id: UUID`, `amount: Money`, `method: PaymentMethod`, `idempotency_key: UUID`, `external_reference: str | None`, `correlation_id: UUID`.
- **Receipt DTO (`PaymentReceipt`):** `payment_id: UUID`, `invoice_id: UUID`, `net_paid: Money`, `outstanding: Money`, `settlement: SettlementStatus`, `received_at: datetime`.
- **Transaction, Concurrency & Idempotency:**
  1. Authorize `principal` via `AccessPolicy.require(principal, Permission.PAYMENT_RECORD, resource_context)`.
  2. Enter `UnitOfWork`. Check the command idempotency ledger keyed by `(clinic_id, principal.account_id, "PAYMENT_RECORD", command.idempotency_key)`.
  3. If the key exists with an identical SHA-256 payload hash, return the stored `PaymentReceipt` without inserting a duplicate payment. If the key exists with a different payload hash, raise `ConflictError(code="IDEMPOTENCY_KEY_REUSED", message_key="payment.idempotency.conflict")`.
  4. Call `InvoiceRepository.get_for_update(clinic_id, invoice_id)` to acquire a PostgreSQL row-level `FOR UPDATE` lock. Raise `NotFoundError` if absent.
  5. Load existing payments and reversals via `PaymentRepository`, execute `validate_payment(invoice, command.amount, payments, reversals)`, construct `Payment`, stage `AuditEntry` and `DomainEvent(event_type="PAYMENT_RECORDED", ...)`, persist the idempotency command record, and commit atomically.
- **Unknown Outcome Recovery:** After a network timeout, the desktop client re-submits the exact same `RecordPaymentCommand` (keeping the original `idempotency_key`) or queries command status by key before allowing the cashier to initiate a new payment.

### 2.2 `invoice_to_response`
- **Signature:** `invoice_to_response(invoice: Invoice, balance: BalanceSummary) -> InvoiceSummary`
- **Purpose:** Explicitly project domain `Invoice` and `BalanceSummary` into `InvoiceSummary` for API/desktop consumption, stripping internal audit metadata and never exposing clinical narratives or staff credentials.

### 2.3 `format_money`
- **Signature:** `format_money(value: Money, locale: str) -> str`
- **Purpose:** Format an immutable `Money` value for PySide6 desktop presentation and PDF invoice exports (e.g., `"1 000,00 DZD"` in `fr_DZ` or `"1,000.00 DZD"` in `en_US`). Display strings are never parsed back into domain calculations.

---

## 3. Deferred Domain Models (DESIGN Specifications)

### 3.1 `CreditNote` (`domain/billing/credit_note.py`)
- **Purpose:** Record an authorized downward adjustment against an `ISSUED` invoice without rewriting historical invoice lines or confusing charge reductions with cash refunds (`PaymentReversal`).
- **Proposed Fields & Signatures:**
  - Fields: `id: UUID`, `clinic_id: UUID`, `invoice_id: UUID`, `amount: Money`, `reason: str`, `issued_at: datetime`, `issued_by: UUID`.
  - Methods: `validate_against(self, invoice: Invoice, previous_credits: Sequence[CreditNote]) -> None`.
- **Relationships, Cardinalities & Scope:** `Invoice 1 ── 0..* CreditNote`; scoped to `clinic_id`.
- **States & Transitions:** Immutable once created (`ISSUED`). Cannot be edited or deleted.
- **Errors:** `ValidationError(code="INVALID_VALUE")` if `amount <= 0`, `reason` is blank, invoice is not `ISSUED`, or cumulative credits exceed `invoice.total()`.
- **Transaction, Concurrency & Security:** Requires `Permission.BILLING_WRITE`, row lock on `Invoice`, and atomic `AuditEntry` commit.
- **Examples:**
  - *Valid:* 200 DZD credit note on a 1,000 DZD unpaid invoice reduces outstanding balance to 800 DZD.
  - *Invalid:* 1,100 DZD credit note on a 1,000 DZD invoice raises `ValidationError`.
- **Future Issue & Dependencies:** `ISSUE-S2-BILL-01` (Depends on M5 `Invoice` and `BalanceSummary`).

### 3.2 `PatientCredit` (`domain/billing/patient_credit.py`)
- **Purpose:** Track advance deposits or authorized overpayments held on a patient's clinic account prior to invoice allocation. (Sprint 1 rejects excess payments directly until this ledger is enabled.)
- **Proposed Fields & Signatures:**
  - Fields: `id: UUID`, `clinic_id: UUID`, `patient_id: UUID`, `amount: Money`, `source_payment_id: UUID`, `recorded_at: datetime`.
  - Methods: `available_amount(self, allocations: Sequence[PaymentAllocation]) -> Money`.
- **Relationships, Cardinalities & Scope:** `Patient 1 ── 0..* PatientCredit`; `PatientCredit 1 ── 0..* PaymentAllocation`; scoped to `clinic_id`.
- **States & Transitions:** Immutable positive credit source; remaining balance is derived from allocations.
- **Errors:** `ValidationError(code="INVALID_VALUE")` if `amount <= 0` or currency mismatches clinic currency.
- **Transaction, Concurrency & Security:** Locked during allocation inside UoW; requires `Permission.PAYMENT_RECORD`.
- **Examples:**
  - *Valid:* 500 DZD credit with one 200 DZD allocation returns `available_amount == 300.00 DZD`.
  - *Invalid:* Zero or negative credit creation raises `ValidationError`.
- **Future Issue & Dependencies:** `ISSUE-S2-BILL-02` (Depends on M2 `Patient` and M5 `Payment`).

### 3.3 `PaymentAllocation` (`domain/billing/payment_allocation.py`)
- **Purpose:** Link a portion of a `PatientCredit` to settle debt on a specific `ISSUED` `Invoice`.
- **Proposed Fields & Signatures:**
  - Fields: `id: UUID`, `credit_id: UUID`, `invoice_id: UUID`, `amount: Money`, `allocated_at: datetime`.
- **Relationships, Cardinalities & Scope:** Joins `PatientCredit` (`N:1`) to `Invoice` (`N:1`) within the same clinic and patient.
- **States & Transitions:** Immutable append-only ledger entry.
- **Errors:** `ValidationError(code="PAYMENT_EXCEEDS_BALANCE")` if `amount` exceeds either `credit.available_amount(...)` or `invoice.outstanding`.
- **Transaction, Concurrency & Security:** Locks both `PatientCredit` and `Invoice` rows in one UoW.
- **Examples:**
  - *Valid:* Allocating 300 DZD from a 300 DZD credit to an invoice with 600 DZD due leaves 0 DZD credit and 300 DZD invoice debt.
  - *Invalid:* Allocating 400 DZD from a 300 DZD credit raises `ValidationError`.
- **Future Issue & Dependencies:** `ISSUE-S2-BILL-03` (Depends on `PatientCredit` and `Invoice`).

### 3.4 `ExpenseCategory` (`domain/financial/enums.py`)
- **Purpose:** Classify operational clinic expenditures using a controlled vocabulary.
- **Proposed Fields & Signatures:** `StrEnum` with values `SUPPLIES`, `RENT`, `UTILITIES`, `PAYROLL`, `EQUIPMENT`, `OTHER`.
- **Relationships, Cardinalities & Scope:** Referenced by `Expense.category`.
- **States & Transitions:** Stateless enumeration.
- **Errors:** `ValidationError(code="INVALID_VALUE")` when parsing unknown category strings.
- **Transaction, Concurrency & Security:** Pure domain type; used in `Permission.FINANCE_REPORT`.
- **Examples:**
  - *Valid:* `ExpenseCategory.SUPPLIES`.
  - *Invalid:* `"MARKETING"` rejected by parser.
- **Future Issue & Dependencies:** `ISSUE-S2-FIN-01`.

### 3.5 `Expense` (`domain/financial/expense.py`)
- **Purpose:** Record non-patient operational costs incurred by the clinic and track when they are paid.
- **Proposed Fields & Signatures:**
  - Fields: `id: UUID`, `clinic_id: UUID`, `category: ExpenseCategory`, `description: str`, `amount: Money`, `incurred_on: date`, `paid_on: date | None`, `supplier_invoice_id: UUID | None`.
  - Methods: `mark_paid(self, *, on_date: date) -> None`.
- **Relationships, Cardinalities & Scope:** `Clinic 1 ── 0..* Expense`; optional `0..1` link to `SupplierInvoice`.
- **States & Transitions:** `UNPAID` (`paid_on is None`) → `PAID` (`paid_on is not None`). Calling `mark_paid` twice raises `InvalidTransitionError`.
- **Errors:** `ValidationError(code="INVALID_VALUE")` if `amount <= 0`, `description` empty, or `paid_on < incurred_on`; `InvalidTransitionError(code="INVALID_TRANSITION")` if already paid.
- **Transaction, Concurrency & Security:** Requires financial administration grant; audited on creation and payment.
- **Examples:**
  - *Valid:* Recording a 50,000 DZD `RENT` expense incurred on `2026-11-01` and marking it paid on `2026-11-05`.
  - *Invalid:* Marking an already paid expense as paid again raises `InvalidTransitionError`.
- **Future Issue & Dependencies:** `ISSUE-S2-FIN-02` (Depends on `ExpenseCategory`, `Money`, `SupplierInvoice`).

### 3.6 `FinancialSummary` (`domain/financial/summary.py`)
- **Purpose:** Read-only reporting projection separating billed revenue, cash inflows, cash outflows, and outstanding receivables over a date interval.
- **Proposed Fields & Signatures:**
  - Fields: `period_start: date`, `period_end: date`, `cash_received: Money`, `cash_paid: Money`, `billed_revenue: Money`, `receivables: Money`.
  - Methods: `net_cash(self) -> Money` (returns `cash_received.subtract(cash_paid)`).
- **Relationships, Cardinalities & Scope:** Pure query projection per `clinic_id`.
- **States & Transitions:** Frozen value object.
- **Errors:** `ValidationError(code="INVALID_VALUE")` if `period_end < period_start` or currencies mismatch.
- **Transaction, Concurrency & Security:** Restricted to `Permission.FINANCE_REPORT`; aggregated server-side via SQL.
- **Examples:**
  - *Valid:* `cash_received = 120,000 DZD`, `cash_paid = 45,000 DZD` yields `net_cash() == 75,000.00 DZD`.
  - *Invalid:* `period_start = 2026-11-30`, `period_end = 2026-11-01` raises `ValidationError`.
- **Future Issue & Dependencies:** `ISSUE-S2-FIN-03` (Depends on `Money`, `Invoice`, `Payment`, `Expense`, `SupplierPayment`).

### 3.7 `Supplier` (`domain/procurement/supplier.py`)
- **Purpose:** Represent an external vendor supplying medical consumables or equipment to the clinic.
- **Proposed Fields & Signatures:**
  - Fields: `id: UUID`, `clinic_id: UUID`, `name: str`, `contact: ContactInfo`, `address: Address | None`, `payment_terms_days: int`, `active: bool`, `version: int = 0`.
  - Methods: `deactivate(self) -> None`.
- **Relationships, Cardinalities & Scope:** `Clinic 1 ── 0..* Supplier`; `Supplier 1 ── 0..* PurchaseOrder`; `Supplier 1 ── 0..* SupplierInvoice`.
- **States & Transitions:** `active=True` → `active=False`. Inactive suppliers cannot receive new purchase orders.
- **Errors:** `ValidationError(code="INVALID_VALUE")` if `name` is blank or `payment_terms_days < 0`.
- **Transaction, Concurrency & Security:** Optimistic locking (`version`); scoped to `clinic_id`.
- **Examples:**
  - *Valid:* Active supplier `"PharmAlliance DZ"` with `payment_terms_days=30`.
  - *Invalid:* `payment_terms_days=-5` raises `ValidationError`.
- **Future Issue & Dependencies:** `ISSUE-S2-PROC-01` (Depends on M2 `ContactInfo` and `Address`).

### 3.8 `PurchaseOrderLine` (`domain/procurement/purchase_order.py`)
- **Purpose:** Immutable line item on a clinic purchase order referencing M3's `Material` catalogue.
- **Proposed Fields & Signatures:**
  - Fields: `material_id: UUID`, `quantity: Decimal`, `unit: str`, `unit_cost: Money`.
  - Methods: `total(self) -> Money` (returns `unit_cost.multiply(quantity)`).
- **Relationships, Cardinalities & Scope:** Owned by `PurchaseOrder` (`1..*`); references M3 `Material.id`.
- **States & Transitions:** Frozen value object.
- **Errors:** `ValidationError(code="INVALID_VALUE")` if `quantity <= 0`, `unit` is empty, or `unit_cost < 0`.
- **Transaction, Concurrency & Security:** Persisted with parent `PurchaseOrder`.
- **Examples:**
  - *Valid:* 10 boxes of examination gloves at `850.00 DZD` yields `total() == 8500.00 DZD`.
  - *Invalid:* `quantity = Decimal("0")` raises `ValidationError`.
- **Future Issue & Dependencies:** `ISSUE-S2-PROC-02` (Depends on M3 `Material` and M5 `Money`).

### 3.9 `PurchaseOrder` (`domain/procurement/purchase_order.py`)
- **Purpose:** Track a clinic's formal order of materials from a `Supplier` and derive delivery progress across partial receipts.
- **Proposed Fields & Signatures:**
  - Fields: `id: UUID`, `clinic_id: UUID`, `supplier_id: UUID`, `lines: tuple[PurchaseOrderLine, ...]`, `status: str`, `ordered_at: datetime | None`, `version: int = 0`.
  - Methods: `send(self, *, at: datetime) -> None`; `cancel(self, reason: str) -> None`; `received_status(self, receipts: Sequence[GoodsReceipt]) -> str`.
- **Relationships, Cardinalities & Scope:** `Supplier 1 ── 0..* PurchaseOrder`; `PurchaseOrder 1 ── 1..* PurchaseOrderLine`; `PurchaseOrder 1 ── 0..* GoodsReceipt`.
- **States & Transitions:** `DRAFT → SENT → PARTIALLY_RECEIVED → RECEIVED`; `DRAFT/SENT → CANCELLED` (only when zero receipts exist).
- **Errors:** `InvalidTransitionError(code="INVALID_TRANSITION")` when cancelling an order with recorded goods receipts or sending an empty order.
- **Transaction, Concurrency & Security:** Versioned aggregate root in `UnitOfWork`.
- **Examples:**
  - *Valid:* Sending a 2-line `DRAFT` order transitions status to `SENT` and sets `ordered_at`.
  - *Invalid:* Cancelling a `PARTIALLY_RECEIVED` order raises `InvalidTransitionError`.
- **Future Issue & Dependencies:** `ISSUE-S2-PROC-03` (Depends on `Supplier`, `PurchaseOrderLine`, `GoodsReceipt`).

### 3.10 `GoodsReceiptLine` (`domain/procurement/goods_receipt.py`)
- **Purpose:** Record the exact quantity and optional batch/lot of a single material delivered in a shipment.
- **Proposed Fields & Signatures:**
  - Fields: `material_id: UUID`, `quantity: Decimal`, `lot_id: UUID | None`.
- **Relationships, Cardinalities & Scope:** Owned by `GoodsReceipt` (`1..*`); references M3 `Material` and optional `StockLot`.
- **States & Transitions:** Frozen value object.
- **Errors:** `ValidationError(code="INVALID_VALUE")` if `quantity <= 0`.
- **Transaction, Concurrency & Security:** Commits atomically with parent `GoodsReceipt` and M3 `StockMovement`.
- **Examples:**
  - *Valid:* Receiving `quantity = Decimal("5")` of `material_id` with `lot_id`.
  - *Invalid:* Negative or zero quantity raises `ValidationError`.
- **Future Issue & Dependencies:** `ISSUE-S2-PROC-04` (Depends on M3 `Material` and `StockLot`).

### 3.11 `GoodsReceipt` (`domain/procurement/goods_receipt.py`)
- **Purpose:** Verify physical delivery against a `SENT` `PurchaseOrder` and trigger corresponding inventory stock receipt movements.
- **Proposed Fields & Signatures:**
  - Fields: `id: UUID`, `clinic_id: UUID`, `order_id: UUID`, `received_at: datetime`, `received_by: UUID`, `lines: tuple[GoodsReceiptLine, ...]`.
  - Methods: `validate_against(self, order: PurchaseOrder, previous: Sequence[GoodsReceipt]) -> None`.
- **Relationships, Cardinalities & Scope:** `PurchaseOrder 1 ── 0..* GoodsReceipt`; scoped to `clinic_id`.
- **States & Transitions:** Immutable posted receipt record.
- **Errors:** `ValidationError(code="INVALID_VALUE")` if an unordered `material_id` appears or cumulative received quantity exceeds ordered quantity.
- **Transaction, Concurrency & Security:** Locks `PurchaseOrder` in UoW; stages `GoodsReceipt` and M3 `StockMovement(kind="RECEIPT")` atomically.
- **Examples:**
  - *Valid:* Two partial receipts of 5 units each against an order of 10 units succeed.
  - *Invalid:* A second receipt of 6 units against a 10-unit order (with 5 already received) raises `ValidationError`.
- **Future Issue & Dependencies:** `ISSUE-S2-PROC-05` (Depends on `PurchaseOrder` and M3 `StockMovement`).

### 3.12 `SupplierInvoice` (`domain/procurement/supplier_invoice.py`)
- **Purpose:** Record a bill issued by a supplier to the clinic and derive the remaining accounts-payable balance.
- **Proposed Fields & Signatures:**
  - Fields: `id: UUID`, `clinic_id: UUID`, `supplier_id: UUID`, `supplier_number: str`, `order_id: UUID | None`, `amount: Money`, `due_on: date`.
  - Methods: `balance(self, payments: Sequence[SupplierPayment]) -> Money`.
- **Relationships, Cardinalities & Scope:** `Supplier 1 ── 0..* SupplierInvoice`; `SupplierInvoice 1 ── 0..* SupplierPayment`; scoped to `clinic_id`.
- **States & Transitions:** Recorded bill; settlement state derived via `balance(payments)`.
- **Errors:** `ValidationError(code="INVALID_VALUE")` if `amount <= 0`, `supplier_number` is empty, or linked payments exceed `amount`.
- **Transaction, Concurrency & Security:** Unique `(clinic_id, supplier_id, supplier_number)` constraint; locked during `SupplierPayment`.
- **Examples:**
  - *Valid:* 20,000 DZD supplier bill with one 8,000 DZD `SupplierPayment` returns `balance() == 12000.00 DZD`.
  - *Invalid:* Blank `supplier_number` raises `ValidationError`.
- **Future Issue & Dependencies:** `ISSUE-S2-PROC-06` (Depends on `Supplier`, `PurchaseOrder`, `SupplierPayment`).

### 3.13 `SupplierPayment` (`domain/procurement/supplier_payment.py`)
- **Purpose:** Record an immutable cash outflow settling all or part of a `SupplierInvoice`.
- **Proposed Fields & Signatures:**
  - Fields: `id: UUID`, `clinic_id: UUID`, `supplier_invoice_id: UUID`, `amount: Money`, `paid_at: datetime`, `paid_by: UUID`, `reference: str`.
- **Relationships, Cardinalities & Scope:** `SupplierInvoice 1 ── 0..* SupplierPayment`; scoped to `clinic_id`.
- **States & Transitions:** Immutable posted settlement record.
- **Errors:** `ValidationError(code="PAYMENT_EXCEEDS_BALANCE")` if `amount` exceeds remaining `SupplierInvoice.balance(...)` or `reference` is blank.
- **Transaction, Concurrency & Security:** Uses row locking on `SupplierInvoice`, idempotency key verification, and `AuditEntry` logging.
- **Examples:**
  - *Valid:* Paying 12,000 DZD on a 12,000 DZD remaining supplier invoice balance settles the bill to 0 DZD.
  - *Invalid:* Paying 12,001 DZD raises `ValidationError(code="PAYMENT_EXCEEDS_BALANCE")`.
- **Future Issue & Dependencies:** `ISSUE-S2-PROC-07` (Depends on `SupplierInvoice` and `Money`).

### 3.14 `PricingPolicy` (`application/ports/pricing.py`)
- **Purpose:** Extension port for future clinic-specific or insurance-tier tax/discount calculation strategies when simple per-line rules are no longer sufficient.
- **Proposed Fields & Signatures:**
  - Protocol method: `calculate(self, subtotal: Money) -> Money`.
- **Relationships, Cardinalities & Scope:** Injected into billing application use cases only when polymorphic pricing rules are required; Week 1 uses the direct deterministic formula on `InvoiceLine`.
- **States & Transitions:** Stateless `Protocol` interface.
- **Errors:** `ValidationError(code="INVALID_VALUE")` if calculated result is negative or changes currency.
- **Transaction, Concurrency & Security:** Pure calculation port; no database or network I/O.
- **Examples:**
  - *Valid:* Standard policy returns quantized `subtotal` plus applicable statutory tax.
  - *Invalid:* Policy returning `USD` for a `DZD` subtotal raises `ValidationError`.
- **Future Issue & Dependencies:** `ISSUE-S2-BILL-04` (Depends on `Money`).
