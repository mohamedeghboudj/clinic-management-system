"""Room and appointment status enumerations for facilities and scheduling."""

from __future__ import annotations

from enum import Enum


class RoomType(Enum):
    """Category of a room within a clinic facility.

    Members:
        CONSULTATION: Standard consultation / examination room.
        OPERATING: Surgical or procedure room (future implementation).
        WARD: Inpatient ward room (future implementation).
    """

    CONSULTATION = "CONSULTATION"
    OPERATING = "OPERATING"
    WARD = "WARD"


class RoomStatus(Enum):
    """Operational status of a room.

    Members:
        ACTIVE: Room is in service and eligible to be booked.
        OUT_OF_SERVICE: Room is temporarily unavailable (maintenance etc.).

    Note:
        Occupancy is derived from active reservations, not represented as a
        permanent room status value.  Do not add an OCCUPIED variant here.
    """

    ACTIVE = "ACTIVE"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"
