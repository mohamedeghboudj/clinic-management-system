# Clinic Management System

Python desktop and modular backend project for clinic staff. The authoritative
database will be remote PostgreSQL; Sprint 1 foundation commands use memory only.

The model demo connects registration, scheduling, clinical history and billing in memory.

See the [delivery plan](docs/delivery.md) for the three increments, sprint deadlines,
implementation issues and the condition for starting Sprint 2.

## Start in a fresh Conda environment

The team confirmed **Python 3.14**. Run from this repository root:

```powershell
conda env create --prefix ./.conda-env --file environment.yml
conda activate ./.conda-env
python -m pip install --require-hashes -r requirements-dev.txt
python -m pip install --no-deps --no-build-isolation -e .
python -m scripts.demo_model
```

Install the local hooks with `python -m pre_commit install` after activating the environment.
Do not reuse the base Conda environment. `environment.yml` defines the portable
minor-version baseline; `requirements-dev.txt` hash-locks developer tools and runtime timezone data. Native
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

The combined suite includes the independent billing, clinical and scheduling contracts.
Run `python -m scripts.demo_model --foundation-only` to isolate transaction checks.
The default demo also verifies the clinical access denial, the 600 DZD balance and rollback.
See [the story-by-story acceptance evidence](docs/requirements.md#sprint-1-increment-verification).

## Package structure

| Location                                                  | Purpose                                                                          |
| --------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `src/clinic_management/domain/shared/`                    | Identity, errors, event envelopes, money, time slots and contact values.    |
| `src/clinic_management/domain/people/`, `access/`         | People and access profiles, membership and authorization.                                               |
| `src/clinic_management/domain/facilities/`, `scheduling/` | Scheduling clinic resources and scheduling.                                                      |
| `src/clinic_management/domain/clinical/`                  | Clinical notes, prescriptions and service catalogue.                                           |
| `src/clinic_management/domain/billing/`                   | Billing invoices and payment records.                                                         |
| `application/contracts/`, `application/ports/`            | Shared DTOs and feature repository ports.                          |
| `infrastructure/`, `api/`, `desktop/`, `bootstrap/`       | Inward-dependent adapters and composition roots; SQL/API/GUI integrations follow Sprint 1. |
| `tests/support/`                                          | Deterministic clocks/IDs and single-threaded rollback/version fakes.                     |
| `scripts/`                                                | Offline checks, Sprint 1 clinic demo and explicit GitHub policy administration.               |
| `docs/`                                                   | Architecture, handoff contracts, operations and review evidence.                         |

No domain module imports SQLAlchemy, FastAPI, Qt, application adapters or tests.
Account roles are composed, not represented by empty Person subclasses. Preserve
the public Foundation signatures in [the contract index](docs/contracts/foundation.md).

## GitHub workflow

Use short-lived feature branches and PRs into `main`. Two
assigned human approvals and independent testing remain mandatory.

The Telegram workflow publishes repository notifications.
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
- [Database design and ER model](docs/design/database.md)
- [Connected visit API and Python contracts](docs/contracts/connected-visit.md)
- [Security reporting and telemetry](SECURITY.md)
