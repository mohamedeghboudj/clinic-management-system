# Independent M4 test evidence — PR #22

**Date:** 24 November 2026. **Tester:** @MohamedAmine-dash (M4).
**Author:** @SamirKor (M3). **Assigned reviewers:** @ayyoubbouchama (M5), @mohamedeghboudj (M1).
**Submitted implementation tested:** `85f6179`.
Production code is unchanged by this independent test contribution.

## Result: independent contract verification (10 passed, 1 defect identified)

| Evidence | Result |
| --- | --- |
| Author branch unit tests | 139 passed |
| M4 independent contract test cases (`test_m4_scheduling_contract.py`) | 10 passed, 1 failed |
| Code quality on independent test suite | Ruff clean, mypy strict clean (0 errors), formatting compliant |
| Production code impact | Unmodified (0 production changes by independent tester) |

### Defect Identified: Early No-Show Allowed (`test_appointment_early_no_show_is_rejected`)

- **Location:** `src/clinic_management/domain/scheduling/appointment.py:Appointment.mark_no_show`
- **Issue:** `Appointment.mark_no_show(at=...)` allows marking an appointment as `NO_SHOW` before the allocated `TimeSlot` has ended.
- **Scenario:** For an appointment scheduled from `09:00:00 UTC` to `10:00:00 UTC`, calling `appt.mark_no_show(at=2026-11-02 09:30:00 UTC)` succeeds without error, transitioning the appointment status to `NO_SHOW` and incrementing the version.
- **Expected Behavior:** Per the scheduling domain contract, an appointment cannot be declared a no-show while the appointment window is still ongoing (`at < self.slot.end`). The method must reject early no-show attempts with a `ValidationError` or `InvalidTransitionError` without modifying status or version.
- **Action Required:** Awaiting M3 fix in `Appointment.mark_no_show` to validate `at >= self.slot.end`.

## What was independently tested

| Area | Invariants & Scenarios Tested | Status |
| --- | --- | --- |
| `TimeSlot` aware instant validation | Rejection of naive datetimes lacking UTC timezone info (`ValidationError`). | Passed |
| `TimeSlot` interval ordering | Rejection of inverted intervals (`start > end`) and zero-duration intervals (`start == end`). | Passed |
| `TimeSlot` duration | Exact positive duration computation (`timedelta(hours=1)`). | Passed |
| `TimeSlot` adjacent non-overlap | Half-open `[start, end)` semantics allowing adjacent contiguous bookings without overlap. | Passed |
| `TimeSlot` intersection overlap | Detection of overlapping intervals across start/midpoint boundaries. | Passed |
| `TimeSlot` contains semantics | `contains(start)` is `True`, `contains(start + 30m)` is `True`, `contains(end)` is `False`. | Passed |
| `Appointment` lifecycle | Happy path: `SCHEDULED -> CHECKED_IN -> COMPLETED`. | Passed |
| `Appointment` invalid transitions | Direct transition `SCHEDULED -> COMPLETED` without prior check-in rejected (`InvalidTransitionError`). | Passed |
| `Appointment` early no-show rejection | Calling `mark_no_show(at=...)` before slot ends (`at < slot.end`) must be rejected. | **Failed (Awaiting M3 Fix)** |
| `Appointment` cancellation reason | Cancellation with empty or whitespace-only reason rejected (`ValidationError`). | Passed |
| `Room` service lifecycle | Active room is bookable; taking room out of service sets `is_bookable() == False`; restoring service re-enables `is_bookable() == True`. | Passed |
