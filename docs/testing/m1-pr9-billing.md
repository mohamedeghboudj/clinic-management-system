# Independent M1 test evidence — PR #9

**Date:** 1 November 2026. **Tester:** @mohamedeghboudj.
**Author:** @ayyoubbouchama. **Assigned reviewers:** @ahmed-ammiche, @SamirKor.
**Submitted implementation tested:** `9929c145be370240099d0d8cb2824dce58cd0923`.
This contribution adds tests/evidence; it does not modify M5 production code.

## Result: independent acceptance blocked

| Evidence | Result |
| --- | --- |
| Submitted branch before M1 tests | 84 passed |
| Original nine M1 billing contract cases | All nine execute and pass; no missing-module skips |
| All M1 independent/contract cases, including inherited Money cases | 89 passed, 7 failed |
| Complete branch including submitted tests | 173 passed, 7 failed; no skips/xfails |
| Combined configured coverage | 98.53%; per-module coverage gate passes |
| Ruff, strict mypy, source contracts, duplication | Pass |

## What was independently tested

| Area | Scenarios |
| --- | --- |
| Money | The 39 boundary cases supplied with PR #8; exactness and error defects propagate here. |
| Invoice lines | Independently calculated fractional quantity/discount/tax examples; sum rounded lines; reject invalid quantity, discount and tax. |
| Snapshot ownership | Clearing the caller's list does not erase invoice lines; lines are frozen and returned as a tuple; issued lines cannot be removed. |
| Invoice transitions | Duplicate IDs/source pairs and invalid issuance do not partially mutate a draft; paid amounts block void; valid void preserves issue/line history and prevents reopening/editing. |
| Rehydrated state | Both ISSUED and VOID constructors must reject due dates before issuance and datetime values passed as calendar dates. Four regressions currently fail. |
| Payments and debt | Unpaid/partial/paid examples, exact remaining payment, nonpositive/excess rejection, repeated validation does not post/mutate money. |
| Reversals | Partial/full corrections, remaining bounds, invalid cumulative reversals, immutable original payments/corrections, replacement of previously reversed funds. |
| Scope and history | Wrong clinic/invoice/parent links, orphan corrections, duplicate payment/reversal IDs and order-independent totals. |
| Overdue/void balance | Explicit due-day boundaries, paid/unissued exceptions, zero-net void debt, rejection of unreconciled void history. |
| Posted records and query DTO | Positive amounts and aware timestamps at construction; frozen records; InvoiceSummary's published field allowlist, calendar dates and valid versions. |

Test code is under `tests/independent/m1/`; the original published acceptance
examples are in `tests/contract/test_billing_contract.py`. Fixtures construct real
M5 classes through public APIs and do not import M5's author-test helpers.

## Outstanding defects and design/port limits

- [#11](https://github.com/mohamedeghboudj/clinic-management-system/issues/11)
  contributes two failing Money precision cases; fix upstream in PR #8.
- [#12](https://github.com/mohamedeghboudj/clinic-management-system/issues/12)
  contributes one raw-overflow failure; fix upstream in PR #8.
- [#13](https://github.com/mohamedeghboudj/clinic-management-system/issues/13)
  contributes four constructor-date regressions. The constructor accepts states
  rejected by `issue()`, including `datetime` values as `due_on`.

The ports expose clinic-scoped IDs, paging, expected versions, transaction-lock
intent and safe DTO types. They are interfaces, not implemented SQL behavior:
unit tests cannot establish real row locking, remote races, number allocation,
authorization or durable idempotency. Before adapters ship, document stable page
ordering/tie-breaker, operational history limits, transaction usage and error
outcomes, then verify them against an isolated remote PostgreSQL test target.
No port-existence assertion is counted as evidence of those guarantees.

## Reproduce and acceptance

```powershell
python -m pytest tests/contract/test_billing_contract.py -q
python -m pytest tests/independent/m1 -q
python -m pytest --cov --cov-report=term-missing --cov-report=json
python -m scripts.check_coverage
python -m ruff check src tests scripts
python -m mypy
```

Recorded execution: Windows/Python 3.14.10, pytest 9.2.0; no database or real data.
Required Linux/Windows CI will remain red while these regressions are present.
High coverage is not independent acceptance when seven assertions still fail.

M5 fixes the Money parent first, merges it into this branch, then fixes invoice
construction. M1 reruns the complete suite on the fixed head. M2/M3 review and
approve final changes; M1 supplies test evidence, not a substitute approval.
After its parent is accepted, retarget this PR appropriately before a main merge.
