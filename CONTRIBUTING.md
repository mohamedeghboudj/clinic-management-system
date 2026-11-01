# Contributing

Use the Python 3.14 Conda environment and run the README checks from the repository
root. Runtime packages belong in pinned `requirements.txt`; direct developer
tools in `pyproject.toml` dependency-groups.dev, generated into `requirements-dev.in`
and resolved with hashes into `requirements-dev.txt`.
The current M1 runtime has no third-party dependency.

```powershell
python -m scripts.requirements_input --write
python -m piptools compile --allow-unsafe --generate-hashes --strip-extras --no-emit-index-url --output-file requirements-dev.txt requirements-dev.in
```

Inspect dependency changes and test both supported CI operating systems. Avoid
environment-specific absolute paths, local data or credentials in any lock file.

## Branches and commits

Begin from updated `main`; create one cohesive `feature/<ticket>-<topic>` branch.
M1's sequence is foundation contracts/tooling, fakes, then demo/design evidence.
Closely dependent work may use explicitly documented stacked PRs; never merge
past independent tests or the required human reviews just to unblock a stack.

```powershell
git switch main
git pull --ff-only origin main
git switch -c feature/your-ticket-topic
git add -- path/to/intended/file.py
git diff --cached
git commit -m "feat(scope): describe the accepted behavior"
git push -u origin feature/your-ticket-topic
```

Open a draft PR early and request the assigned independent tester. The tester
contributes tests to that branch from their own clone. Fetch/pull before editing
a shared branch; do not rebase or force-push it. Integrate upstream changes with
`git fetch origin` followed by `git merge origin/main`, resolve deliberately and
rerun checks. Squash-merge the reviewed PR, preserving contributor attribution.

## Review and independent verification

| Author | Assigned reviewers | Independent test author |
| --- | --- | --- |
| M1 Mohamed | M3 SamirKor, M4 pending | M2 pending |
| M2 pending | M4 pending, M5 ayyoubbouchama | M3 SamirKor |
| M3 SamirKor | M5 ayyoubbouchama, M1 Mohamed | M4 pending |
| M4 pending | M1 Mohamed, M2 pending | M5 ayyoubbouchama |
| M5 ayyoubbouchama | M2 pending, M3 SamirKor | M1 Mohamed |

Author verification is allowed but is labelled separately. Two non-author human
approvals apply after final changes, including test changes. A reviewer merges.
M1 work stays unmerged until M2/M4 join or the team explicitly changes the
assignments. CODEOWNERS can only name available users with repository access;
its available-owner fallback does not replace the table above.

## Seven code rules

1. No block over 40 lines repeated at least three times. The configured duplicate
   detector warns at two normalized copies; reviewers check the actual concept.
2. Cohesive OOP and replaceable dependency ports; typed pure helpers are allowed.
3. No maintained Python file, including tests/scripts, over 500 physical lines.
4. No avoidable branch chains; complexity budget <=10, with ordinary guards allowed.
5. Google-style docstrings on every function, including private helpers/tests.
6. Annotate all inputs and returns, except conventional `self`/`cls` receivers.
7. Declare every required package and commit tested dependency locks.

The source checker enforces file size, all-function documentation/annotations
and inward imports. Ruff covers style/security/complexity, mypy strict types,
pylint normalized duplication, deptry undeclared/unused dependencies, and the
secret scanner candidate credentials. No silent/bare exception handlers.

## Definition of Done

Accepted behavior and invariants are documented; independent tests and both
human approvals are present; required CI is green; each measured implementation
module has >=80% branch coverage (statement coverage when it has no branches);
docs/dependencies/migrations are updated; no real patient data or secrets; the
integrated behavior is demonstrated. Test support is measured too. Coverage is
not evidence that untested remote transactions or permissions are correct.

The original Telegram workflow is deliberately preserved. Do not alter it,
its secret names or repository visibility as an incidental cleanup. New security
settings live in the reviewed policy and require actual administration access.
