"""Shared messages for the connected clinic visit."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from clinic_management.domain.access.principal import Principal
from clinic_management.domain.clinical.amendment import ClinicalAmendment
from clinic_management.domain.clinical.enums import ConsultationStatus
from clinic_management.domain.clinical.record_entry import ClinicalEntry
from clinic_management.domain.shared.money import Money


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandContext:
    """Verified actor, client command key and server request correlation ID."""

    principal: Principal
    key: UUID
    correlation_id: UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class CommandReceipt:
    """Immutable acknowledgment of one committed command, safe to replay."""

    key: UUID
    operation: str
    resource_id: UUID
    resource_version: int
    committed_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ServiceSnapshot:
    """Authorized billable projection with the catalogue price at selection."""

    service_id: UUID
    description: str
    unit_price: Money


@dataclass(frozen=True, slots=True, kw_only=True)
class ChangeHint:
    """Authorized invalidation for a view, without clinical or financial payload."""

    event_id: UUID
    event_type: str
    entity_id: UUID
    entity_version: int


@dataclass(frozen=True, slots=True, kw_only=True)
class BookingResource:
    """Minimal permitted option for the scheduling selector."""

    id: UUID
    label: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ConsultationView:
    """Assigned clinician’s read model of an editable or finalized note."""

    consultation_id: UUID
    appointment_id: UUID
    note: str
    status: ConsultationStatus
    version: int


@dataclass(frozen=True, slots=True, kw_only=True)
class EntryHistory:
    """Original immutable clinical entry and its append-only corrections."""

    original: ClinicalEntry
    amendments: tuple[ClinicalAmendment, ...]
