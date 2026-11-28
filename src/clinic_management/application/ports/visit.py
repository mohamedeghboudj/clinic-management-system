"""Provider-neutral application boundaries for the connected desktop workflow."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from typing import Literal, Protocol
from uuid import UUID

from clinic_management.application.contracts.billing import InvoiceSummary
from clinic_management.application.contracts.clinical import ClinicalEntrySummary
from clinic_management.application.contracts.health import ComponentHealth
from clinic_management.application.contracts.paging import Page, PageRequest
from clinic_management.application.contracts.people import PatientSummary
from clinic_management.application.contracts.scheduling import AppointmentSummary
from clinic_management.application.contracts.visit import (
    BookingResource,
    ChangeHint,
    CommandContext,
    CommandReceipt,
    ConsultationView,
    EntryHistory,
    ServiceSnapshot,
)
from clinic_management.domain.access.principal import Principal
from clinic_management.domain.billing.balance import BalanceSummary
from clinic_management.domain.billing.enums import PaymentMethod
from clinic_management.domain.clinical.prescription import PrescriptionItem
from clinic_management.domain.shared.contact import ContactInfo
from clinic_management.domain.shared.money import Money
from clinic_management.domain.shared.time_slot import TimeSlot


class VisitGateway(Protocol):
    """Platform interface shared by API handlers, adapters and contract tests."""

    def ready(self) -> ComponentHealth:
        """Report service readiness against configured remote dependencies.

        Returns:
            Service readiness against configured remote dependencies.
        """
        ...

    def command_status(self, principal: Principal, key: UUID) -> CommandReceipt | None:
        """Look up this actorâ€™s committed command in the selected clinic.

        Args:
            principal: Server-resolved, current clinic identity.
            key: Original client command identifier.

        Returns:
            This actorâ€™s committed command in the selected clinic.
        """
        ...

    def changes(self, principal: Principal) -> Iterator[ChangeHint]:
        """Yield authorized committed invalidations until disconnect or revocation.

        Args:
            principal: Server-resolved, current clinic identity.

        Returns:
            Authorized committed invalidations until disconnect or revocation.
        """
        ...


class PatientWorkflow(Protocol):
    """Access and patients interface shared by API handlers, adapters and contract tests."""

    def me(self, principal: Principal) -> Principal:
        """Return the current validated clinic identity.

        Args:
            principal: Server-resolved, current clinic identity.

        Returns:
            The current validated clinic identity.
        """
        ...

    def register(
        self,
        ctx: CommandContext,
        *,
        given_name: str,
        family_name: str,
        contact: ContactInfo,
        birth_date: date | None,
    ) -> CommandReceipt:
        """Register a person and clinic patient and allocate a unique number.

        Args:
            ctx: Verified identity, replay key and correlation metadata.
            given_name: Patientâ€™s given name.
            family_name: Patientâ€™s family name.
            contact: Validated contact value.
            birth_date: Optional date of birth.

        Returns:
            The persisted acknowledgment of this command.
        """
        ...

    def search(
        self, principal: Principal, *, query: str, page: PageRequest
    ) -> Page[PatientSummary]:
        """Search permitted patients using a stable, bounded cursor.

        Args:
            principal: Server-resolved, current clinic identity.
            query: Clinic-scoped search text.
            page: Bounded page size and continuation cursor.

        Returns:
            Permitted patients using a stable, bounded cursor.
        """
        ...


class BookingWorkflow(Protocol):
    """Scheduling interface shared by API handlers, adapters and contract tests."""

    def book(
        self,
        ctx: CommandContext,
        *,
        patient_id: UUID,
        doctor_id: UUID,
        room_id: UUID,
        slot: TimeSlot,
    ) -> CommandReceipt:
        """Book an available clinic doctor and room in one transaction.

        Args:
            ctx: Verified identity, replay key and correlation metadata.
            patient_id: Clinic patient identifier.
            doctor_id: Clinic doctor profile identifier.
            room_id: Clinic room identifier.
            slot: Half-open appointment interval.

        Returns:
            The persisted acknowledgment of this command.
        """
        ...

    def check_in(
        self, ctx: CommandContext, *, appointment_id: UUID, expected_version: int
    ) -> CommandReceipt:
        """Check in a scheduled patient using the observed version.

        Args:
            ctx: Verified identity, replay key and correlation metadata.
            appointment_id: Clinic appointment identifier.
            expected_version: Last observed aggregate version (invoice version for payments).

        Returns:
            The persisted acknowledgment of this command.
        """
        ...

    def schedule(
        self, principal: Principal, *, doctor_id: UUID, day: date, page: PageRequest
    ) -> Page[AppointmentSummary]:
        """Read the permitted schedule for a clinic-local date.

        Args:
            principal: Server-resolved, current clinic identity.
            doctor_id: Clinic doctor profile identifier.
            day: Clinic-local calendar date.
            page: Bounded page size and continuation cursor.

        Returns:
            The permitted schedule for a clinic-local date.
        """
        ...

    def cancel(
        self, ctx: CommandContext, *, appointment_id: UUID, reason: str, expected_version: int
    ) -> CommandReceipt:
        """Cancel a booking and release the reserved interval.

        Args:
            ctx: Verified command metadata.
            appointment_id: Target appointment.
            reason: Cancellation reason.
            expected_version: Observed appointment version.

        Returns:
            Committed command acknowledgment.
        """
        ...

    def reschedule(
        self, ctx: CommandContext, *, appointment_id: UUID, slot: TimeSlot, expected_version: int
    ) -> CommandReceipt:
        """Reserve the replacement interval and release the old interval atomically.

        Args:
            ctx: Verified command metadata.
            appointment_id: Target appointment.
            slot: Requested half-open interval.
            expected_version: Observed appointment version.

        Returns:
            Committed command acknowledgment.
        """
        ...

    def complete(
        self, ctx: CommandContext, *, appointment_id: UUID, expected_version: int
    ) -> CommandReceipt:
        """Complete a checked-in visit under the authorized transition.

        Args:
            ctx: Verified command metadata.
            appointment_id: Target appointment.
            expected_version: Observed appointment version.

        Returns:
            Committed command acknowledgment.
        """
        ...

    def resources(
        self, principal: Principal, *, kind: Literal["doctor", "room"], page: PageRequest
    ) -> Page[BookingResource]:
        """List permitted scheduling choices with stable identifiers.

        Args:
            principal: Verified clinic identity.
            kind: Scheduling resource category.
            page: Bounded continuation request.

        Returns:
            Authorized resource projection.
        """
        ...


class ClinicalWorkflow(Protocol):
    """Clinical interface shared by API handlers, adapters and contract tests."""

    def start(self, ctx: CommandContext, *, appointment_id: UUID, note: str) -> CommandReceipt:
        """Create the consultation for an eligible checked-in appointment.

        Args:
            ctx: Verified identity, replay key and correlation metadata.
            appointment_id: Clinic appointment identifier.
            note: Consultation narrative.

        Returns:
            The persisted acknowledgment of this command.
        """
        ...

    def save_note(
        self, ctx: CommandContext, *, consultation_id: UUID, note: str, expected_version: int
    ) -> CommandReceipt:
        """Save a draft without overwriting a concurrent change.

        Args:
            ctx: Verified identity, replay key and correlation metadata.
            consultation_id: Clinic consultation identifier.
            note: Consultation narrative.
            expected_version: Last observed aggregate version (invoice version for payments).

        Returns:
            The persisted acknowledgment of this command.
        """
        ...

    def finalize(
        self, ctx: CommandContext, *, consultation_id: UUID, expected_version: int
    ) -> CommandReceipt:
        """Finalize the note and append immutable history atomically.

        Args:
            ctx: Verified identity, replay key and correlation metadata.
            consultation_id: Clinic consultation identifier.
            expected_version: Last observed aggregate version (invoice version for payments).

        Returns:
            The persisted acknowledgment of this command.
        """
        ...

    def amend(
        self, ctx: CommandContext, *, entry_id: UUID, reason: str, replacement_content: str
    ) -> CommandReceipt:
        """Append a correction while retaining the original entry.

        Args:
            ctx: Verified identity, replay key and correlation metadata.
            entry_id: Original immutable history entry identifier.
            reason: Reason for the action.
            replacement_content: Correction text retained alongside the original.

        Returns:
            The persisted acknowledgment of this command.
        """
        ...

    def prescribe(
        self, ctx: CommandContext, *, consultation_id: UUID, items: tuple[PrescriptionItem, ...]
    ) -> CommandReceipt:
        """Issue an ordered prescription for the authorized consultation.

        Args:
            ctx: Verified identity, replay key and correlation metadata.
            consultation_id: Clinic consultation identifier.
            items: Ordered prescribed items.

        Returns:
            The persisted acknowledgment of this command.
        """
        ...

    def history(
        self, principal: Principal, *, patient_id: UUID, page: PageRequest
    ) -> Page[ClinicalEntrySummary]:
        """Return the permitted clinical history summary.

        Args:
            principal: Server-resolved, current clinic identity.
            patient_id: Clinic patient identifier.
            page: Bounded page size and continuation cursor.

        Returns:
            The permitted clinical history summary.
        """
        ...

    def services(self, principal: Principal, *, page: PageRequest) -> Page[ServiceSnapshot]:
        """List active services using the billing-safe projection.

        Args:
            principal: Server-resolved, current clinic identity.
            page: Bounded page size and continuation cursor.

        Returns:
            Active services using the billing-safe projection.
        """
        ...

    def consultation(self, principal: Principal, *, consultation_id: UUID) -> ConsultationView:
        """Reload the authorized consultation and its current version.

        Args:
            principal: Verified clinic identity.
            consultation_id: Consultation to reload.

        Returns:
            Authorized resource projection.
        """
        ...

    def corrections(self, principal: Principal, *, entry_id: UUID) -> EntryHistory:
        """Read the original clinical entry and its ordered corrections.

        Args:
            principal: Verified clinic identity.
            entry_id: Original immutable entry.

        Returns:
            Authorized resource projection.
        """
        ...


class BillingWorkflow(Protocol):
    """Billing interface shared by API handlers, adapters and contract tests."""

    def draft(
        self,
        ctx: CommandContext,
        *,
        patient_id: UUID,
        consultation_id: UUID,
        service_ids: tuple[UUID, ...],
    ) -> CommandReceipt:
        """Create a draft with ordered immutable catalogue price snapshots.

        Args:
            ctx: Verified identity, replay key and correlation metadata.
            patient_id: Clinic patient identifier.
            consultation_id: Clinic consultation identifier.
            service_ids: Ordered billable catalogue identifiers.

        Returns:
            The persisted acknowledgment of this command.
        """
        ...

    def issue(
        self, ctx: CommandContext, *, invoice_id: UUID, expected_version: int, due_on: date
    ) -> CommandReceipt:
        """Allocate the invoice number and issue the versioned draft.

        Args:
            ctx: Verified identity, replay key and correlation metadata.
            invoice_id: Clinic invoice identifier.
            expected_version: Last observed aggregate version (invoice version for payments).
            due_on: Payment due date.

        Returns:
            The persisted acknowledgment of this command.
        """
        ...

    def pay(
        self,
        ctx: CommandContext,
        *,
        invoice_id: UUID,
        amount: Money,
        method: PaymentMethod,
        expected_version: int,
    ) -> CommandReceipt:
        """Lock the invoice, validate the balance and record one payment.

        Args:
            ctx: Verified identity, replay key and correlation metadata.
            invoice_id: Clinic invoice identifier.
            amount: Exact currency amount.
            method: Payment method.
            expected_version: Last observed aggregate version (invoice version for payments).

        Returns:
            The persisted acknowledgment of this command.
        """
        ...

    def reverse(
        self,
        ctx: CommandContext,
        *,
        payment_id: UUID,
        amount: Money,
        reason: str,
        expected_version: int,
    ) -> CommandReceipt:
        """Reverse an allowed amount under the parent invoice version.

        Args:
            ctx: Verified identity, replay key and correlation metadata.
            payment_id: Identifier of the original payment.
            amount: Exact currency amount.
            reason: Reason for the action.
            expected_version: Last observed aggregate version (invoice version for payments).

        Returns:
            The persisted acknowledgment of this command.
        """
        ...

    def balance(self, principal: Principal, *, invoice_id: UUID) -> BalanceSummary:
        """Read a permitted ledger balance using the current invoice state.

        Args:
            principal: Server-resolved, current clinic identity.
            invoice_id: Clinic invoice identifier.

        Returns:
            A permitted ledger balance using the current invoice state.
        """
        ...

    def summary(self, principal: Principal, *, invoice_id: UUID) -> InvoiceSummary:
        """Read a permitted invoice including its current version.

        Args:
            principal: Server-resolved, current clinic identity.
            invoice_id: Clinic invoice identifier.

        Returns:
            A permitted invoice including its current version.
        """
        ...
