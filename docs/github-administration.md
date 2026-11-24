# GitHub administration and preservation

Repository: `mohamedeghboudj/clinic-management-system`, public, default branch main.
Initial inspection found main unprotected and no rulesets; the policy below is
now applied. Verified write access: M2 `ahmed-ammiche`, M3 `SamirKor`,
M4 `MohamedAmine-dash`, M5 `ayyoubbouchama`. M2 independently tests M1; M3/M4
are the assigned reviewers. Having access is not evidence of completed acceptance.

The original Telegram notification blob is preserved:
`b81663a6e5b4611129f05367b7da406867fb4c06`. Its original filename, contents and
secret references remain unchanged. The old nonempty charter was archived outside
the application folder; prior scaffold/history remains recoverable in Git.

## Prepared configuration

`.github/repository-policy.json` describes squash-only PR merges, branch deletion
after merge, two approvals, stale-review dismissal, code-owner/last-push approval,
strict required CI, conversation resolution, admin enforcement and no force pushes.
It also configures read-only workflow tokens without bot PR approval, selected
Actions (including the retained Telegram exception), dependency alerts/fixes and
secret scanning/push protection. New workflows pin action commit SHAs.

## Active branch rulesets — 1 November 2026

Both rulesets are active and have empty bypass lists, including for administrators
and integrations. Existing classic main protection is also retained.

| Ruleset | Scope | Enforced behavior |
| --- | --- | --- |
| [Main: reviewed PRs and verified CI](https://github.com/mohamedeghboudj/clinic-management-system/rules/26311417) | `main` | PR required; two approvals; stale approvals dismissed; code-owner review; approval after the latest push from someone other than its pusher; resolved conversations; current required CI; squash-only merge; linear history; no deletion or force push. |
| [Working branches: preserve shared history](https://github.com/mohamedeghboudj/clinic-management-system/rules/26311418) | Every other branch, including future feature branches | No force pushes. Normal commits, merge-based updates and branch creation remain available. Merged feature branches can still be deleted automatically. |

Direct pushes to main are blocked by the PR requirement. The required checks are
`quality`, `unit (ubuntu-latest)`, `unit (windows-latest)`, `dependencies` and
`analyze`, each bound to the verified GitHub Actions integration (app ID 15368).
The source binding prevents a same-name status from another integration from
satisfying the rule. Auto-merge remains disabled.

Versioned definitions live in `.github/rulesets/main.json` and
`.github/rulesets/working-branches.json`; `repository-policy.json` references them.
The administration script creates missing named rulesets or updates their existing
IDs. It leaves unrelated rulesets untouched and refuses duplicate names. `--check`
verifies enforcement, targets, bypass lists, rule types and parameters from GitHub.

CODEOWNERS names eligible review pairs; GitHub's two-approval plus code-owner rules
do not require both specific people automatically. Check the named rotation in
CONTRIBUTING.md before merging. GitHub reads CODEOWNERS from the PR's base branch:
until #5 lands, it is not yet available on main, so verify the assigned M3/M4 pair
manually for that first PR. The two-approval rule is already active.

The three stacked foundation PRs keep their existing bases and draft status.
Independent tests and assigned reviews remain mandatory for each; merge #5,
retarget #6 to main, then repeat for #7. Normal working-branch pushes are necessary
for M2 to add tests; no PR-only restriction is applied to those source branches.

The GitHub plugin supports contents/PR work but exposes no administration-write
tool. Local SSH authentication is unavailable; public HTTPS fetch works. An
administration credential was supplied through the authenticated CLI; the
prepared policy is now applied and its full readback matches on 1 November.
No token is requested in chat, read from the plugin's private storage or committed.

For future inspection or reviewed policy changes using authenticated GitHub CLI:

```powershell
python -m scripts.configure_github            # inspect exact public policy
python -m scripts.configure_github --apply    # explicit settings mutations
python -m scripts.configure_github --check    # verify current remote enforcement
```

The script also accepts a privately supplied GH_TOKEN environment value, never
printing or persisting it. It validates the fixed authorized repository and admin
permission before writes. Settings changes are sequential; if a provider permission
or plan rejects one, report the actual partial state and rerun/check after resolving
it. A checked-in settings file by itself does not configure GitHub.

Do not enable a global SHA-only Actions restriction that breaks the preserved
Telegram action at `@master`; any change to that user-owned workflow is separate.
Do not weaken approvals while independent tests or reviews are pending. No PR auto-approval, auto-merge,
direct main push, visibility change or release deployment is included.

References: [protected-branch API](https://docs.github.com/en/rest/branches/branch-protection),
[repository rulesets API](https://docs.github.com/en/rest/repos/rules),
[CODEOWNERS base-branch behavior](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners),
[Actions permissions API](https://docs.github.com/en/rest/actions/permissions),
[Actions security guidance](https://docs.github.com/en/actions/reference/security/secure-use).
