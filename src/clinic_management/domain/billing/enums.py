"""Enumerations for invoice lifecycle, settlement projection and payment methods."""

from __future__ import annotations

from enum import StrEnum


class InvoiceStatus(StrEnum):
    """Represent the document lifecycle state of a patient invoice."""

    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    VOID = "VOID"


class SettlementStatus(StrEnum):
    """Represent the derived payment settlement state of an invoice."""

    UNPAID = "UNPAID"
    PARTIAL = "PARTIAL"
    PAID = "PAID"


class PaymentMethod(StrEnum):
    """Represent the recorded method by which a payment was received."""

    CASH = "CASH"
    CARD = "CARD"
    CHEQUE = "CHEQUE"
    BANK_TRANSFER = "BANK_TRANSFER"
