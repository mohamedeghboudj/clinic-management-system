# Connected visit interface contract v1

**Contract status:** fixed for parallel Sprint 2 implementation. The Python [workflow protocols](../../src/clinic_management/application/ports/visit.py), [messages](../../src/clinic_management/application/contracts/visit.py) and [transaction bundle](../../src/clinic_management/application/ports/visit_transaction.py) are importable now. HTTP handlers, remote repositories, the event dispatcher and desktop screens are Sprint 2 deliverables. Change a shared signature through a reviewed PR covering its consumers.

## Transport and data

All routes below have prefix `/api/v1`. Except for readiness, HTTP carries `Authorization: Bearer <access token>` and `X-Clinic-ID` (UUID). Verify both on every request. Desktop sign-in/refresh/sign-out use Supabase Auth with the public project URL and publishable key. The backend resolves the verified subject, current enabled membership and scoped grants. The fixed integration boundary is `IdentityProvider.resolve_principal(access_token, *, clinic_id, at) -> Principal`. Resolve sign-in clinic context via the configured staff clinic. Disable self-enrollment for staff. Never pass a client-supplied principal, role or assignment through to a workflow.

Each mutation requires `Idempotency-Key: <UUID>`. Mutations whose Python signature contains `expected_version` additionally require `If-Match: "<integer>"`; for payments and reversals it is the **invoice** version. Generate a correlation UUID on the server. Construct CommandContext from authenticated data and headers. Enforce authorization before either execution or returning any cached result. Replay lookup precedes the version comparison for a previously committed identical command.

| Route | Python target | Body fields (GET uses query) | Response |
| --- | --- | --- | --- |
| `GET /health/ready` | `VisitGateway.ready` | â€” | `ComponentHealth` |
| `GET /commands/{key}` | `VisitGateway.command_status` | â€” | `CommandReceipt \| None` |
| `WS /events` | `VisitGateway.changes` | â€” | `Iterator[ChangeHint]` |
| `GET /me` | `PatientWorkflow.me` | â€” | `Principal` |
| `POST /patients` | `PatientWorkflow.register` | given_name, family_name, contact, birth_date | `CommandReceipt` |
| `GET /patients` | `PatientWorkflow.search` | query, limit, cursor | `Page[PatientSummary]` |
| `POST /appointments` | `BookingWorkflow.book` | patient_id, doctor_id, room_id, slot | `CommandReceipt` |
| `POST /appointments/{appointment_id}/check-in` | `BookingWorkflow.check_in` | â€” | `CommandReceipt` |
| `GET /appointments` | `BookingWorkflow.schedule` | doctor_id, day, limit, cursor | `Page[AppointmentSummary]` |
| `POST /consultations` | `ClinicalWorkflow.start` | appointment_id, note | `CommandReceipt` |
| `PATCH /consultations/{consultation_id}/note` | `ClinicalWorkflow.save_note` | note | `CommandReceipt` |
| `POST /consultations/{consultation_id}/finalize` | `ClinicalWorkflow.finalize` | â€” | `CommandReceipt` |
| `POST /clinical-entries/{entry_id}/amendments` | `ClinicalWorkflow.amend` | reason, replacement_content | `CommandReceipt` |
| `POST /prescriptions` | `ClinicalWorkflow.prescribe` | consultation_id, items | `CommandReceipt` |
| `GET /patients/{patient_id}/history` | `ClinicalWorkflow.history` | limit, cursor | `Page[ClinicalEntrySummary]` |
| `GET /services` | `ClinicalWorkflow.services` | limit, cursor | `Page[ServiceSnapshot]` |
| `POST /invoices` | `BillingWorkflow.draft` | patient_id, consultation_id, service_ids | `CommandReceipt` |
| `POST /invoices/{invoice_id}/issue` | `BillingWorkflow.issue` | due_on | `CommandReceipt` |
| `POST /invoices/{invoice_id}/payments` | `BillingWorkflow.pay` | amount, method | `CommandReceipt` |
| `POST /payments/{payment_id}/reversals` | `BillingWorkflow.reverse` | amount, reason | `CommandReceipt` |
| `GET /invoices/{invoice_id}/balance` | `BillingWorkflow.balance` | â€” | `BalanceSummary` |
| `GET /invoices/{invoice_id}` | `BillingWorkflow.summary` | â€” | `InvoiceSummary` |
| `POST /appointments/{appointment_id}/cancel` | `BookingWorkflow.cancel` | reason | `CommandReceipt` |
| `POST /appointments/{appointment_id}/reschedule` | `BookingWorkflow.reschedule` | slot | `CommandReceipt` |
| `POST /appointments/{appointment_id}/complete` | `BookingWorkflow.complete` | â€” | `CommandReceipt` |
| `GET /booking-resources` | `BookingWorkflow.resources` | kind, limit, cursor | `Page[BookingResource]` |
| `GET /consultations/{consultation_id}` | `ClinicalWorkflow.consultation` | â€” | `ConsultationView` |
| `GET /clinical-entries/{entry_id}` | `ClinicalWorkflow.corrections` | â€” | `EntryHistory` |

- HTTP 200 for successful reads and committed commands including repeat calls. The command result fields are `key, operation, resource_id, resource_version, committed_at`. Operation is the Python method qualified with its protocol name. Payment and reversal receipts identify the new payment/reversal; resource_version is the resulting **invoice** version. An append-only creation with no version has version zero. Fetch permitted details using a read endpoint. Never store clinical text or tokens in a receipt.
- `GET /commands/{key}` returns the same receipt, or 404 when no committed result is visible for that clinic and actor. Concurrent uncommitted work can also produce 404. Retain the key, retry within a deadline, and repeat only the identical command. HTTP 409 for payload reuse or a stale version, 422 for malformed data, 401 for invalid/expired identity, 403 for denied operations, 404 for invisible resources, 503 for transient dependency failure. JSON error is `{"code":"â€¦","message_key":"â€¦","correlation_id":"â€¦"}`.
- Wire object field names match the frozen Python DTOs. Serialize Money as `{"amount":"400.00","currency":"DZD"}`, TimeSlot as `{"start":"â€¦Z","end":"â€¦Z"}`, ContactInfo as `{"phone":null,"email":"â€¦"}`. PrescriptionItem contains medication {name,strength,form}, dose, route, frequency, duration, instructions. UUIDs are canonical strings, dates ISO, timestamps UTC with offset, enum values are strings, tuples are arrays. Optional values are nullable. Page is `{items,next_cursor}`. Default limit 25, allowed 1â€“100. Sorting must be stable and cursor-bound to clinic, filters and order. Reject unknown fields.
- Response projections are the named types in [contracts](../../src/clinic_management/application/contracts/). History summaries exclude narrative. The model `BalanceSummary` includes invoice_id, total, net_paid, outstanding, settlement. Fetch the invoice summary for its optimistic version. The role-specific presenter obtains resource IDs from receipts; no peer guesses another serviceâ€™s IDs.
- The desktop socket is a native authenticated Upgrade with the same bearer and clinic headers over WSS. One JSON ChangeHint per text frame. Only authorized subscriptions receive the entity ID and version. Recheck grant/membership for each delivery and reconnect; disconnect revoked users. On reconnect reload permitted views by HTTPS. Use a background worker and marshal updates onto the GUI thread. No credentials in the URL.
- Server-generated actor, timestamps, totals and catalogue prices may not be posted by a client. For the initial invoice-from-visit operation, each distinct selected service produces one line, quantity 1, discount and tax zero. Broader pricing rules remain in the backlog. Retain the original money modelâ€™s exact rounding rules.

## Transactions and dependency injection

The API composition root injects one implementation per Protocol. The workflow opens one `with transactions(clinic_id=principal.clinic_id) as tx`. Every repository on tx uses that same database connection. Existing methods on PatientRepository, AppointmentRepository, ClinicalRepository, ServiceCatalogRepository, InvoiceRepository and PaymentRepository retain their exact signatures. Use scoped reads that return None for invisible rows. Compose patient details through allowed fields, then return the summary. Billing calls `tx.billing_source.snapshot(clinic_id, patient_id, consultation_id, service_id) -> ServiceSnapshot`. The clinical adapter checks that the finalized visit belongs to the named patient and clinic, and reads the active service on that same transaction. The authorized billing workflow receives only the service ID, description and price.

1. Re-resolve membership and authorize using trusted resource facts. Construct the digest from the validated operation, route, version and body. Acquire a transaction lock for the scoped key via `tx.receipts.lock_and_find(ctx, operation=â€¦, digest=â€¦)`. If found, return the same receipt after authorization. On mismatched input raise ConflictError.
2. For a new command, load and lock the affected aggregate. Compare the observed version. Mutate using the domain methods and save with the existing expected-version port. A payment or reversal also advances the locked invoice version. Lock and validate invoice before payment on reversals. Enforce tenant constraints at SQL and application boundaries.
3. Save the receipt, stage audit and DomainEvent on tx, and call commit once. An exception or context exit before commit rolls back every write. The dispatcher publishes **after commit**. A publisher failure leaves the committed command visible, and dispatch retries the original event.
4. Desktop writes only to this API. Run unit tests using deterministic fakes for these ports. Validate real transaction races, failed acknowledgments and authorized sync against isolated remote synthetic data before accepting the sprint.

## Round trip for the demo

Register patient â†’ book â†’ check in â†’ start and finalize consultation â†’ issue prescription â†’ create and issue invoice â†’ record payment. Use the returned IDs and versions at each step. With a 1,000.00 DZD invoice, paying 400.00 DZD leaves 600.00 DZD. Drop the response after commit, query with the same key, repeat the request and verify there is one payment and one original receipt. A second authorized desktop refetches the balance. The secretary is denied access to the clinical history.
