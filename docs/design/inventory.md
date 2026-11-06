# Inventory — Design Document

**Module:** M3 — Facilities, Scheduling and Inventory Design  
**Sprint:** Week 1  
**Status:** Design only. No Python classes are implemented in Week 1.

> **All models in this document are proposed future design. Nothing here is implemented yet.**

---

## 1. Purpose

This document describes the proposed design for inventory and stock management within the Clinic Management System. Inventory covers consumable materials (drugs, disposables, supplies), their stock levels, movements, and expiry tracking.

---

## 2. Proposed Models

### 2.1 Material

Represents a type of consumable item stocked by the clinic.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `clinic_id` | UUID | Owning clinic |
| `sku` | str | Clinic-scoped stock-keeping unit code |
| `name` | str | Human-readable name |
| `unit` | str | Unit of measure (e.g. `"box"`, `"vial"`, `"mL"`) |
| `reorder_level` | Decimal | Stock quantity below which replenishment is triggered |
| `active` | bool | Whether the material is currently stocked |

**Design notes:**
- `reorder_level` must be non-negative (zero means "never reorder automatically").
- Units must be explicit and consistent — mixing `"box"` and `"unit"` for the same material would cause calculation errors.
- SKUs are clinic-scoped; the same physical product may have different SKUs across clinics.

---

### 2.2 StockMovement

An immutable record of a quantity change for a material.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `clinic_id` | UUID | Clinic scope |
| `material_id` | UUID | Affected material |
| `quantity` | Decimal | Signed quantity: positive = receipt/return, negative = issue/write-off |
| `movement_kind` | enum | `RECEIPT`, `ISSUE`, `ADJUSTMENT`, `RETURN`, `WRITE_OFF` |
| `reason` | str | Human-readable explanation |
| `source_id` | UUID \| None | Optional reference to source document (e.g. appointment_id for issues) |
| `actor_id` | UUID | Staff member recording the movement |
| `occurred_at` | datetime | Timezone-aware timestamp of the physical event |

**Design notes:**
- **Stock movements must be immutable.** Past movements must never be edited or deleted.
- Corrections must be recorded as new adjustment movements with appropriate reasons.
- This creates a full audit trail and enables historical balance reconstruction.
- `occurred_at` is distinct from the recording timestamp to allow back-dating of corrections.

---

### 2.3 StockBalance

A derived projection of the current stock level for a material, computed from all `StockMovement` records.

| Field | Type | Description |
|-------|------|-------------|
| `clinic_id` | UUID | Clinic scope |
| `material_id` | UUID | Material identifier |
| `quantity` | Decimal | Current balance (sum of all movement quantities) |
| `unit` | str | Unit of measure (from Material) |

**Design notes:**
- `StockBalance` is **not an aggregate root** — it is a read-side projection.
- It may be maintained as a denormalised cache (updated on each movement) or computed on demand.
- The balance must never go negative in normal operation. The repository must enforce an atomic decrement with a constraint check to prevent concurrent over-issues.
- Because the balance is derived, it can always be recomputed from movements if the cache becomes inconsistent.

---

### 2.4 StockLot

Tracks a specific received batch of a material for expiry and recall purposes.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `material_id` | UUID | Associated material |
| `batch_code` | str | Manufacturer or supplier batch/lot number |
| `expires_on` | date \| None | Expiry date (None for non-perishable items) |
| `received_on` | date | Date the lot was received at the clinic |

**Design notes:**
- Lots enable FEFO (First Expired, First Out) issuing to minimise waste.
- Lot tracking also enables targeted recalls — if a supplier issues a recall on a batch, the clinic can identify all affected stock and usage.
- `StockMovement` records may optionally reference a `lot_id` to link issues to specific batches.

---

### 2.5 LowStockDetected (Domain Event)

An immutable domain-event hint raised when a material's balance crosses below `reorder_level`.

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | UUID | Unique event identifier |
| `clinic_id` | UUID | Clinic scope |
| `material_id` | UUID | Material that is low |
| `current_balance` | Decimal | Balance at the time of detection |
| `reorder_level` | Decimal | Configured threshold |
| `occurred_at` | datetime | When the threshold was crossed |

**Design notes:**
- `LowStockDetected` is an **immutable observation**, not a command.
- It must not trigger side effects (e.g. sending emails or placing orders) synchronously from within the domain.
- Downstream subscribers (notification service, procurement workflow) handle the event asynchronously.
- Multiple crossings of the same threshold must each produce a separate event — the system must not suppress repeat events.

---

## 3. Proposed Repository Port

### StockRepository

```python
class StockRepository(abc.ABC):
    @abc.abstractmethod
    def balance(self, clinic_id: UUID, material_id: UUID) -> StockBalance: ...

    @abc.abstractmethod
    def append_movement(self, movement: StockMovement) -> None: ...
```

**Notes:**
- `balance()` returns the current projection. Infrastructure may cache this.
- `append_movement()` appends an immutable record and atomically updates the balance projection.
- Atomic decrement: when issuing stock, the repository must enforce `balance - quantity >= 0` using a database constraint or a row-level lock, not just a Python-level check, to prevent concurrent over-issues.

---

## 4. Additional Design Notes

### Stock Units and Quantities
- All quantities use `Decimal` to avoid floating-point rounding errors (critical for drug dosing).
- Units are stored as free-form strings on `Material`; validation rules may be added later.
- Mixing units for the same material (e.g. recording some movements in `"vial"` and others in `"mL"`) is a data quality error; the application layer must validate consistency.

### Negative Stock Prevention
- The balance must never go below zero in normal operation.
- If a movement would cause a negative balance, the repository must reject it with a domain error.
- Write-offs may be an exception if the physical stock is already missing; the reason field must document this.

### Atomic Decrement Requirements
- Issuing stock from a concurrent system (e.g. multiple nurses simultaneously dispensing from the same lot) requires database-level atomicity.
- A Python-level balance check followed by an insert is not sufficient — this is a classic TOCTOU race condition.
- Recommended approach: PostgreSQL advisory lock or `UPDATE … WHERE balance >= issue_qty RETURNING *` with an application-level check on the row count.

### Expiry Tracking
- Stock lots with `expires_on` in the past must be quarantined automatically (or flagged for review).
- FEFO issuing should be enforced by the application layer when creating issue movements.
- Near-expiry alerts (e.g. expiring within 30 days) are a future notification feature.

### Reorder Thresholds
- When `balance < reorder_level`, a `LowStockDetected` event is raised.
- The procurement workflow (M5) subscribes to this event to initiate a purchase order.
- The reorder level is configurable per material per clinic.

### Future Integration with M5 (Billing and Procurement)
- When materials are received via a supplier purchase order (M5), a `StockMovement(kind=RECEIPT)` must be created automatically.
- The `source_id` on the movement references the purchase order ID.
- Cost per unit at time of receipt should be recorded for COGS (cost of goods sold) reporting.
- Drug costs tied to consultations or procedures must reference both the material lot and the clinical event.

### Why Stock Movements Must Be Immutable
Immutability is a core design constraint because:
1. **Audit trail**: Regulatory compliance requires knowing exactly what happened and when.
2. **Historical reconstruction**: The current balance can always be recomputed by replaying all movements.
3. **Concurrency safety**: Immutable append-only records avoid update conflicts.
4. **Error correction**: Mistakes are corrected with new adjustment movements, not by editing history — this preserves a complete record of what was done and what was corrected.
