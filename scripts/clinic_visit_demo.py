"""Run the Week 1 exit scenario with synthetic records and the team's memory transaction."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from datetime import time, timedelta
from decimal import Decimal
from uuid import UUID

from clinic_management.domain.access.audit import AuditEntry
from clinic_management.domain.access.enums import AccessScope, Permission, Role
from clinic_management.domain.access.grants import RoleGrant
from clinic_management.domain.access.policy import AccessPolicy, ResourceContext
from clinic_management.domain.access.principal import Principal
from clinic_management.domain.billing.balance import calculate_balance, validate_payment
from clinic_management.domain.billing.enums import PaymentMethod, SettlementStatus
from clinic_management.domain.billing.invoice import Invoice
from clinic_management.domain.billing.invoice_line import InvoiceLine
from clinic_management.domain.billing.payment import Payment
from clinic_management.domain.billing.reversal import validate_reversal
from clinic_management.domain.clinical.amendment import ClinicalAmendment
from clinic_management.domain.clinical.consultation import Consultation
from clinic_management.domain.clinical.medication import Medication
from clinic_management.domain.clinical.prescription import Prescription, PrescriptionItem
from clinic_management.domain.clinical.record_entry import ClinicalEntry
from clinic_management.domain.facilities.clinic import Clinic
from clinic_management.domain.facilities.enums import RoomType
from clinic_management.domain.facilities.opening_hours import OpeningHours, OpeningPeriod
from clinic_management.domain.facilities.room import Room
from clinic_management.domain.people.doctor_profile import DoctorProfile
from clinic_management.domain.people.patient import Patient
from clinic_management.domain.people.person import Person
from clinic_management.domain.people.staff_profile import StaffProfile
from clinic_management.domain.scheduling.appointment import Appointment
from clinic_management.domain.shared.contact import ContactInfo
from clinic_management.domain.shared.entity import Entity
from clinic_management.domain.shared.errors import (
    InvalidTransitionError,
    PermissionDeniedError,
    ValidationError,
)
from clinic_management.domain.shared.events import DomainEvent
from clinic_management.domain.shared.money import Money
from clinic_management.domain.shared.time_slot import TimeSlot
from tests.support.fixtures import FIXED_TIME
from tests.support.store import MemoryStore
from tests.support.unit_of_work import MemoryUnitOfWork


def _authorize(doctor: DoctorProfile, patient: Patient, account: UUID, cashier_id: UUID) -> None:
    """Check the assigned doctor's clinical permissions and deny the same request to reception.

    Args:
        doctor: Doctor assigned to the visit.
        patient: Patient whose clinical record will be accessed.
        account: Synthetic doctor's account ID.
        cashier_id: Account with clinic-scoped invoicing and payment grants.
    """
    permissions = (Permission.CLINICAL_WRITE, Permission.PRESCRIBE)
    grants = tuple(
        RoleGrant(
            role=Role.DOCTOR, permission=permission, scope=AccessScope.ASSIGNED, fields=frozenset()
        )
        for permission in permissions
    )
    billing_permissions = (Permission.BILLING_WRITE, Permission.PAYMENT_RECORD)
    cashier_grants = tuple(
        RoleGrant(
            role=Role.SECRETARY, permission=permission, scope=AccessScope.CLINIC, fields=frozenset()
        )
        for permission in billing_permissions
    )
    policy = AccessPolicy(grants=grants + cashier_grants)
    principal = Principal(
        account_id=account,
        clinic_id=patient.clinic_id,
        membership_id=UUID(int=90),
        staff_id=doctor.staff_id,
        patient_id=None,
        roles=frozenset({Role.DOCTOR}),
        auth_version=1,
    )
    resource = ResourceContext(
        clinic_id=patient.clinic_id,
        patient_id=patient.id,
        assigned_staff_ids=frozenset({doctor.staff_id}),
        available_fields=frozenset(),
    )
    for permission in permissions:
        policy.require(principal, permission, resource)
    cashier = replace(
        principal,
        account_id=cashier_id,
        membership_id=UUID(int=91),
        staff_id=UUID(int=92),
        roles=frozenset({Role.SECRETARY}),
    )
    for permission in billing_permissions:
        policy.require(cashier, permission, resource)
    try:
        policy.require(
            cashier,
            Permission.CLINICAL_WRITE,
            resource,
        )
    except PermissionDeniedError:
        return
    raise RuntimeError("An unauthorized clinical write was accepted")


def _register(
    ids: Iterator[UUID], store: MemoryStore
) -> tuple[Clinic, Room, DoctorProfile, Patient]:
    """Register a clinic, room and linked staff and patient identities.

    Args:
        ids: Deterministic source of synthetic IDs.
        store: In-memory store for this visit.

    Returns:
        The clinic and participants for scheduling.
    """
    contact = ContactInfo(email="demo@example.invalid")
    hours = OpeningHours(
        timezone="UTC",
        periods=(
            OpeningPeriod(weekday=FIXED_TIME.weekday(), opens_at=time(8), closes_at=time(17)),
        ),
    )
    clinic = Clinic(
        id=next(ids),
        name="Synthetic clinic",
        contact=contact,
        timezone="UTC",
        currency="DZD",
        opening_hours=hours,
    )
    room = Room(
        id=next(ids), clinic_id=clinic.id, number="01", kind=RoomType.CONSULTATION, capacity=2
    )
    clinician = Person(id=next(ids), given_name="Demo", family_name="Clinician", contact=contact)
    recipient = Person(id=next(ids), given_name="Demo", family_name="Patient", contact=contact)
    staff = StaffProfile(
        id=next(ids),
        clinic_id=clinic.id,
        person_id=clinician.id,
        staff_number="S-001",
        hired_on=FIXED_TIME.date(),
    )
    doctor = DoctorProfile(
        id=next(ids),
        clinic_id=clinic.id,
        staff_id=staff.id,
        specialty="General",
        licence_number="DEMO-01",
    )
    patient = Patient(
        id=next(ids), clinic_id=clinic.id, person_id=recipient.id, patient_number="P-001"
    )
    store.replace_collection("people", {clinician.id: clinician, recipient.id: recipient})
    for entity in (clinic, room, staff, doctor, patient):
        store.replace_collection(type(entity).__name__, {entity.id: entity})
    return clinic, room, doctor, patient


def _visit(
    ids: Iterator[UUID], store: MemoryStore, account: UUID, cashier_id: UUID
) -> Consultation:
    """Check in, authorize treatment, finalize the note and issue the linked prescription.

    Args:
        ids: Synthetic identifiers.
        store: Transaction store for the demo.
        account: Doctor's account ID.
        cashier_id: Account recording the invoice and payment.

    Returns:
        Finalized consultation for billing.
    """
    clinic, room, doctor, patient = _register(ids, store)
    slot = TimeSlot(start=FIXED_TIME, end=FIXED_TIME + timedelta(minutes=30))
    if not room.is_bookable() or not clinic.opening_hours.covers(slot):
        raise RuntimeError("Synthetic slot is unavailable")
    appointment = Appointment(
        id=next(ids),
        clinic_id=clinic.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        room_id=room.id,
        slot=slot,
        updated_at=slot.start,
    )
    appointment.check_in(at=slot.start)
    _authorize(doctor, patient, account, cashier_id)
    note = Consultation(
        id=next(ids),
        clinic_id=clinic.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_id=appointment.id,
        note="Synthetic visit",
        created_at=slot.start,
        updated_at=slot.start,
    )
    note.finalize(at=slot.end)
    rx = Prescription(
        id=next(ids),
        clinic_id=clinic.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        consultation_id=note.id,
    )
    rx.add_item(
        PrescriptionItem(
            medication=Medication(name="Demo item"),
            dose="Demo",
            route="Demo",
            frequency="Demo",
            duration="Demo",
        )
    )
    rx.issue(at=slot.end)
    _amend(note, ids)
    appointment.complete(at=slot.end)
    records: tuple[Entity, ...] = (appointment, note, rx)
    for entity in records:
        store.replace_collection(type(entity).__name__, {entity.id: entity})
    return note


def _amend(note: Consultation, ids: Iterator[UUID]) -> None:
    """Check that a correction references the original entry and preserves its text.

    Args:
        note: Final consultation from the visit.
        ids: Source of synthetic identifiers.
    """
    entry = ClinicalEntry(
        id=next(ids),
        clinic_id=note.clinic_id,
        patient_id=note.patient_id,
        consultation_id=note.id,
        author_id=note.doctor_id,
        kind="NOTE",
        content=note.note,
        recorded_at=note.updated_at,
    )
    correction = ClinicalAmendment(
        id=next(ids),
        clinic_id=entry.clinic_id,
        patient_id=entry.patient_id,
        entry_id=entry.id,
        author_id=entry.author_id,
        reason="Synthetic correction",
        replacement_content="Corrected synthetic visit",
        recorded_at=entry.recorded_at,
    )
    if (
        not correction.applies_to(entry)
        or entry.content != note.note
        or correction.replacement_content == entry.content
    ):
        raise RuntimeError("Correction did not preserve the original entry")


@contextmanager
def _expect_rejection(key: str) -> Iterator[None]:
    """Require a specific domain validation failure.

    Args:
        key: Expected domain message key.

    Yields:
        Control to the proposed invalid transaction.
    """
    try:
        yield
    except ValidationError as exc:
        if exc.message_key != key:
            raise
    else:
        raise RuntimeError(f"Expected rejection {key}")


def clinic_demo() -> None:
    """Commit a linked visit, verify its partial balance and roll back a rejected edit."""
    ids = (UUID(int=index) for index in range(1, 80))
    store = MemoryStore()
    with MemoryUnitOfWork(store) as transaction:
        cashier_id = next(ids)
        note = _visit(ids, store, next(ids), cashier_id)
        invoice = Invoice(
            id=next(ids), clinic_id=note.clinic_id, patient_id=note.patient_id, currency="DZD"
        )
        fee = Money(amount=Decimal("1000"), currency=invoice.currency)
        invoice.add_line(
            InvoiceLine(
                line_id=next(ids),
                description="Consultation",
                quantity=Decimal(1),
                unit_price=fee,
                discount_amount=Money(amount=Decimal(0), currency=invoice.currency),
                tax_rate=Decimal(0),
                source_service_id=None,
                source_consultation_id=note.id,
            )
        )
        at = FIXED_TIME + timedelta(minutes=30)
        invoice.issue("DEMO-001", at=at, due_on=at.date())
        paid = Money(amount=Decimal("400"), currency=invoice.currency)
        validate_payment(invoice, paid, (), ())
        payment = Payment(
            id=next(ids),
            clinic_id=invoice.clinic_id,
            invoice_id=invoice.id,
            amount=paid,
            method=PaymentMethod.CASH,
            received_at=at,
            received_by=cashier_id,
            idempotency_key=next(ids),
        )
        store.replace_collection("Invoice", {invoice.id: invoice})
        store.replace_collection("Payment", {payment.id: payment})
        audit = AuditEntry(
            id=next(ids),
            clinic_id=invoice.clinic_id,
            actor_id=cashier_id,
            action="PAYMENT_RECORD",
            resource_type="Payment",
            resource_id=payment.id,
            outcome="SUCCESS",
            occurred_at=at,
            correlation_id=payment.idempotency_key,
        )
        event = DomainEvent(
            event_id=next(ids),
            event_type="PAYMENT_RECORDED",
            clinic_id=invoice.clinic_id,
            entity_id=payment.id,
            entity_version=0,
            actor_id=cashier_id,
            occurred_at=at,
            correlation_id=payment.idempotency_key,
        )
        transaction.stage_audit(audit)
        transaction.stage_event(event)
        transaction.commit()

    try:
        with MemoryUnitOfWork(store) as rejected:
            rejected.stage_audit(replace(audit, id=next(ids)))
            rejected.stage_event(replace(event, event_id=next(ids)))
            store.replace_collection("Payment", {})
            note.update_note("Rejected amendment", at=at)
    except InvalidTransitionError:
        pass
    else:
        raise RuntimeError("Finalized note accepted an edit")
    saved = store.read_collection("Payment").get(payment.id)
    if not isinstance(saved, Payment):
        raise RuntimeError("Rollback lost the committed payment")
    snapshot = store.snapshot()
    if snapshot.audit_entries != (audit,) or snapshot.outbox_events != (event,):
        raise RuntimeError("Rollback changed the committed payment audit or outbox")
    with _expect_rejection("payment.amount.exceeds_outstanding"):
        validate_payment(invoice, fee, (saved,), ())
    with _expect_rejection("reversal.exceeds_payment"):
        validate_reversal(saved, fee, ())
    balance = calculate_balance(invoice, (saved,), ())
    if (
        balance.outstanding.amount != Decimal("600")
        or balance.settlement != SettlementStatus.PARTIAL
    ):
        raise RuntimeError("The committed invoice has an incorrect partial balance")
    print("Visit passed: authorized doctor, completed appointment, final note and prescription.")
    print("Invoice 1000 DZD, paid 400 DZD, outstanding 600 DZD. Denial and rollback verified.")
