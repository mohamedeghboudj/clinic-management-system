# Independent M1 test evidence — PR #8

**Date:** 1 November 2026. **Tester:** @mohamedeghboudj.
**Author:** @ayyoubbouchama. **Assigned reviewers:** @ahmed-ammiche, @SamirKor.
**Submitted implementation tested:** `9910f3f24d866f4f18cc6d2b1c9f45f0656ab397`.
Production code is unchanged by this test contribution.

## Result: independent acceptance blocked

| Evidence | Result |
| --- | --- |
| Submitted branch before independent tests | 72 passed |
| New independent Money cases | 36 passed, 3 failed; no skips/xfails |
| Complete branch with independent tests | 108 passed, 3 failed |
| Money statements and branches exercised | 100% each; this does not make failing behavior acceptable |
| Combined configured coverage | 99.38%; per-module coverage gate passes |
| Ruff, strict mypy, source contracts, duplication | Pass |

New cases are in `tests/independent/m1/test_m1_money_contract.py`. They cover
positive/negative half-cent rounding, signed zero, quiet/signalling NaN,
infinities, wrong input types, unsupported currencies, immutable operands,
exact addition/subtraction/comparison, fractional quantities, one-pass generator
sums, empty-sum currency and percentage boundaries. Expected examples come from
the member guide's exact-decimal/ROUND_HALF_UP contract, not M5's test helpers.

## Reproduced defects

1. [#11 — double rounding](https://github.com/mohamedeghboudj/clinic-management-system/issues/11):
   `1.01 * 1.0049504950495049504950495049` returns `1.02` at the normal precision
   of 28. The exact product is `1.014999999999999999999999999949`, so the stated
   one-round cent policy requires `1.01`. A second case reproduces the same
   problem with precision 4 and quantity `1.00494`.
2. [#12 — unsafe arithmetic failure](https://github.com/mohamedeghboudj/clinic-management-system/issues/12):
   a finite `1E+1000000` factor leaks `decimal.Overflow` before quantization.
   Unsupported arithmetic magnitudes must fail through an explicit domain error.

The three regression cases remain ordinary failing tests. No production fix,
skip, xfail, warning suppression or reduced assertion is included.

## Reproduce and hand back

Use this branch's Python 3.14 environment from its repository root:

```powershell
python -m pytest tests/independent/m1/test_m1_money_contract.py -q
python -m pytest --cov --cov-report=term-missing --cov-report=json
python -m scripts.check_coverage
python -m ruff check src tests scripts
python -m mypy
```

Recorded execution used Windows, Python 3.14.10, pytest 9.2.0 and synthetic data.
GitHub's Linux/Windows jobs provide remote confirmation after this test commit.
There is no database, network payment service or GUI involved in these cases.

M5 fixes #11/#12 on `feature/w1-billing-money`, then merges the updated branch
into `feature/w1-billing-models` without rebasing/force-pushing. Rerun all tests;
both reviewers approve the final fixed changes only after independent evidence
is green. M1 is the tester and does not replace either assigned reviewer.
The foundation dependency must be accepted/retargeted before merging into main.
