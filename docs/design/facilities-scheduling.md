# Facilities and Scheduling — Design Document

**Module:** M3 — Facilities, Scheduling and Inventory Design  
**Sprint:** Week 1  
**Status:** Implemented (core models); future extensions noted below.

---

## 1. Purpose and Scope

This document describes the design of the **facilities** and **scheduling** subsystems within the Clinic Management System.

**Facilities** covers the physical infrastructure of a clinic: its identity, location, contact details, timezone, opening hours, and the rooms it contains.

**Scheduling** covers the lifecycle of appointments: booking, check-in, completion, cancellation, no-show, and rescheduling. It also covers the availability rules used to validate that a requested slot is within opening hours and free of exceptions.

---

## 2. Domain Models

### 2.1 TimeSlot

`domain/shared/time_slot.py`

A **value object** representing a half-open time interval `[start, end)`.

| Property | Type | Description |
|----------|------|-------------|
| `start` | `datetime` | Inclusive start (timezone-aware) |
| `end` | `datetime` | Exclusive end (timezone-aware) |

**Key semantics:**

- Both endpoints must be timezone-aware. Naive datetimes are always rejected.
- `start` must be strictly before `end`.
- **Half-open interval `[start, end)`**: `start` is contained; `end` is not.
- Two adjacent intervals (one ends where the other begins) do **not** overlap.
- `overlaps(other)`: returns `True` iff `self.start < other.end AND other.start < self.end`.
- `contains(instant)`: returns `True` iff `start <= instant < end`.
- `duration()`: always positive.

---

### 2.2 OpeningPeriod and OpeningHours

`domain/facilities/opening_hours.py`

**OpeningPeriod** is an immutable value object for a single same-day local-time window:

| Property | Type | Description |
|----------|------|-------------|
| `weekday` | `int` | ISO weekday: 0 = Monday, 6 = Sunday |
| `opens_at` | `time` | Local time the clinic opens (inclusive) |
| `closes_at` | `time` | Local time the clinic closes (exclusive) |

Overnight periods must be split into two `OpeningPeriod` instances (e.g. 22:00–00:00 and 00:00–02:00 on the next weekday).

**OpeningHours** is an immutable weekly configuration:

| Property | Type | Description |
|----------|------|-------------|
| `timezone` | `str` | IANA timezone identifier (e.g. `"Africa/Algiers"`) |
| `periods` | `tuple[OpeningPeriod, ...]` | Weekly opening windows |

**Coverage check — `covers(slot: TimeSlot) -> bool`:**

1. Convert both endpoints of the slot to the clinic's local timezone.
2. Walk every calendar date spanned by the slot.
3. For each date, find the matching weekday's periods.
4. Verify the portion of the slot falling on that date is fully covered by the union of those periods.
5. Return `True` only if **every** portion is covered.

> **Design decision — boundary at exactly closing time:**  
> A slot ending precisely at `closes_at` is considered fully covered because the period itself uses `[opens_at, closes_at)` semantics consistent with `TimeSlot`.

---

### 2.3 Clinic

`domain/facilities/clinic.py`

Aggregate root representing a healthcare facility.

| Property | Type | Description |
|----------|------|-------------|
| `id` | `UUID` | Unique identifier |
| `version` | `int` | Optimistic concurrency version |
| `name` | `str` | Display name |
| `contact` | `ContactInfo` | Phone / email |
| `address` | `Address \| None` | Optional physical address |
| `timezone` | `str` | IANA timezone |
| `currency` | `str` | ISO 4217 three-letter code |
| `opening_hours` | `OpeningHours` | Weekly schedule |
| `active` | `bool` | Whether the clinic accepts appointments |

**Invariant:** `opening_hours.timezone` must equal `clinic.timezone`.

**Methods:**
- `update_opening_hours(schedule)` — replaces the schedule; enforces timezone match.
- `deactivate()` — sets `active = False`. Does **not** cancel existing appointments; the calling use case handles downstream effects.

There is one active clinic in Sprint 1, but the model supports multiple clinics by design.

---

### 2.4 RoomType and RoomStatus

`domain/facilities/enums.py`

`RoomType`:
- `CONSULTATION` — standard examination room
- `OPERATING` — surgical/procedure room *(future)*
- `WARD` — inpatient ward *(future)*

`RoomStatus`:
- `ACTIVE` — in service, bookable
- `OUT_OF_SERVICE` — unavailable

> **Important:** Occupancy is derived from active reservations, not stored as a room status. Do not add an `OCCUPIED` status.

---

### 2.5 Room

`domain/facilities/room.py`

Entity representing a physical room within a clinic.

| Property | Type | Description |
|----------|------|-------------|
| `id` | `UUID` | Unique identifier |
| `version` | `int` | Optimistic concurrency version |
| `clinic_id` | `UUID` | Owning clinic |
| `number` | `str` | Short human-readable label (e.g. `"C-01"`) |
| `kind` | `RoomType` | Room category |
| `capacity` | `int` | Maximum patients (must be ≥ 1) |
| `status` | `RoomStatus` | Operational status |
| `status_reason` | `str \| None` | Explanation for out-of-service status |

**Methods:**
- `mark_out_of_service(reason)` — requires a non-empty reason. Does **not** cancel existing appointments.
- `restore_service()` — clears reason, sets `ACTIVE`.
- `is_bookable()` — returns `True` only when status is `ACTIVE`.

There is **no** `Room.book()` method. Appointment scheduling is the single source of reservation information.

---

### 2.6 AppointmentStatus

`domain/scheduling/enums.py`

| Status | Active reservation? |
|--------|-------------------|
| `SCHEDULED` | ✅ |
| `CHECKED_IN` | ✅ |
| `COMPLETED` | ❌ (history) |
| `CANCELLED` | ❌ (terminal) |
| `NO_SHOW` | ❌ (terminal) |

**Permitted transitions:**

```
SCHEDULED  → CHECKED_IN
SCHEDULED  → NO_SHOW
SCHEDULED  → CANCELLED
CHECKED_IN → COMPLETED
CHECKED_IN → CANCELLED
```

Completed, cancelled, and no-show appointments are terminal and cannot transition further.

---

### 2.7 Appointment

`domain/scheduling/appointment.py`

Aggregate root for a scheduled clinic appointment.

| Property | Type | Description |
|----------|------|-------------|
| `id` | `UUID` | Unique identifier |
| `version` | `int` | Optimistic concurrency version |
| `clinic_id` | `UUID` | Clinic scope |
| `patient_id` | `UUID` | Attending patient |
| `doctor_id` | `UUID` | Conducting doctor |
| `room_id` | `UUID` | Allocated room |
| `slot` | `TimeSlot` | Reserved time interval |
| `updated_at` | `datetime` | Timestamp of last status change |
| `status` | `AppointmentStatus` | Lifecycle status |
| `reason_summary` | `str \| None` | Optional visit reason |
| `cancellation_reason` | `str \| None` | Populated on cancellation |

**Availability checks are NOT performed inside `Appointment`.**  
Cross-record conflict detection is the responsibility of the application use case, using `AppointmentRepository.find_overlaps()`.

---

## 3. Relationships

```
Clinic ──< Room
Clinic ──< Appointment
Appointment >── Patient   (by patient_id)
Appointment >── Doctor    (by doctor_id — DoctorProfile from M2)
Appointment >── Room      (by room_id)
Clinic       ── OpeningHours ──< OpeningPeriod
```

---

## 4. Appointment Lifecycle and Transition Table

```
Created
   │
   ▼
SCHEDULED ──────────────────────────────► NO_SHOW
   │                                         (terminal)
   │
   ├──────────────────────────────────────► CANCELLED
   │                                         (terminal)
   ▼
CHECKED_IN ───────────────────────────────► CANCELLED
   │                                         (terminal)
   ▼
COMPLETED
(terminal, immutable history)
```

**Rules enforced at the entity level:**
- `check_in()` requires status `SCHEDULED`.
- `complete()` requires status `CHECKED_IN`.
- `cancel(reason)` requires a non-empty cancellation reason; permitted from `SCHEDULED` or `CHECKED_IN`.
- `mark_no_show()` requires status `SCHEDULED`. Timing enforcement (at ≥ slot.end) is the use case's responsibility.
- `reschedule(slot)` requires status `SCHEDULED`; does not check for conflicts.
- All timestamp arguments must be timezone-aware.

---

## 5. Opening Hours — Timezone Handling

- `OpeningHours.timezone` must be a valid IANA identifier (validated via `zoneinfo`).
- `Clinic.timezone` and `Clinic.opening_hours.timezone` must always agree.
- `covers(slot)` converts the slot's aware UTC (or any-tz) instants to the clinic's local timezone before comparing against opening periods.
- This correctly handles clinics in non-UTC zones and slots expressed in different timezones.

**Example:**  
Clinic in `Africa/Algiers` (UTC+1). Period: Monday 08:00–17:00.  
A slot `[07:00 UTC, 08:00 UTC)` = `[08:00 local, 09:00 local)` → **covered**.  
A slot `[06:30 UTC, 07:30 UTC)` = `[07:30 local, 08:30 local)` → **not covered** (starts before opening).

---

## 6. Doctor and Room Availability Rules

`domain/scheduling/availability.py`

`AvailabilityRule.allows(slot, opening_hours, exceptions)` is a **stateless pure policy** that:

1. Calls `within_opening_hours(slot, schedule)` → delegates to `OpeningHours.covers()`.
2. For each `ScheduleException` in `exceptions`, checks `slot.overlaps(exc.slot)`.
3. Returns `True` only if the slot is within opening hours **and** overlaps no exception.

**No database calls are made.** The caller (application use case) must pre-fetch relevant exceptions for the queried resource before calling `allows()`.

---

## 7. Schedule Exceptions, Closures, Leave and Maintenance

`ScheduleException`:

| Property | Type | Description |
|----------|------|-------------|
| `resource_id` | `UUID` | Affected resource (doctor, room, or clinic) |
| `slot` | `TimeSlot` | Unavailable interval |
| `reason_code` | `str` | Machine-readable code (e.g. `"ANNUAL_LEAVE"`, `"MAINTENANCE"`) |

Immutable. Used for one-off exceptions. For recurring unavailability (e.g. weekly closure), exceptions must be expanded at query time into individual `ScheduleException` instances. Recurrence is a **future design concern** (see §13).

---

## 8. Repository Ports and Responsibilities

### AppointmentRepository (`application/ports/scheduling.py`)

| Method | Description |
|--------|-------------|
| `get(clinic_id, appointment_id)` | Fetch single appointment |
| `add(appointment)` | Persist new appointment |
| `save(appointment, expected_version)` | Optimistic-lock update |
| `find_overlaps(clinic_id, slot, *, doctor_id, room_id, exclude_id)` | Advisory conflict check |
| `list_for_doctor(clinic_id, doctor_id, day, page)` | Paginated daily schedule |

**`find_overlaps` semantics:**
- At least one of `doctor_id` or `room_id` must be supplied.
- When both are given, results are the **union** of doctor conflicts and room conflicts.
- Only `SCHEDULED` and `CHECKED_IN` appointments count as conflicts.
- Results are bounded to the requested `TimeSlot`.
- `exclude_id` excludes one appointment (used during rescheduling).

### ClinicRepository (`application/ports/facilities.py`)

| Method | Description |
|--------|-------------|
| `get(clinic_id)` | Fetch clinic |
| `add(clinic)` | Persist new clinic |
| `save(clinic, expected_version)` | Optimistic-lock update |

### RoomRepository (`application/ports/facilities.py`)

| Method | Description |
|--------|-------------|
| `get(clinic_id, room_id)` | Fetch room |
| `add(room)` | Persist new room |
| `list_active(clinic_id, page)` | Paginated active rooms |
| `save(room, expected_version)` | Optimistic-lock update |

---

## 9. Appointment Booking Workflow

```
1. Use case receives: clinic_id, patient_id, doctor_id, room_id, slot
2. Load Clinic → verify active, slot within opening_hours
3. Load Room → verify is_bookable()
4. Load relevant ScheduleExceptions for doctor and room
5. AvailabilityRule.allows(slot, opening_hours, exceptions)
6. AppointmentRepository.find_overlaps(clinic_id, slot, doctor_id=…, room_id=…)
   → If overlaps found → raise ConflictError
7. Construct Appointment(id=new_uuid(), ..., updated_at=now)
8. AppointmentRepository.add(appointment)
9. Publish DomainEvent("APPOINTMENT_BOOKED")
```

> **Concurrency note:** Step 6 is advisory. A concurrent insert between step 6 and step 8 can still create a double-booking. Database-level uniqueness constraints or pessimistic locking must be used in infrastructure to prevent this.

---

## 10. Appointment Rescheduling Workflow

```
1. Use case receives: clinic_id, appointment_id, new_slot
2. AppointmentRepository.get(clinic_id, appointment_id)
   → If not found → raise NotFoundError
3. Verify appointment.status == SCHEDULED
4. Load opening_hours, exceptions, check availability for new_slot
5. AppointmentRepository.find_overlaps(…, exclude_id=appointment_id)
   → If overlaps → raise ConflictError
6. appointment.reschedule(new_slot, at=now)
7. AppointmentRepository.save(appointment, expected_version=appointment.version)
8. Publish DomainEvent("APPOINTMENT_RESCHEDULED")
```

---

## 11. Conflict Detection and Concurrency Considerations

Python-level prechecks (`find_overlaps`) do **not** guarantee concurrency safety:

- Two concurrent booking requests can both pass the overlap check and both succeed.
- Database-level enforcement (e.g. a partial unique index on `(clinic_id, doctor_id, slot_overlap)` using exclusion constraints in PostgreSQL, or application-level row locking) is required for strong guarantees.
- `save()` uses optimistic concurrency (`expected_version`) to prevent lost updates on a single aggregate but does **not** prevent two new inserts from conflicting.

**Doctor overlap constraint:** A doctor may not have two active appointments with overlapping slots within the same clinic.

**Room overlap constraint:** A room may not have two active appointments with overlapping slots.

**Adjacent intervals:** Two appointments where one ends exactly when another begins do **not** conflict (half-open semantics).

**Out-of-service room behavior:** Marking a room out of service does not cancel existing appointments. The use case must decide whether to notify affected patients.

---

## 12. Clinic-Local Day Queries

`AppointmentRepository.list_for_doctor(clinic_id, doctor_id, day, page)` accepts a `date` representing a **clinic-local calendar day**. Infrastructure adapters must convert this to a UTC range using the clinic's IANA timezone before querying the database, to correctly handle appointments at day boundaries.

---

## 13. Future Extensions (Not Implemented in Week 1)

### ResourceReservation
A unified reservation model for doctors, rooms, and equipment that prevents cross-feature double-bookings by maintaining a single reservation table. Each reservation references a resource type, resource ID, and time slot. Conflict queries need only scan this table regardless of which feature created the reservation.

### Bed
A model with `clinic_id`, `room_id`, `number`, and `active` state. Occupancy is derived from admissions (patient admitted to a bed), not from a room-level status field. Individual bed identity matters for billing, recalls, and infection tracking. `Room.capacity` is a planning aid, not a substitute for individual beds.

### Admission
A model linking a patient to a bed with `admitted_at`, `discharged_at`, and `daily_rate`. Billing rules for partial days (e.g. checking in at 23:50) and midnight boundary handling must be agreed upon before implementation.

### StaffShift
A model for staff schedules and shift assignments, linking a staff member to a date/time range. Needed for shift-based availability rules and overtime tracking.

### Equipment
A durable asset model with `asset_code`, `name`, `status` (`ACTIVE`, `IN_MAINTENANCE`, `RETIRED`), and `next_maintenance_date`. Equipment availability overlaps with room availability during procedures.

### RecurringAvailability
A model for recurring schedule patterns (e.g. "Doctor available every Monday 09:00–12:00"). Must include `effective_from`, `effective_until`, timezone, and a recurrence rule (e.g. iCal RRULE). At query time, recurring rules are expanded into concrete `ScheduleException` or availability window instances. This avoids storing infinite future records. Exception overrides (e.g. "skip this Monday's slot") must be supported.
