"""Access-control enumeration types for roles, permissions, and scopes."""

from __future__ import annotations

from enum import Enum


class Role(Enum):
    """Clinic membership roles that determine which grants apply to a user.

    Roles belong to a ClinicMembership, not to a Person or StaffProfile.
    A user may hold multiple roles within the same clinic.
    """

    OWNER = "OWNER"
    MANAGER = "MANAGER"
    DOCTOR = "DOCTOR"
    NURSE = "NURSE"
    SECRETARY = "SECRETARY"


class Permission(Enum):
    """System permissions that guard individual actions on clinic resources.

    Unknown or unrecognised permissions must always be denied.
    """

    PATIENT_READ = "PATIENT_READ"
    PATIENT_WRITE = "PATIENT_WRITE"
    APPOINTMENT_READ = "APPOINTMENT_READ"
    APPOINTMENT_WRITE = "APPOINTMENT_WRITE"
    CLINICAL_READ = "CLINICAL_READ"
    CLINICAL_WRITE = "CLINICAL_WRITE"
    PRESCRIBE = "PRESCRIBE"
    BILLING_READ = "BILLING_READ"
    BILLING_WRITE = "BILLING_WRITE"
    PAYMENT_RECORD = "PAYMENT_RECORD"
    PAYMENT_REVERSE = "PAYMENT_REVERSE"
    FINANCE_REPORT = "FINANCE_REPORT"
    STAFF_MANAGE = "STAFF_MANAGE"
    ROLE_MANAGE = "ROLE_MANAGE"


class AccessScope(Enum):
    """Access scope that further restricts which resources a grant covers.

    CLINIC:   The grant applies to all resources within the authorized clinic.
    ASSIGNED: The grant applies only to resources assigned to the authenticated
              staff member (e.g. a doctor's assigned patients).
    OWN:      The grant applies only to resources belonging to the authenticated
              user themselves.

    Scope enforcement relies on trusted server-side resource information; the
    client must never be allowed to assert its own scope.
    """

    CLINIC = "CLINIC"
    ASSIGNED = "ASSIGNED"
    OWN = "OWN"

