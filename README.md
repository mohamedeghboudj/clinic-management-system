# Clinic Management System

Python desktop and modular backend project for clinic staff. The authoritative
database will be remote PostgreSQL; Week 1 foundation commands use memory only.

The foundation is being implemented by M1 (Mohamed). Patient/access, scheduling,
clinical and billing implementations belong to M2–M5. Empty feature packages are
documented extension locations, not claims that those features work.

## Start in a fresh Conda environment

The team confirmed **Python 3.14**. Run from this repository root:

```powershell
conda env create --prefix ./.conda-env --file environment.yml
conda activate ./.conda-env
python -m pip install --require-hashes -r requirements-dev.txt
python -m pip install --no-deps --no-build-isolation -e .
python -m scripts.demo_model --foundation-only
```

Install the local hooks with `python -m pre_commit install` after activating the environment.
Do not reuse the base Conda environment. `environment.yml` defines the portable
minor-version baseline; `requirements-dev.txt` hash-locks Python tooling. Native
Conda dependencies vary by operating system. CI uses clean Python 3.14 runners
on Linux and Windows to check portability. No local database service is needed.

## Verify before requesting review

```powershell
python -m ruff check src tests scripts
python -m ruff format --check src tests scripts
python -m mypy
python -m scripts.check_source
python -m scripts.check_repository
python -m scripts.check_workflows
python -m scripts.requirements_input
python -m pylint --persistent=no src tests scripts
python -m deptry .
python -m scripts.check_secrets
python -m pytest --cov --cov-report=term-missing --cov-report=json
python -m scripts.check_coverage
python -m build --no-isolation
```

Tests in `tests/verification/` are M1 author verification, permitted by Mohamed.
They do **not** replace M2's independent foundation tests. M1's billing contract
tests are explicitly deferred until M5's implementation is available. Missing
features never receive passing placeholder tests.

## Structure and ownership

| Location | Purpose / owner |
| --- | --- |
| `src/clinic_management/domain/shared/` | M1 identity, errors, event envelopes; M5 adds Money, M3 TimeSlot, M2 contact/address. |
| `src/clinic_management/domain/people/`, `access/` | M2 profiles, membership and authorization. |
| `src/clinic_management/domain/facilities/`, `scheduling/` | M3 clinic resources and scheduling. |
| `src/clinic_management/domain/clinical/` | M4 notes, prescriptions and service catalogue. |
| `src/clinic_management/domain/billing/` | M5 invoices and payment records. |
| `application/contracts/`, `application/ports/` | M1 shared DTOs/ports; each member adds their feature contracts. |
| `infrastructure/`, `api/`, `desktop/`, `bootstrap/` | Inward-dependent adapters and composition roots; SQL/API/GUI integrations follow Week 1. |
| `tests/support/` | Deterministic clocks/IDs and single-threaded rollback/version fakes. |
| `scripts/` | Offline checks, foundation demo and explicit GitHub policy administration. |
| `docs/` | Architecture, handoff contracts, operations and review evidence. |

No domain module imports SQLAlchemy, FastAPI, Qt, application adapters or tests.
Account roles are composed, not represented by empty Person subclasses. Preserve
the public M1 signatures in [the contract index](docs/contracts/foundation.md).

## GitHub workflow

Use short-lived `feature/w1-foundation-*` branches and PRs into `main`. Two
assigned human approvals and independent testing remain mandatory. M2 is
`@ahmed-ammiche`, M3 `@SamirKor`, M4 `@MohamedAmine-dash` and M5
`@ayyoubbouchama`; all have verified write access. Never substitute
the author, a bot or a fabricated reviewer for a missing teammate.

Your original `.github/workflows/telegram-notif.yml` is preserved byte-for-byte.
New workflows use pinned action commits, least-privilege tokens, timeouts and
clean installs. See [GitHub administration](docs/github-administration.md) for
the exact policy and the difference between prepared files and active settings.

Active rulesets require PRs into `main`, two approvals, resolved conversations,
current required GitHub Actions checks and squash merging, with no bypass actors.
Main deletion and force pushes are blocked; other branches also block force pushes
while allowing normal author/tester commits and deletion after merge.

## Continue here

- [Contribution and review rules](CONTRIBUTING.md)
- [Architecture and dependency decisions](docs/adr/0001-architecture.md)
- [Foundation signatures and compatibility](docs/contracts/foundation.md)
- [Error codes](docs/contracts/error-codes.md)
- [Recovery and operation runbook](docs/runbook.md)
- [M1 completion and external dependencies](docs/M1_PROGRESS.md)
- [Security reporting and telemetry](SECURITY.md)

The three planning documents live outside this standalone repository in the
parent `Project/` directory as requested. The previous nonempty process charter
was also preserved there as `Team-Process-Charter.pdf`. Historical scaffold
contents remain recoverable through Git history.
