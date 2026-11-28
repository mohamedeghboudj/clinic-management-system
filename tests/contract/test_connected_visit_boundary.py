"""Check that the common API messages can cross feature boundaries safely."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import get_type_hints
from uuid import UUID

import pytest

from clinic_management.application.contracts.visit import ChangeHint, CommandReceipt
from clinic_management.application.ports.visit import BillingWorkflow, VisitGateway
from clinic_management.application.ports.visit_transaction import ReceiptRepository


def test_replay_receipt_is_shared_by_command_and_lookup() -> None:
    """Keep the result type identical across original payment, replay and lookup."""
    assert get_type_hints(BillingWorkflow.pay)["return"] is CommandReceipt
    assert get_type_hints(VisitGateway.command_status)["return"] == CommandReceipt | None
    assert get_type_hints(ReceiptRepository.lock_and_find)["return"] == CommandReceipt | None
    receipt = CommandReceipt(
        key=UUID(int=1),
        operation="BillingWorkflow.pay",
        resource_id=UUID(int=2),
        resource_version=3,
        committed_at=datetime(2026, 11, 27, tzinfo=UTC),
    )
    with pytest.raises(FrozenInstanceError):
        setattr(receipt, "resource_version", 4)  # noqa: B010 -- verify frozen runtime behavior


def test_notification_has_only_the_public_invalidation_fields() -> None:
    """Prevent a new domain payload from being exposed by the socket projection."""
    assert get_type_hints(ChangeHint) == {
        "event_id": UUID,
        "event_type": str,
        "entity_id": UUID,
        "entity_version": int,
    }
