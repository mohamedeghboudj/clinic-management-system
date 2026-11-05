# Clinical Care Module — Design Specification

**Author:** M4 (Clinical Care Lead)  
**Sprint:** Sprint 1 — Week 1 Design Deliverable  
**Status:** DESIGN ONLY — Specification for future increments. No production Python classes are created for these models in Week 1.

---

## 1. Overview and Architectural Boundaries

The clinical care domain manages the patient's medical records, consultations, prescriptions, amendments, treatment plans, allergies, laboratory workflows, and surgical procedures.

In Sprint 1 (Week 1), core consultation finalization, immutable record entries, amendments, written prescriptions, and billable service items are **built** as pure Python domain models. The remaining models detailed below are **designed** for implementation in subsequent increments.

All clinical facts are strictly scoped to a `clinic_id` to enforce tenant isolation. Access requires an authenticated `Principal` with verified doctor-patient care assignment (`Permission.CLINICAL_READ`, `Permission.CLINICAL_WRITE`, or `Permission.PRESCRIBE`). Business ownership alone never grants access to clinical narratives.

---

## 2. Design-Only Clinical Models

### 2.1 MedicalRecord (Logical Patient History Boundary)

* **Purpose:** Represents the logical aggregation boundary of a patient's clinical history within a clinic. Does not load a patient's entire lifetime history into one in-memory list; instead, delegates to a paginated query service.
* **Proposed Properties:**
  * `clinic_id: UUID` (Clinic boundary)
  * `patient_id: UUID` (Associated patient)
* **Proposed Operations:**
  * `history(self, query: HistoryQuery) -> Page[ClinicalEntrySummary]` (Query projection, not an aggregate method that mutates state)
* **Relationships & Cardinalities:**
  * `Clinic 1 ── * MedicalRecord`
  * `Patient 1 ── 0..1 MedicalRecord` (One logical record per patient per clinic)
  * `MedicalRecord 1 ── * ClinicalEntry` (Read-only paginated relationship)
* **Allowed States & Transitions:**
  * Stateless logical anchor. Patient archiving disables write access via the application use cases.
* **Error Handling:**
  * `NotFoundError(code="PATIENT_NOT_FOUND", message_key="patient.not_found")`
  * `PermissionDeniedError(code="ACCESS_DENIED", message_key="clinical.access_denied")`
* **Concurrency, Transactions & Security:**
  * Read-only projection queries; no row-level locking needed.
  * Access policy checks caller's assignment to the patient before returning clinical summaries.
* **Examples:**
  * *Normal:* Querying page 1 (limit 25) of clinical entries for patient `P-101` returns 12 summaries with continuation cursor `None`.
  * *Invalid:* Requesting page with limit 150 raises `ValidationError(code="INVALID_VALUE", message_key="paging.limit.invalid")`.
* **Future Issue / Dependency:** Issue `#CLIN-01` (Week 2 Query Service), depends on M2 `Patient` and M1 `PageRequest`.

---

### 2.2 Allergy

* **Purpose:** Records patient adverse drug reactions, food allergies, and substance sensitivities to alert clinicians during prescribing and consultation.
* **Proposed Properties:**
  * `id: UUID` (Unique identity)
  * `clinic_id: UUID` (Tenant scope)
  * `patient_id: UUID` (Target patient)
  * `substance: str` (Allergen name, e.g., "Penicillin G")
  * `reaction: str | None` (Observed clinical reaction, e.g., "Anaphylaxis", "Urticaria")
  * `status: str` (`"ACTIVE"`, `"RESOLVED"`, `"ENTERED_IN_ERROR"`)
  * `recorded_by: UUID` (Clinician actor ID)
  * `recorded_at: datetime` (UTC instant)
* **Proposed Operations:**
  * `mark_entered_in_error(self, reason: str, *, at: datetime) -> None`: Preserves the record with audit trail rather than physical deletion.
  * `resolve(self, *, at: datetime) -> None`: Marks the allergy as resolved if no longer clinically active.
* **Relationships & Cardinalities:**
  * `Patient 1 ── * Allergy`
  * `DoctorProfile 1 ── * Allergy` (Recorded by)
* **Allowed States & Transitions:**
  * `ACTIVE → RESOLVED`
  * `ACTIVE → ENTERED_IN_ERROR`
  * `RESOLVED → ENTERED_IN_ERROR`
  * `ENTERED_IN_ERROR` is terminal; cannot transition to `ACTIVE`.
* **Error Handling:**
  * `InvalidTransitionError(code="INVALID_TRANSITION", message_key="clinical.allergy.already_entered_in_error")`
  * `ValidationError(code="INVALID_VALUE", message_key="clinical.allergy.substance.empty")`
* **Concurrency, Transactions & Security:**
  * Stored in patient clinical record table with foreign key `patient_id`.
  * Requires `Permission.CLINICAL_WRITE` to record or amend.
* **Examples:**
  * *Normal:* Doctor records active Penicillin allergy with reaction "Severe rash".
  * *Invalid:* Attempting to reactivate an allergy that was marked `ENTERED_IN_ERROR` raises `InvalidTransitionError`.
* **Future Issue / Dependency:** Issue `#CLIN-02` (Sprint 2 Clinical Safety), depends on M2 `DoctorProfile`.

---

### 2.3 TreatmentPlan

* **Purpose:** Outlines structured clinical goals, interventions, and scheduled reviews for chronic conditions or postoperative care.
* **Proposed Properties:**
  * `id: UUID`
  * `clinic_id: UUID`
  * `patient_id: UUID`
  * `author_id: UUID` (Attending physician)
  * `description: str` (Clinical regimen and targets)
  * `started_on: date` (Treatment start date)
  * `ended_on: date | None` (Actual completion date)
  * `status: str` (`"ACTIVE"`, `"COMPLETED"`, `"CANCELLED"`)
* **Proposed Operations:**
  * `complete(self, *, on_date: date) -> None`: Transitions to `COMPLETED` and sets `ended_on`.
  * `cancel(self, reason: str, *, on_date: date) -> None`: Transitions to `CANCELLED` with recorded reason.
* **Relationships & Cardinalities:**
  * `Patient 1 ── * TreatmentPlan`
  * `TreatmentPlan 1 ── * Consultation` (Linked follow-up visits)
* **Allowed States & Transitions:**
  * `ACTIVE → COMPLETED`
  * `ACTIVE → CANCELLED`
  * `COMPLETED` and `CANCELLED` are terminal states.
* **Error Handling:**
  * `InvalidTransitionError(code="INVALID_TRANSITION", message_key="clinical.treatment_plan.not_active")`
  * `ValidationError(code="INVALID_VALUE", message_key="clinical.treatment_plan.dates.invalid")` (if `ended_on < started_on`)
* **Concurrency, Transactions & Security:**
  * Optimistic versioning (`version: int`).
  * Only assigned doctors may complete or cancel a plan.
* **Examples:**
  * *Normal:* Doctor completes 3-month hypertension management plan on `2026-11-01`.
  * *Invalid:* Attempting to complete a plan with `ended_on` before `started_on` raises `ValidationError`.
* **Future Issue / Dependency:** Issue `#CLIN-03` (Sprint 2 Care Plans), depends on M2 `DoctorProfile`.

---

### 2.4 AttachmentMetadata

* **Purpose:** Stores metadata and security scanning status for medical binary attachments (e.g., DICOM scans, ultrasound images, PDF discharge letters). The binary payload is stored in private cloud object storage, never in the transactional PostgreSQL database.
* **Proposed Properties:**
  * `id: UUID`
  * `clinic_id: UUID`
  * `patient_id: UUID`
  * `storage_key: str` (Remote S3/Supabase Storage bucket object path)
  * `media_type: str` (MIME type, e.g. `"application/pdf"`, `"image/png"`)
  * `size_bytes: int` (Positive integer, max 50 MB per file)
  * `sha256: str` (Cryptographic digest for tamper detection)
  * `scan_status: str` (`"PENDING"`, `"CLEAN"`, `"INFECTED"`)
  * `uploaded_by: UUID` (Actor account ID)
* **Proposed Operations:**
  * `mark_scan_result(self, *, clean: bool) -> None`: Updates scan status to `CLEAN` or `INFECTED`. Download links are only generated for `CLEAN` attachments.
* **Relationships & Cardinalities:**
  * `Patient 1 ── * AttachmentMetadata`
  * `Consultation 0..1 ── * AttachmentMetadata`
* **Allowed States & Transitions:**
  * `PENDING → CLEAN`
  * `PENDING → INFECTED`
  * Terminal: Once scanned, status cannot return to `PENDING`.
* **Error Handling:**
  * `ValidationError(code="INVALID_VALUE", message_key="attachment.size_exceeded")`
  * `PermissionDeniedError(code="ATTACHMENT_NOT_CLEAN", message_key="attachment.quarantined")`
* **Concurrency, Transactions & Security:**
  * Binary files downloaded only through short-lived presigned URLs after authorization verification.
  * Audit log entry created on every download request.
* **Examples:**
  * *Normal:* Clean PDF attachment of 2.4 MB with SHA-256 digest verified.
  * *Invalid:* Uploading a file of 75 MB raises `ValidationError(code="INVALID_VALUE", message_key="attachment.size_exceeded")`.
* **Future Issue / Dependency:** Issue `#CLIN-04` (Sprint 3 Storage Adapter), depends on Cloud Storage S3 bucket integration.

---

### 2.5 ProcedureType

* **Purpose:** Defines standardized surgical or minor clinical procedures, linking clinical operations to billing items without embedding billing logic in the clinical domain.
* **Proposed Properties:**
  * `id: UUID`
  * `clinic_id: UUID`
  * `code: str` (Unique procedural code, e.g. `"PROC-APP-01"`)
  * `description: str` (e.g. `"Laparoscopic Appendectomy"`)
  * `service_id: UUID` (Reference to `ServiceCatalogItem` for invoicing)
* **Proposed Operations:**
  * `update_service_link(self, service_id: UUID) -> None`: Updates the linked billing service.
* **Relationships & Cardinalities:**
  * `Clinic 1 ── * ProcedureType`
  * `ProcedureType 1 ── 1 ServiceCatalogItem`
  * `ProcedureType 1 ── * Surgery`
* **Allowed States & Transitions:**
  * Active catalogue item; soft deactivation prevents assignment to new procedures.
* **Error Handling:**
  * `ConflictError(code="CODE_EXISTS", message_key="procedure.code.duplicate")`
* **Concurrency, Transactions & Security:**
  * Unique constraint on `(clinic_id, code)`.
* **Examples:**
  * *Normal:* Procedure `"PROC-SUT-01"` ("Wound Suture") linked to catalog item with price 3,500 DZD.
  * *Invalid:* Creating procedure with blank code raises `ValidationError`.
* **Future Issue / Dependency:** Issue `#CLIN-05` (Sprint 2 Operating Room / Procedures), depends on `ServiceCatalogItem`.

---

### 2.6 SurgeryTeamMember & Surgery

* **Purpose:** Represents an operating room surgery involving a multi-disciplinary team (lead surgeon, assistant, anesthesiologist, scrub nurse) and unified resource reservations.
* **Proposed Properties:**
  * `SurgeryTeamMember` (Frozen Line):
    * `staff_id: UUID` (Staff profile reference)
    * `role: str` (`"LEAD_SURGEON"`, `"ASSISTANT_SURGEON"`, `"ANESTHESIOLOGIST"`, `"SCRUB_NURSE"`)
  * `Surgery` (Aggregate Root):
    * `id: UUID`
    * `clinic_id: UUID`
    * `patient_id: UUID`
    * `procedure_id: UUID`
    * `lead_doctor_id: UUID`
    * `team: tuple[SurgeryTeamMember, ...]`
    * `reservation_ids: tuple[UUID, ...]` (Unified M3 doctor/operating-room/equipment reservations)
    * `status: str` (`"PLANNED"`, `"IN_PROGRESS"`, `"COMPLETED"`, `"CANCELLED"`)
* **Proposed Operations:**
  * `start(self, *, at: datetime) -> None`: Moves from `PLANNED` to `IN_PROGRESS`.
  * `complete(self, *, at: datetime) -> None`: Moves from `IN_PROGRESS` to `COMPLETED`.
  * `cancel(self, reason: str, *, at: datetime) -> None`: Cancels and releases all associated resource reservations.
* **Relationships & Cardinalities:**
  * `Patient 1 ── * Surgery`
  * `Surgery 1 ── 1 ProcedureType`
  * `Surgery 1 ── 1..* SurgeryTeamMember`
  * `Surgery 1 ── 1..* ResourceReservation` (M3 unified reservations)
* **Allowed States & Transitions:**
  * `PLANNED → IN_PROGRESS → COMPLETED`
  * `PLANNED → CANCELLED`
  * `IN_PROGRESS → CANCELLED` (requires emergency post-op incident reason)
* **Error Handling:**
  * `InvalidTransitionError(code="INVALID_TRANSITION", message_key="surgery.already_completed")`
  * `ConflictError(code="RESOURCE_CONFLICT", message_key="surgery.room_unavailable")`
* **Concurrency, Transactions & Security:**
  * Atomic transaction releases or claims doctor, room, and equipment reservations together with surgical state.
* **Examples:**
  * *Normal:* Appendectomy with lead surgeon, anesthesiologist, and scrub nurse transitioning `PLANNED` → `IN_PROGRESS` → `COMPLETED`.
  * *Invalid:* Attempting to start a surgery that has already been cancelled raises `InvalidTransitionError`.
* **Future Issue / Dependency:** Issue `#CLIN-06` (Sprint 3 Inpatient & Surgery), depends on M3 `ResourceReservation`.

---

### 2.7 Laboratory Orders & Results (LabTestType, LabOrderItem, LabOrder, LabResult)

* **Purpose:** Handles diagnostic lab requisitions, sample collection tracking, and entry of test results with reference intervals.
* **Proposed Properties:**
  * `LabTestType`:
    * `id: UUID`, `clinic_id: UUID`, `code: str`, `name: str`, `result_kind: str` (`"NUMERIC"`, `"TEXTUAL"`, `"PANEL"`), `unit: str | None`, `service_id: UUID`
  * `LabOrderItem` (Frozen Line):
    * `test_type_id: UUID`, `instructions: str | None`
  * `LabOrder`:
    * `id: UUID`, `clinic_id: UUID`, `patient_id: UUID`, `doctor_id: UUID`, `items: tuple[LabOrderItem, ...]`, `status: str` (`"ORDERED"`, `"COLLECTED"`, `"RESULTED"`, `"VALIDATED"`, `"CANCELLED"`), `ordered_at: datetime`
  * `LabResult`:
    * `id: UUID`, `clinic_id: UUID`, `order_id: UUID`, `test_type_id: UUID`, `value: Decimal | str`, `unit: str | None`, `reference_text: str | None`, `entered_by: UUID`, `validated_by: UUID | None`, `recorded_at: datetime`
* **Proposed Operations:**
  * `LabOrder.mark_collected(self, *, at: datetime) -> None`
  * `LabOrder.cancel(self, reason: str) -> None`
  * `LabResult.validate_result(self, validator_id: UUID, *, at: datetime) -> None`
  * Amendments to lab results follow the same linked correction pattern as `ClinicalAmendment` without erasing provenance.
* **Relationships & Cardinalities:**
  * `Patient 1 ── * LabOrder 1 ── 1..* LabOrderItem 1 ── 1 LabTestType`
  * `LabOrder 1 ── 0..* LabResult`
* **Allowed States & Transitions:**
  * `ORDERED → COLLECTED → RESULTED → VALIDATED`
  * `ORDERED → CANCELLED`
* **Error Handling:**
  * `InvalidTransitionError(code="INVALID_TRANSITION", message_key="lab.order.already_validated")`
  * `ValidationError(code="INVALID_VALUE", message_key="lab.result.invalid_numeric_value")`
* **Concurrency, Transactions & Security:**
  * Only staff with laboratory role can enter results; a distinct licensed clinician must validate results.
* **Examples:**
  * *Normal:* Fasting blood glucose ordered, collected, resulted at `5.8 mmol/L` (reference `3.9 - 6.1`), and validated.
  * *Invalid:* Marking an order collected without items raises `ValidationError`.
* **Future Issue / Dependency:** Issue `#CLIN-07` (Sprint 3 Laboratory Orders).

---

## 3. Future Application Use-Case Contracts

These command and query boundaries will be implemented in Week 2 under `application/clinical/`:

### 3.1 FinalizeConsultation

```python
class FinalizeConsultation:
    """Authorize attending doctor, finalize consultation, and create history entry atomically."""

    def execute(
        self,
        consultation_id: UUID,
        expected_version: int,
        principal: Principal,
    ) -> ConsultationDetail:
        """Finalize draft consultation inside a single transactional Unit of Work.

        Workflow:
            1. AccessPolicy.require(principal, Permission.CLINICAL_WRITE, resource)
            2. consultation = clinical_repo.get_consultation(clinic_id, consultation_id)
            3. consultation.finalize(at=clock.now())
            4. entry = ClinicalEntry(
                   id=id_gen.new_id(),
                   clinic_id=clinic_id,
                   patient_id=consultation.patient_id,
                   consultation_id=consultation.id,
                   author_id=consultation.doctor_id,
                   kind="consultation_note",
                   content=consultation.note,
                   recorded_at=clock.now(),
               )
            5. clinical_repo.save_consultation(consultation, expected_version=expected_version)
            6. clinical_repo.append_entry(entry)
            7. uow.stage_event(DomainEvent(event_type="CONSULTATION_FINALIZED", ...))
            8. uow.commit()
            9. return consultation_to_response(consultation, allowed_fields)
        """
        ...
```

### 3.2 IssuePrescription

```python
class IssuePrescription:
    """Authorize prescriber, validate items, and issue prescription atomically."""

    def execute(
        self,
        prescription_id: UUID,
        expected_version: int,
        principal: Principal,
    ) -> PrescriptionDetail:
        """Validate items >= 1 and transition prescription to ISSUED inside UoW.

        Workflow:
            1. AccessPolicy.require(principal, Permission.PRESCRIBE, resource)
            2. prescription = clinical_repo.get_prescription(clinic_id, prescription_id)
            3. prescription.issue(at=clock.now())
            4. clinical_repo.save_prescription(prescription, expected_version=expected_version)
            5. uow.stage_event(DomainEvent(event_type="PRESCRIPTION_ISSUED", ...))
            6. uow.commit()
            7. return prescription_to_response(prescription)
        """
        ...
```

### 3.3 consultation_to_response (Safe Field-Filtered Transport DTO)

```python
@dataclass(frozen=True, kw_only=True)
class ConsultationDetail:
    """Safe response DTO for consultation presentation.

    Attributes:
        id: UUID string
        clinic_id: UUID string
        patient_id: UUID string
        doctor_id: UUID string
        appointment_id: UUID string
        note: Note content (included only if authorized)
        status: ConsultationStatus value
        created_at: ISO 8601 aware UTC timestamp
        finalized_at: ISO 8601 aware UTC timestamp or None
        version: Integer version counter
    """
    id: UUID
    clinic_id: UUID
    patient_id: UUID
    doctor_id: UUID
    appointment_id: UUID
    note: str
    status: ConsultationStatus
    created_at: datetime
    finalized_at: datetime | None
    version: int
```

---

## 4. Traceability Matrix

| Requirement / Blueprint Outcome | Domain Model (Week 1) | Design Spec (Week 1) | Target Use Case (Week 2) |
|---|---|---|---|
| S4: Doctor records draft consultation and finalizes it | `Consultation`, `validation.py` | Section 3.1 | `FinalizeConsultation` |
| S4: Finalized content amended without rewriting history | `ClinicalEntry`, `ClinicalAmendment` | Section 2.1 | `AmendClinicalEntry` |
| S4: Doctor issues written prescription with line items | `Prescription`, `PrescriptionItem`, `Medication` | Section 3.2 | `IssuePrescription` |
| S5: Billable consultation items retain catalogue prices | `ServiceCatalogItem` | Section 2.5 | `CreateInvoiceFromServices` |
| Future surgical workflows and operating room reservations | — | Section 2.6 | `ScheduleSurgery` |
| Future laboratory orders and validated results | — | Section 2.7 | `OrderLabTests`, `ValidateLabResult` |
